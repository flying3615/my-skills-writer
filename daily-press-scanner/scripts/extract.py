#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import importlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Lightweight translated press extractor")
    parser.add_argument("--url", default="", help="Single PDF URL or local path")
    parser.add_argument("--urls", default="", help="Path to a text file with one PDF URL or local path per line")
    parser.add_argument("--source-config", default="", help="Optional JSON config with translated PDF URL templates")
    parser.add_argument("--run-date", default="", help="Optional run date in YYYY-MM-DD format")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    return parser.parse_args()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_dir(path: Path) -> Path:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def display_path(path: Path, base_dir: Path) -> str:
    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


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
    candidate = re.sub(r"\.pdf$", "", candidate, flags=re.IGNORECASE)
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


def load_translated_source_config(path: Path) -> list[dict[str, object]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        raw_sources = data.get("sources", [])
    elif isinstance(data, list):
        raw_sources = data
    else:
        raise ValueError("source config must be a list or an object with a sources list")

    if not isinstance(raw_sources, list):
        raise ValueError("source config sources must be a list")

    sources: list[dict[str, object]] = []
    for raw_source in raw_sources:
        if not isinstance(raw_source, dict):
            continue
        if raw_source.get("enabled", True) is False:
            continue
        url_template = str(raw_source.get("url_template") or raw_source.get("url") or "").strip()
        if not url_template:
            continue
        source_name = str(raw_source.get("source_name") or raw_source.get("name") or "").strip()
        normalized = dict(raw_source)
        normalized["source_name"] = source_name or infer_source_name(url_template)
        normalized["url_template"] = url_template
        normalized["enabled"] = True
        sources.append(normalized)
    return sources


def resolve_translated_source_urls(sources: list[dict[str, object]], run_date: date) -> list[dict[str, object]]:
    resolved_sources: list[dict[str, object]] = []
    for source in sources:
        url_template = str(source.get("url_template", "")).strip()
        if not url_template:
            continue
        url = url_template.format(
            month=run_date.month,
            day=run_date.day,
            year=run_date.year,
            date=run_date.isoformat(),
        )
        resolved_source = dict(source)
        resolved_source["url"] = url
        resolved_source["run_date"] = run_date.isoformat()
        resolved_sources.append(resolved_source)
    return resolved_sources


def collect_sources(
    *,
    url: str | None,
    urls_path: Path | None,
    source_config_path: Path | None,
    run_date: date,
) -> list[dict[str, object]]:
    if source_config_path is not None:
        return resolve_translated_source_urls(load_translated_source_config(source_config_path), run_date)

    sources: list[dict[str, object]] = []
    if url:
        sources.append({"source_name": infer_source_name(url), "url": url, "enabled": True})
    if urls_path is not None:
        for raw_source in read_source_lines(urls_path):
            sources.append({"source_name": infer_source_name(raw_source), "url": raw_source, "enabled": True})
    return sources


def download_or_copy_source(source: str, dest: Path) -> tuple[Path | None, str | None]:
    try:
        ensure_dir(dest.parent)
        source_path = Path(source)
        if source_path.exists():
            shutil.copy2(source_path, dest)
            return dest, None

        parsed = urlparse(source)
        if parsed.scheme in {"http", "https"}:
            request = Request(source, headers={"User-Agent": "Mozilla/5.0"})
            with urlopen(request, timeout=120) as response, dest.open("wb") as handle:
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


def normalize_page_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    lines = [line.rstrip() for line in normalized.splitlines()]
    return "\n".join(lines).strip()


def write_page_texts(page_texts: list[tuple[int, str]], text_dir: Path, out_dir: Path) -> list[dict[str, object]]:
    ensure_dir(text_dir)
    page_list: list[dict[str, object]] = []
    for page_number, page_text in page_texts:
        normalized = normalize_page_text(page_text)
        if not normalized:
            continue
        page_path = text_dir / f"page-{page_number:03d}.txt"
        page_path.write_text(normalized + "\n", encoding="utf-8")
        page_list.append({"page": page_number, "path": display_path(page_path, out_dir), "chars": len(normalized)})
    return page_list


def extract_text_pdftotext(pdf_path: Path, text_dir: Path, out_dir: Path) -> dict[str, object]:
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as handle:
        temp_output = Path(handle.name)
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), str(temp_output)],
            capture_output=True,
            text=True,
            timeout=120,
            check=False,
        )
        if result.returncode != 0:
            return {"status": "error", "reason": result.stderr.strip() or "pdftotext failed"}

        raw_text = temp_output.read_text(encoding="utf-8", errors="replace")
        page_texts = [(page_number, page_text) for page_number, page_text in enumerate(raw_text.split("\f"), start=1)]
        page_list = write_page_texts(page_texts, text_dir, out_dir)
        return {
            "status": "ok",
            "method": "pdftotext",
            "pages": len(page_list),
            "page_list": page_list,
        }
    except FileNotFoundError:
        return {"status": "unavailable", "reason": "pdftotext not found"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": "pdftotext timed out"}
    finally:
        temp_output.unlink(missing_ok=True)


def import_pymupdf_module():
    for module_name in ("pymupdf", "fitz"):
        try:
            return importlib.import_module(module_name)
        except ImportError:
            continue
    raise ImportError("PyMuPDF not installed")


def extract_text_pymupdf(pdf_path: Path, text_dir: Path, out_dir: Path) -> dict[str, object]:
    try:
        pymupdf = import_pymupdf_module()
    except ImportError as exc:
        return {"status": "error", "reason": str(exc)}

    document = pymupdf.open(str(pdf_path))
    try:
        page_texts = []
        for page_number, page in enumerate(document, start=1):
            page_texts.append((page_number, page.get_text()))
    finally:
        document.close()

    page_list = write_page_texts(page_texts, text_dir, out_dir)
    return {
        "status": "ok",
        "method": "pymupdf",
        "pages": len(page_list),
        "page_list": page_list,
    }


def extract_text(pdf_path: Path, text_dir: Path, out_dir: Path) -> dict[str, object]:
    result = extract_text_pdftotext(pdf_path, text_dir, out_dir)
    if result.get("status") == "ok":
        return result
    fallback = extract_text_pymupdf(pdf_path, text_dir, out_dir)
    if fallback.get("status") == "ok":
        fallback["pdftotext_status"] = result.get("status")
        fallback["pdftotext_reason"] = result.get("reason")
        return fallback
    return {
        "status": "error",
        "reason": f"pdftotext: {result.get('reason', 'unknown')}; pymupdf: {fallback.get('reason', 'unknown')}",
    }


def process_paper(source: str | dict[str, object], out_dir: Path) -> dict[str, object]:
    if isinstance(source, dict):
        source_record = dict(source)
        source_url = str(source_record.get("url") or source_record.get("url_template") or "").strip()
        source_name = str(source_record.get("source_name") or infer_source_name(source_url or str(source_record))).strip()
    else:
        source_url = source
        source_name = infer_source_name(source)
        source_record = {"source_name": source_name, "url": source, "enabled": True}

    paper_id = safe_slug(source_url or source_name)
    pdf_path = ensure_dir(out_dir / "pdfs") / f"{paper_id}.pdf"
    text_dir = reset_dir(out_dir / "text" / paper_id)

    try:
        downloaded_path, download_error = download_or_copy_source(source_url, pdf_path)
        if download_error:
            try:
                pdf_path.unlink(missing_ok=True)
            except Exception:
                pass
            return {
                "source_name": source_name,
                "paper_id": paper_id,
                "url": source_url,
                "source_record": source_record,
                "local_pdf": None,
                "status": "download_failed",
                "method": "none",
                "pages": 0,
                "page_list": [],
                "text_dir": display_path(text_dir, out_dir),
                "error": download_error,
            }

        pdf_path = downloaded_path or pdf_path
        extracted = extract_text(pdf_path, text_dir, out_dir)
        return {
            "source_name": source_name,
            "paper_id": paper_id,
            "url": source_url,
            "source_record": source_record,
            "local_pdf": None,
            "status": "ok" if extracted.get("status") == "ok" else "extraction_failed",
            "method": str(extracted.get("method") or "none"),
            "pages": int(extracted.get("pages") or 0),
            "page_list": list(extracted.get("page_list") or []),
            "text_dir": display_path(text_dir, out_dir),
            "error": str(extracted.get("reason") or ""),
        }
    finally:
        try:
            pdf_path.unlink(missing_ok=True)
        except Exception:
            pass


def write_results(out_dir: Path, run_date_value: date, inputs: list[dict[str, object]], papers: list[dict[str, object]]) -> Path:
    payload = {
        "run_date": run_date_value.isoformat(),
        "inputs": inputs,
        "papers": papers,
    }
    results_path = out_dir / "results.json"
    ensure_dir(results_path.parent)
    results_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return results_path


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)

    try:
        run_date_value = date.fromisoformat(args.run_date) if args.run_date else date.today()
    except ValueError:
        print(f"Invalid --run-date: {args.run_date}", file=sys.stderr)
        return 2

    urls_path = Path(args.urls) if args.urls else None
    if urls_path is not None and not urls_path.exists():
        print(f"Missing --urls file: {urls_path}", file=sys.stderr)
        return 2

    source_config_path = Path(args.source_config) if args.source_config else None
    if source_config_path is not None and not source_config_path.exists():
        print(f"Missing --source-config file: {source_config_path}", file=sys.stderr)
        return 2

    if not any([args.url, args.urls, args.source_config]):
        print("Provide --url, --urls, or --source-config", file=sys.stderr)
        return 2

    try:
        sources = collect_sources(
            url=args.url or None,
            urls_path=urls_path,
            source_config_path=source_config_path,
            run_date=run_date_value,
        )
    except (ValueError, json.JSONDecodeError) as exc:
        if source_config_path is not None:
            print(f"Invalid --source-config: {source_config_path} ({exc})", file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 2

    if not sources:
        print("No sources found", file=sys.stderr)
        return 2

    papers: list[dict[str, object]] = []
    for source in sources:
        print(f"Processing: {source['url']}", file=sys.stderr)
        papers.append(process_paper(source, out_dir))

    results_path = write_results(out_dir, run_date_value, sources, papers)
    print(f"Wrote {results_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
