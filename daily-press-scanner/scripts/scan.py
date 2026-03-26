#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen

try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    PdfReader = None

try:
    from PIL import Image, ImageOps  # type: ignore
except Exception:
    Image = None
    ImageOps = None


OPINION_KEYWORDS = (
    "opinion",
    "editorial",
    "analysis",
    "column",
    "comment",
    "review",
    "letters",
)

DEFAULT_TOPIC_MAP = {
    "tariffs": ("tariff", "tariffs", "trade", "duties", "duty", "import", "imports", "export", "exports"),
    "ai": ("ai", "artificial intelligence", "machine learning", "nvidia", "openai", "model", "models", "chip", "chips"),
    "china": ("china", "chinese", "beijing", "xi", "xi jinping", "yuan", "property", "manufacturing"),
    "fed": ("fed", "federal reserve", "powell", "rates", "inflation", "interest rate", "interest rates"),
    "war": ("war", "missile", "strike", "gaza", "ukraine", "iran", "israel", "russia", "conflict"),
    "markets": ("market", "markets", "stocks", "stock", "bonds", "yields", "equities", "shares", "wall street"),
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local daily press PDF scanner")
    parser.add_argument("--urls", required=True, help="Path to a text file with one PDF URL or local path per line")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--topics", default="", help="Optional comma-separated topic list")
    parser.add_argument("--max-pages", type=int, default=12, help="Optional page cap per paper")
    parser.add_argument("--dpi", type=int, default=200, help="Render DPI for pdftoppm")
    return parser.parse_args()


def read_source_lines(path: Path) -> list[str]:
    lines: list[str] = []
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        lines.append(line)
    return lines


def safe_slug(value: str, fallback_prefix: str = "paper") -> str:
    parsed = urlparse(value)
    if parsed.scheme in {"http", "https", "file"}:
        candidate = Path(unquote(parsed.path)).name
    else:
        candidate = Path(value).name
    candidate = re.sub(r"[^A-Za-z0-9._-]+", "-", candidate).strip("-._")
    candidate = candidate.replace(".pdf", "")
    if not candidate:
        candidate = fallback_prefix
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return f"{candidate}-{digest}"


def infer_source_name(source: str) -> str:
    parsed = urlparse(source)
    if parsed.scheme in {"http", "https", "file"}:
        candidate = Path(unquote(parsed.path)).stem
    else:
        candidate = Path(source).stem
    candidate = re.sub(r"[_-]+", " ", candidate).strip()
    return candidate or safe_slug(source)


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def run_command(cmd: list[str], *, cwd: Path | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def download_or_copy_source(source: str, dest: Path) -> tuple[Path | None, str | None]:
    try:
        source_path = Path(source)
        if source_path.exists():
            shutil.copy2(source_path, dest)
            return dest, None

        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            request = Request(source, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=60) as response, dest.open("wb") as handle:
                shutil.copyfileobj(response, handle)
            return dest, None
        if parsed.scheme == "file":
            raw_path = unquote(parsed.path or "")
            if parsed.netloc:
                raw_path = f"//{parsed.netloc}{raw_path}"
            source_path = Path(raw_path)
            if not source_path.exists():
                return None, f"file url does not exist: {source}"
            shutil.copy2(source_path, dest)
            return dest, None
        return None, f"unsupported or missing source: {source}"
    except Exception as exc:
        return None, f"download failed: {exc}"


def get_page_count(pdf_path: Path) -> tuple[int | None, str | None]:
    if PdfReader is not None:
        try:
            reader = PdfReader(str(pdf_path))
            return len(reader.pages), "pypdf"
        except Exception as exc:
            pypdf_error = str(exc)
    else:
        pypdf_error = "pypdf unavailable"

    try:
        result = run_command(["pdfinfo", str(pdf_path)])
        match = re.search(r"^Pages:\s+(\d+)$", result.stdout, re.MULTILINE)
        if match:
            return int(match.group(1)), "pdfinfo"
        return None, f"pdfinfo could not parse page count: {pdf_path}"
    except FileNotFoundError:
        return None, f"pdfinfo unavailable; {pypdf_error}"
    except subprocess.CalledProcessError as exc:
        return None, f"pdfinfo failed: {exc.stderr.strip() or exc.stdout.strip()}"


def render_page(pdf_path: Path, page_number: int, preview_stem: Path, dpi: int) -> Path:
    ensure_dir(preview_stem.parent)
    cmd = [
        "pdftoppm",
        "-f",
        str(page_number),
        "-l",
        str(page_number),
        "-singlefile",
        "-png",
        "-r",
        str(dpi),
        str(pdf_path),
        str(preview_stem),
    ]
    run_command(cmd)
    return preview_stem.with_suffix(".png")


def ocr_image(image_path: Path) -> str:
    cmd = ["tesseract", str(image_path), "stdout", "-l", "eng", "--psm", "6"]
    try:
        result = run_command(cmd)
    except FileNotFoundError as exc:
        raise RuntimeError("tesseract is not available") from exc
    return result.stdout.strip()


def normalize_text(text: str) -> str:
    text = text.replace("\x0c", "\n")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def title_candidate(lines: list[str]) -> str:
    best_line = ""
    best_score = -1.0
    for index, line in enumerate(lines[:18]):
        clean = line.strip()
        if not clean:
            continue
        if len(clean) < 8:
            continue
        if re.fullmatch(r"[\d\s-]+", clean):
            continue
        letters = sum(1 for ch in clean if ch.isalpha())
        digits = sum(1 for ch in clean if ch.isdigit())
        upper_ratio = sum(1 for ch in clean if ch.isupper()) / max(1, letters)
        punctuation_penalty = sum(1 for ch in clean if ch in ".,;:!?") * 0.2
        length_bonus = min(len(clean), 120) / 12.0
        position_bonus = max(0.0, 2.0 - index * 0.1)
        score = length_bonus + position_bonus + upper_ratio * 2.0 - digits * 0.1 - punctuation_penalty
        lowered = clean.lower()
        if any(keyword in lowered for keyword in OPINION_KEYWORDS):
            score -= 0.5
        if score > best_score:
            best_score = score
            best_line = clean
    return best_line


def section_guess(text: str) -> str:
    lowered = text.lower()
    for keyword in ("opinion", "editorial", "analysis", "column", "comment", "review", "books"):
        if re.search(rf"\b{re.escape(keyword)}\b", lowered):
            return keyword
    return ""


def snippet_text(lines: list[str]) -> str:
    body = []
    for line in lines:
        clean = line.strip()
        if not clean:
            continue
        lowered = clean.lower()
        if lowered in {"opinion", "editorial", "analysis", "column", "review", "comment"}:
            continue
        if re.fullmatch(r"by\s+.+", lowered):
            continue
        body.append(clean)
        if sum(len(part) for part in body) > 300:
            break
    return compact_text(" ".join(body))[:320]


def opinion_score(lines: list[str], text: str) -> tuple[float, str, list[str]]:
    joined = "\n".join(lines[:35])
    lowered = text.lower()
    reasons: list[str] = []
    score = 0.0

    section = section_guess(joined or text)
    if section:
        score += 0.25
        reasons.append(f"section:{section}")

    if any(re.search(rf"\b{keyword}\b", lowered) for keyword in OPINION_KEYWORDS):
        score += 0.25
        reasons.append("opinion keyword")

    if re.search(r"(?im)^by\s+[A-Z][A-Za-z.'-]+", text) or re.search(r"(?im)\bby\s+[A-Z][A-Za-z.'-]+\b", text):
        score += 0.2
        reasons.append("byline")

    word_count = len(re.findall(r"\b\w+\b", text))
    digit_count = len(re.findall(r"\d", text))
    if word_count >= 120 and digit_count <= max(10, word_count // 20):
        score += 0.15
        reasons.append("prose-heavy")

    upper_lines = sum(1 for line in lines[:15] if line.isupper() and len(line) > 5)
    if upper_lines >= 2:
        score += 0.1
        reasons.append("headline layout")

    if digit_count > word_count // 6:
        score -= 0.15
        reasons.append("digit-heavy")

    return max(0.0, min(1.0, score)), section, reasons


def singular_forms(term: str) -> set[str]:
    terms = {term}
    if term.endswith("ies") and len(term) > 3:
        terms.add(term[:-3] + "y")
    elif term.endswith("s") and len(term) > 3:
        terms.add(term[:-1])
    else:
        terms.add(f"{term}s")
    return {item for item in terms if item}


def normalize_topic_terms(topics: str) -> dict[str, list[str]]:
    raw_topics = [item.strip() for item in topics.split(",") if item.strip()]
    if raw_topics:
        topic_map: dict[str, list[str]] = {}
    else:
        topic_map = {key: list(values) for key, values in DEFAULT_TOPIC_MAP.items()}

    for raw_topic in raw_topics:
        canonical = re.sub(r"\s+", " ", raw_topic.lower())
        seed_terms = set(DEFAULT_TOPIC_MAP.get(canonical, (canonical,)))
        if " " not in canonical:
            expanded = set()
            for term in seed_terms:
                expanded |= singular_forms(term)
            seed_terms |= expanded
        topic_map[canonical] = sorted(seed_terms)
    return topic_map


def term_present(term: str, haystack: str) -> bool:
    if " " in term:
        return term in haystack
    return bool(re.search(rf"\b{re.escape(term)}\b", haystack))


def topic_matches(topic_map: dict[str, list[str]], text: str, title: str, snippet: str) -> list[dict[str, object]]:
    haystack = {
        "title": title.lower(),
        "snippet": snippet.lower(),
        "body": text.lower(),
    }
    matches: list[dict[str, object]] = []
    for topic, terms in topic_map.items():
        matched_terms: list[str] = []
        score = 0.0
        for term in terms:
            term_l = term.lower()
            if term_present(term_l, haystack["title"]):
                matched_terms.append(term)
                score += 3.0
            elif term_present(term_l, haystack["snippet"]):
                matched_terms.append(term)
                score += 2.0
            elif term_present(term_l, haystack["body"]):
                matched_terms.append(term)
                score += 1.0
        if matched_terms:
            unique_terms = sorted(set(matched_terms), key=matched_terms.index)
            matches.append(
                {
                    "topic": topic,
                    "score": round(min(1.0, score / 6.0), 3),
                    "matched_terms": unique_terms,
                }
            )
    matches.sort(key=lambda item: item["score"], reverse=True)
    return matches


def prepare_ocr_variants(image_path: Path, work_dir: Path) -> list[Path]:
    if Image is None or ImageOps is None:
        return [image_path]

    ensure_dir(work_dir)
    variants: list[Path] = []
    with Image.open(image_path) as img:
        gray = ImageOps.autocontrast(img.convert("L"))
        full_path = work_dir / "full.png"
        gray.save(full_path)
        variants.append(full_path)

        width, height = gray.size
        if width >= 1.25 * height and width >= 1400:
            overlap = max(40, width // 40)
            mid = width // 2
            left = gray.crop((0, 0, min(width, mid + overlap), height))
            right = gray.crop((max(0, mid - overlap), 0, width, height))
            left_path = work_dir / "left.png"
            right_path = work_dir / "right.png"
            left.save(left_path)
            right.save(right_path)
            variants.extend([left_path, right_path])
    return variants


def merge_ocr_texts(texts: Iterable[str]) -> str:
    lines: list[str] = []
    seen = set()
    for text in texts:
        for line in text.splitlines():
            clean = line.strip()
            if not clean:
                continue
            key = clean.lower()
            if key in seen:
                continue
            seen.add(key)
            lines.append(clean)
    return normalize_text("\n".join(lines))


def process_paper(
    source: str,
    out_dir: Path,
    dpi: int,
    max_pages: int | None,
    topic_map: dict[str, list[str]],
) -> dict[str, object]:
    paper_slug = safe_slug(source)
    source_name = infer_source_name(source)
    pdf_dir = ensure_dir(out_dir / "pdfs")
    ocr_dir = ensure_dir(out_dir / "ocr" / paper_slug)
    preview_dir = ensure_dir(out_dir / "previews" / paper_slug)

    pdf_path = pdf_dir / f"{paper_slug}.pdf"
    paper_errors: list[dict[str, object]] = []

    downloaded_path, download_error = download_or_copy_source(source, pdf_path)
    if download_error:
        return {
            "paper": {
                "source_name": source_name,
                "paper_id": paper_slug,
                "url": source,
                "local_pdf": None,
                "page_count": 0,
                "scanned_pages": 0,
                "status": "download_failed",
            },
            "page_index": [],
            "opinion_candidates": [],
            "topic_hits": [],
            "errors": [{"source": source, "paper": paper_slug, "stage": "download", "message": download_error}],
        }

    pdf_path = downloaded_path or pdf_path
    page_count, page_count_source = get_page_count(pdf_path)
    if page_count is None:
        page_limit = max_pages if max_pages is not None else 200
        paper_errors.append(
            {
                "source": source,
                "paper": paper_slug,
                "stage": "page_count",
                "message": page_count_source or "unknown page count",
            }
        )
    else:
        page_limit = min(page_count, max_pages) if max_pages is not None else page_count

    page_index: list[dict[str, object]] = []
    opinion_candidates: list[dict[str, object]] = []
    topic_hits: list[dict[str, object]] = []

    with tempfile.TemporaryDirectory(prefix=f"{paper_slug}-") as tmp_root:
        tmp_dir = Path(tmp_root)
        scan_limit = page_limit if page_limit is not None else (max_pages or 200)
        for page_number in range(1, scan_limit + 1):
            preview_stem = preview_dir / f"page-{page_number:03d}"
            ocr_path = ocr_dir / f"page-{page_number:03d}.txt"
            page_record: dict[str, object] = {
                "source_name": source_name,
                "paper_id": paper_slug,
                "url": source,
                "page": page_number,
                "preview_path": str(preview_stem.with_suffix(".png").relative_to(out_dir)),
                "ocr_path": str(ocr_path.relative_to(out_dir)),
            }
            try:
                image_path = render_page(pdf_path, page_number, preview_stem, dpi)
                variants = prepare_ocr_variants(image_path, tmp_dir / f"page-{page_number:03d}")
                variant_texts: list[str] = []
                ocr_variant_errors = 0
                for variant in variants:
                    try:
                        variant_texts.append(ocr_image(variant))
                    except Exception as exc:
                        ocr_variant_errors += 1
                        paper_errors.append(
                            {
                                "source": source,
                                "paper": paper_slug,
                                "page": page_number,
                                "stage": "ocr",
                                "message": str(exc),
                            }
                        )
                merged_text = merge_ocr_texts(variant_texts)
                if not merged_text:
                    if ocr_variant_errors == 0:
                        paper_errors.append(
                            {
                                "source": source,
                                "paper": paper_slug,
                                "page": page_number,
                                "stage": "ocr",
                                "message": "ocr produced no usable text",
                            }
                        )
                    continue

                ocr_path.write_text(merged_text + "\n", encoding="utf-8")

                raw_lines = [line.strip() for line in merged_text.splitlines() if line.strip()]
                title = title_candidate(raw_lines)
                snippet = snippet_text(raw_lines)
                op_score, section, op_reasons = opinion_score(raw_lines, merged_text)
                matches = topic_matches(topic_map, merged_text, title, snippet)

                page_record.update(
                    {
                        "title": title,
                        "snippet": snippet,
                        "section_guess": section,
                        "opinion_score": round(op_score, 3),
                        "topic_matches": matches,
                    }
                )
                page_index.append(page_record)

                if op_score >= 0.5:
                    opinion_candidates.append(
                        {
                            "source_name": source_name,
                            "url": source,
                            "page": page_number,
                            "title": title,
                            "section_guess": section,
                            "snippet": snippet,
                            "confidence": round(op_score, 3),
                            "topic_tags": [match["topic"] for match in matches[:3]],
                            "reasons": op_reasons,
                        }
                    )

                for match in matches:
                    topic_hits.append(
                        {
                            "source_name": source_name,
                            "url": source,
                            "page": page_number,
                            "topic": match["topic"],
                            "title": title,
                            "snippet": snippet,
                            "score": match["score"],
                            "matched_terms": match["matched_terms"],
                        }
                    )
            except subprocess.CalledProcessError as exc:
                paper_errors.append(
                    {
                        "source": source,
                        "paper": paper_slug,
                        "page": page_number,
                        "stage": "render",
                        "message": exc.stderr.strip() or exc.stdout.strip() or str(exc),
                    }
                )
                if page_count is None:
                    break
            except Exception as exc:
                paper_errors.append(
                    {
                        "source": source,
                        "paper": paper_slug,
                        "page": page_number,
                        "stage": "page",
                        "message": str(exc),
                    }
                )
                continue

    paper_summary = {
        "source_name": source_name,
        "paper_id": paper_slug,
        "url": source,
        "local_pdf": str(pdf_path.relative_to(out_dir)),
        "page_count": page_count,
        "scanned_pages": len(page_index),
        "status": "ok" if not paper_errors else "ok_with_errors",
        "page_count_source": page_count_source,
    }
    write_preview_summary(preview_dir / "summary.txt", paper_summary, page_index, opinion_candidates, topic_hits)
    return {
        "paper": paper_summary,
        "page_index": page_index,
        "opinion_candidates": opinion_candidates,
        "topic_hits": topic_hits,
        "errors": paper_errors,
    }


def write_preview_summary(
    path: Path,
    paper_summary: dict[str, object],
    page_index: list[dict[str, object]],
    opinion_candidates: list[dict[str, object]],
    topic_hits: list[dict[str, object]],
) -> None:
    lines = [
        f"source_name: {paper_summary['source_name']}",
        f"paper_id: {paper_summary['paper_id']}",
        f"url: {paper_summary['url']}",
        f"page_count: {paper_summary['page_count']}",
        f"scanned_pages: {paper_summary['scanned_pages']}",
        "",
        "pages:",
    ]
    opinion_pages = {item["page"] for item in opinion_candidates}
    topic_pages = Counter((item["page"], item["topic"]) for item in topic_hits)
    for page in page_index:
        page_num = page["page"]
        hits = [topic for (hit_page, topic), count in topic_pages.items() if hit_page == page_num and count > 0]
        lines.append(
            f"- page {page_num:03d}: {page.get('title') or '[no title]'} | "
            f"opinion={'yes' if page_num in opinion_pages else 'no'} | "
            f"topics={', '.join(sorted(set(hits))) if hits else '-'}"
        )
        snippet = page.get("snippet")
        if snippet:
            lines.append(f"  snippet: {snippet}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    urls_path = Path(args.urls)
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)
    ensure_dir(out_dir / "pdfs")
    ensure_dir(out_dir / "ocr")
    ensure_dir(out_dir / "previews")

    if not urls_path.exists():
        print(f"Missing --urls file: {urls_path}", file=sys.stderr)
        return 2

    sources = read_source_lines(urls_path)
    if not sources:
        print("No sources found in --urls file", file=sys.stderr)
        return 2

    topic_map = normalize_topic_terms(args.topics)
    results: dict[str, object] = {
        "run_date": date.today().isoformat(),
        "inputs": sources,
        "papers": [],
        "page_index": [],
        "opinion_candidates": [],
        "topic_hits": [],
        "errors": [],
    }

    for source in sources:
        paper_result = process_paper(
            source=source,
            out_dir=out_dir,
            dpi=args.dpi,
            max_pages=args.max_pages if args.max_pages and args.max_pages > 0 else None,
            topic_map=topic_map,
        )
        results["papers"].append(paper_result["paper"])
        results["page_index"].extend(paper_result["page_index"])
        results["opinion_candidates"].extend(paper_result["opinion_candidates"])
        results["topic_hits"].extend(paper_result["topic_hits"])
        results["errors"].extend(paper_result["errors"])

    results_path = out_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
