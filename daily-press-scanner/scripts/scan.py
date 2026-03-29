#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
import unicodedata
import xml.etree.ElementTree as ET
from collections import Counter
from datetime import date
from pathlib import Path
from typing import Iterable
from urllib.parse import unquote, urlparse
import ssl as _ssl
from urllib.request import Request, urlopen

try:
    from pypdf import PdfReader  # type: ignore
except Exception:
    PdfReader = None

try:
    from PIL import Image, ImageFilter, ImageOps  # type: ignore
except Exception:
    Image = None
    ImageFilter = None
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
    "tariffs": (
        "tariff",
        "tariffs",
        "trade",
        "duties",
        "duty",
        "import",
        "imports",
        "export",
        "exports",
        "关税",
        "贸易",
        "进口",
        "出口",
    ),
    "ai": (
        "ai",
        "artificial intelligence",
        "machine learning",
        "nvidia",
        "openai",
        "model",
        "models",
        "chip",
        "chips",
        "人工智能",
        "机器学习",
        "模型",
        "芯片",
    ),
    "china": (
        "china",
        "chinese",
        "beijing",
        "xi",
        "xi jinping",
        "yuan",
        "property",
        "manufacturing",
        "中国",
        "北京",
        "习近平",
        "人民币",
        "制造业",
    ),
    "fed": (
        "fed",
        "federal reserve",
        "powell",
        "rates",
        "inflation",
        "interest rate",
        "interest rates",
        "美联储",
        "鲍威尔",
        "利率",
        "通胀",
        "降息",
        "加息",
    ),
    "war": (
        "war",
        "missile",
        "strike",
        "gaza",
        "ukraine",
        "iran",
        "israel",
        "russia",
        "conflict",
        "战争",
        "导弹",
        "打击",
        "加沙",
        "乌克兰",
        "伊朗",
        "以色列",
        "俄罗斯",
        "冲突",
    ),
    "markets": (
        "market",
        "markets",
        "stocks",
        "stock",
        "bonds",
        "yields",
        "equities",
        "shares",
        "wall street",
        "市场",
        "股市",
        "债券",
        "收益率",
        "华尔街",
        "股票",
    ),
}

REVIEW_MIN_TOPIC_SCORE = 0.5


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local daily press PDF scanner")
    parser.add_argument("--urls", default="", help="Path to a text file with one PDF URL or local path per line")
    parser.add_argument("--out-dir", required=True, help="Output directory")
    parser.add_argument("--source-config", default="", help="Optional JSON config with translated PDF URL templates")
    parser.add_argument("--run-date", default="", help="Optional run date in YYYY-MM-DD format")
    parser.add_argument("--topics", default="", help="Optional comma-separated topic list")
    parser.add_argument("--max-pages", type=int, default=30, help="Optional page cap per paper")
    parser.add_argument("--dpi", type=int, default=300, help="Render DPI for pdftoppm")
    return parser.parse_args()


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


def resolve_translated_source_urls(
    sources: list[dict[str, object]],
    run_date: date,
) -> list[dict[str, object]]:
    resolved_sources: list[dict[str, object]] = []
    for source in sources:
        url_template = str(source.get("url_template", "")).strip()
        if not url_template:
            continue
        url = url_template.format(month=run_date.month, day=run_date.day, year=run_date.year, date=run_date.isoformat())
        resolved_source = dict(source)
        resolved_source["url"] = url
        resolved_source["run_date"] = run_date.isoformat()
        resolved_sources.append(resolved_source)
    return resolved_sources


def score_text_layer_output(text: str) -> float:
    normalized = normalize_text(text)
    if not normalized:
        return 0.0

    visible_chars = sum(1 for ch in normalized if not ch.isspace())
    line_count = sum(1 for line in normalized.splitlines() if line.strip())
    cjk_chars = sum(1 for ch in normalized if "\u4e00" <= ch <= "\u9fff")
    latin_chars = sum(1 for ch in normalized if ch.isalpha() and ch.isascii())

    score = 0.0
    if visible_chars >= 200:
        score += 0.35
    elif visible_chars >= 80:
        score += 0.25
    elif visible_chars >= 20:
        score += 0.1

    if line_count >= 10:
        score += 0.25
    elif line_count >= 4:
        score += 0.15
    elif line_count >= 2:
        score += 0.05

    if cjk_chars >= 100:
        score += 0.35
    elif cjk_chars >= 30:
        score += 0.25
    elif cjk_chars >= 8:
        score += 0.15

    if latin_chars >= 120:
        score += 0.2
    elif latin_chars >= 40:
        score += 0.1

    if cjk_chars and latin_chars:
        score += 0.05

    return round(min(1.0, score), 3)


def _extract_text_with_pymupdf(pdf_path: Path) -> dict[str, object]:
    """Fallback text extraction using PyMuPDF when pdftotext is unavailable."""
    try:
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        page_texts = []
        for page in doc:
            page_texts.append(page.get_text())
        doc.close()
        # Join with form-feed to match pdftotext page separation convention
        raw_text = "\f".join(page_texts)
        text = normalize_text(raw_text)
        visible_chars = sum(1 for ch in text if not ch.isspace())
        line_count = sum(1 for line in text.splitlines() if line.strip())
        score = score_text_layer_output(text)
        return {"status": "available", "reason": "pymupdf fallback", "score": score,
                "char_count": visible_chars, "line_count": line_count, "text": text,
                "raw_text": raw_text}
    except Exception as exc:
        return {"status": "unavailable", "reason": f"pymupdf failed: {exc}",
                "score": 0.0, "char_count": 0, "line_count": 0, "text": ""}


def extract_text_layer(pdf_path: Path) -> dict[str, object]:
    try:
        result = run_command(["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), "-"])
    except FileNotFoundError:
        return _extract_text_with_pymupdf(pdf_path)
    except subprocess.CalledProcessError as exc:
        return {
            "status": "unavailable",
            "reason": exc.stderr.strip() or exc.stdout.strip() or "pdftotext failed",
            "score": 0.0,
            "char_count": 0,
            "line_count": 0,
            "text": "",
        }

    raw_text = result.stdout.replace("\r\n", "\n").replace("\r", "\n")
    text = normalize_text(raw_text)
    visible_chars = sum(1 for ch in text if not ch.isspace())
    line_count = sum(1 for line in text.splitlines() if line.strip())
    score = score_text_layer_output(text)
    if visible_chars == 0:
        return {
            "status": "unavailable",
            "reason": "empty text layer",
            "score": score,
            "char_count": 0,
            "line_count": line_count,
            "text": "",
            "raw_text": "",
        }
    if score < 0.2:
        return {
            "status": "unavailable",
            "reason": "text layer too sparse",
            "score": score,
            "char_count": visible_chars,
            "line_count": line_count,
            "text": text,
            "raw_text": raw_text,
        }
    return {
        "status": "available",
        "reason": "",
        "score": score,
        "char_count": visible_chars,
        "line_count": line_count,
        "text": text,
        "raw_text": raw_text,
    }


def split_text_layer_pages(raw_text: str) -> list[tuple[int, str]]:
    pages: list[tuple[int, str]] = []
    for page_number, raw_page in enumerate(raw_text.replace("\r\n", "\n").replace("\r", "\n").split("\f"), start=1):
        page_text = normalize_layout_page_text(raw_page)
        if page_text:
            pages.append((page_number, page_text))
    return pages


def write_text_layer_artifacts(raw_text: str, text_dir: Path) -> dict[int, Path]:
    ensure_dir(text_dir)
    paths: dict[int, Path] = {}
    for page_number, page_text in split_text_layer_pages(raw_text):
        page_path = text_dir / f"page-{page_number:03d}.txt"
        page_path.write_text(page_text + "\n", encoding="utf-8")
        paths[page_number] = page_path
    return paths


def collect_sources(
    *,
    urls_path: Path | None,
    source_config_path: Path | None,
    run_date: date,
) -> list[dict[str, object]]:
    if source_config_path is not None:
        translated_sources = load_translated_source_config(source_config_path)
        return resolve_translated_source_urls(translated_sources, run_date)

    if urls_path is None:
        return []

    collected: list[dict[str, object]] = []
    for raw_source in read_source_lines(urls_path):
        collected.append(
            {
                "source_name": infer_source_name(raw_source),
                "url": raw_source,
                "enabled": True,
            }
        )
    return collected


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


def display_path(path: Path, base_dir: Path) -> str:
    try:
        return str(path.relative_to(base_dir))
    except ValueError:
        return str(path)


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
            ctx = _ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = _ssl.CERT_NONE
            with urlopen(request, timeout=60, context=ctx) as response, dest.open("wb") as handle:
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


def ocr_image(image_path: Path, *, psm: int = 6) -> str:
    cmd = ["tesseract", str(image_path), "stdout", "-l", "eng", "--psm", str(psm)]
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


def normalize_layout_page_text(text: str) -> str:
    lines: list[str] = []
    for raw_line in text.replace("\x0c", "\n").replace("\r\n", "\n").replace("\r", "\n").splitlines():
        clean = raw_line.rstrip()
        if not clean.strip():
            if lines and lines[-1] != "":
                lines.append("")
            continue
        lines.append(clean)
    while lines and lines[0] == "":
        lines.pop(0)
    while lines and lines[-1] == "":
        lines.pop()
    return "\n".join(lines)


def strip_article_page_furniture(text: str) -> str:
    normalized = normalize_text(text)
    if not normalized:
        return ""

    furniture_patterns = (
        r"^《[^》]{1,40}》$",
        r"^第\d+\s*版$",
        r"^\d{4}年\d{1,2}月\d{1,2}日[，,].*$",
        r"^星期[一二三四五六日天].*$",
        r"^天气$",
        r"^今日[，,].*$",
        r"^今晚[，,].*$",
        r"^明天[，,].*$",
        r"^英国\s+\d+(?:\.\d+)?\s+英镑.*$",
        r"^爱尔兰共和国\s+\d+(?:\.\d+)?\s+欧元.*$",
        r"^\$\d+(?:\.\d+)?$",
        r"^加拿大地区价格可能较高$",
        r"^VOL\.\s*CLXXV.*$",
        r"^No\.\s*\d+.*$",
    )

    lines: list[str] = []
    for raw_line in normalized.splitlines():
        clean = raw_line.strip()
        if not clean:
            continue
        lowered = clean.lower()
        if lowered in {"weather", "the weather"}:
            continue
        if any(re.fullmatch(pattern, clean) for pattern in furniture_patterns):
            continue
        if clean in {"《纽约时报》", "《金融时报》"}:
            continue
        if clean.startswith("天气图见"):
            continue
        lines.append(clean)
    return normalize_text("\n".join(lines))


def compact_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def count_cjk_chars(text: str) -> int:
    return sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")


def normalize_article_title(title: str) -> str:
    normalized = unicodedata.normalize("NFKC", title or "")
    translation = str.maketrans(
        {
            "“": '"',
            "”": '"',
            "„": '"',
            "‟": '"',
            "‘": "'",
            "’": "'",
            "‚": "'",
            "‛": "'",
            "：": ":",
            "，": ",",
            "；": ";",
            "？": "?",
            "！": "!",
            "（": "(",
            "）": ")",
            "【": "[",
            "】": "]",
            "《": "<",
            "》": ">",
            "—": "-",
            "–": "-",
            "―": "-",
            "…": "...",
        }
    )
    normalized = normalized.translate(translation)
    normalized = re.sub(r"\s*:\s*", ":", normalized)
    normalized = re.sub(r"\s*;\s*", ";", normalized)
    normalized = re.sub(r"\s*,\s*", ",", normalized)
    normalized = re.sub(r"\s*\?\s*", "?", normalized)
    normalized = re.sub(r"\s*!\s*", "!", normalized)
    normalized = re.sub(r"\s*-\s*", "-", normalized)
    normalized = re.sub(r"\.{3,}", "...", normalized)
    return compact_text(normalized)


def build_article_id(
    *,
    paper_id: str,
    page: int,
    title_normalized: str,
    block_kind: str,
    block_index: int,
) -> str:
    seed = "|".join(
        [
            str(paper_id or ""),
            str(page or 0),
            str(block_kind or ""),
            str(block_index or 0),
            title_normalized,
        ]
    )
    digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:12]
    return f"{paper_id}:p{page}:{block_kind}:{block_index}:{digest}"


def build_article_lookup_keys(article_id: str, paper_id: str, page: int, title_normalized: str, block_kind: str, block_index: int) -> list[str]:
    keys = [
        article_id,
        f"paper_id:{paper_id}",
        f"page:{page}",
    ]
    if title_normalized:
        keys.append(f"title:{title_normalized}")
    keys.append(f"block:{block_kind}:{block_index}")
    return keys


def merge_article_lookup_keys(
    existing_keys: object,
    article_id: str,
    paper_id: str,
    page: int,
    title_normalized: str,
    block_kind: str,
    block_index: int,
) -> list[str]:
    merged: list[str] = []
    if isinstance(existing_keys, list):
        merged.extend(str(item) for item in existing_keys if str(item).strip())
    for key in build_article_lookup_keys(article_id, paper_id, page, title_normalized, block_kind, block_index):
        if key not in merged:
            merged.append(key)
    return merged


def compute_article_priority_score(article: dict[str, object]) -> float:
    explicit_priority = article.get("priority_score")
    if explicit_priority is not None:
        try:
            return round(float(explicit_priority), 3)
        except (TypeError, ValueError):
            pass
    score = 0.0
    page = int(article.get("page", 0) or 0)
    title = str(article.get("title_guess") or article.get("title") or "").strip()
    body_text = str(article.get("body_text", "")).strip()
    byline = str(article.get("byline", "")).strip()
    block_kind = str(article.get("block_kind", "")).strip()
    importance_hints = [str(item) for item in article.get("importance_hints", []) if str(item).strip()]
    topic_tags = [str(item) for item in article.get("topic_tags", []) if str(item).strip()]

    if title:
        score += 2.0
    if body_text:
        score += min(len(body_text), 1200) / 600.0
    if byline:
        score += 0.6
    for hint in importance_hints:
        if hint == "headline":
            score += 2.5
        elif hint.startswith("topic:"):
            score += 1.0
        elif hint.startswith("section:"):
            score += 0.75
        elif hint == "front_pages":
            score += 1.0
        elif hint == "long_body":
            score += 0.5
    if topic_tags:
        score += min(1.5, 0.35 * len(topic_tags))
    if page > 0:
        score += max(0.0, 10.0 - min(page, 10)) * 0.15
    if block_kind == "article_block":
        score += 1.2
    elif block_kind == "page_fallback":
        score -= 0.3
    elif block_kind == "service_block":
        score -= 3.0
    if any(marker in body_text for marker in ("订阅", "客户服务", "服务指南", "nytimes.com", "音频", "视频", "互动报道")):
        score -= 2.0
    noisy_title_markers = (
        "NEW YORK TIMES",
        "路透社",
        "美联社",
        "图片来源",
        "内容速递",
        "读者专栏",
        "迷你纵横字谜",
        ".com",
        ".org",
        "___",
    )
    if any(marker in title for marker in noisy_title_markers):
        score -= 4.0
    if re.search(r"\b[A-Z]\d+\b", title):
        score -= 2.5
    if len(re.findall(r"\d+", title)) >= 3:
        score -= 3.0
    if not byline and not topic_tags:
        score -= 1.0
    return round(score, 3)


def enrich_article_record(article: dict[str, object]) -> dict[str, object]:
    enriched = dict(article)
    paper_id = str(enriched.get("paper_id", "") or "")
    page = int(enriched.get("page", 0) or 0)
    block_kind = str(enriched.get("block_kind", "") or "page_fallback")
    block_index = int(enriched.get("block_index", 0) or 0)
    title_guess = str(enriched.get("title_guess") or enriched.get("title") or "").strip()
    title = normalize_article_title(str(enriched.get("title") or title_guess))
    title_normalized = normalize_article_title(str(enriched.get("title_normalized") or title))
    article_id = str(enriched.get("article_id") or "").strip()
    if not article_id:
        article_id = build_article_id(
            paper_id=paper_id,
            page=page,
            title_normalized=title_normalized,
            block_kind=block_kind,
            block_index=block_index,
        )
    lookup_keys = enriched.get("lookup_keys")
    lookup_keys = merge_article_lookup_keys(
        lookup_keys,
        article_id,
        paper_id,
        page,
        title_normalized,
        block_kind,
        block_index,
    )

    enriched["page"] = page
    enriched["title"] = title
    enriched["title_guess"] = title_guess or title
    enriched["title_normalized"] = title_normalized
    enriched["block_kind"] = block_kind
    enriched["block_index"] = block_index
    enriched["article_id"] = article_id
    enriched["lookup_keys"] = [str(item) for item in lookup_keys if str(item).strip()]
    explicit_priority = enriched.get("priority_score")
    if explicit_priority is None:
        explicit_priority = enriched.get("summary_score")
    if explicit_priority is None:
        priority_score = compute_article_priority_score(enriched)
    else:
        priority_score = round(float(explicit_priority), 3)
    enriched["priority_score"] = priority_score
    return enriched


TRANSLATED_FURNITURE_SUBSTRINGS = (
    "《纽约时报》",
    "《金融时报》",
    "天气图见",
    "报纸及更多内容",
    "今日报刊",
    "内容速递",
    "服务指南",
    "热门在线头条新闻",
    "历史上的今日头条",
    "今日语录",
    "联系客户服务中心",
    "管理您的订阅",
    "提供机密新闻线索",
    "致信编辑",
    "邮寄订阅费率",
    "纽约时报公司",
    "请访问 nytimes.com",
    "欢迎访问 nytimes.com",
    "nytimes.com/campuswide",
    "nytimes.com/podcast",
    "nytimes.com/video",
    "nytimes.com/books",
    "更正 A",
    "填字游戏",
    "迷你纵横字谜",
    "往期字谜答案",
    "今日报刊",
)

TRANSLATED_FURNITURE_EXACT = {
    "天气",
    "服务指南",
    "音频",
    "视频",
    "互动报道",
    "新闻",
    "观点",
    "商业",
    "国内新闻",
    "国际新闻",
    "艺术",
    "体育",
    "趣闻轶事",
    "读者专栏",
    "来自评论论坛",
    "时报内幕",
}

TRANSLATED_NAVIGATION_PATTERNS = (
    r"^下转\s*[A-Z]?\d+版$",
    r"^下接\s*[A-Z]?\d+版$",
    r"^转至\s*[A-Z]?\d+版$",
    r"^见\s*[A-Z]?\d+版$",
    r"^详见\s*[A-Z]?\d+版$",
)


def is_navigation_line(line: str) -> bool:
    clean = compact_text(line)
    return any(re.fullmatch(pattern, clean) for pattern in TRANSLATED_NAVIGATION_PATTERNS)


def is_translated_furniture_line(line: str) -> bool:
    clean = compact_text(line)
    if not clean:
        return True
    lowered = clean.lower()
    if clean in TRANSLATED_FURNITURE_EXACT:
        return True
    if any(fragment in clean for fragment in TRANSLATED_FURNITURE_SUBSTRINGS):
        return True
    if re.fullmatch(r"[A-Z]\d+\s+N\s+《纽约时报》.*", clean):
        return True
    if re.fullmatch(r"[A-Z]\d+\s+\d{4}年\d{1,2}月\d{1,2}日.*", clean):
        return True
    if re.fullmatch(r"^第\s*CLXXV\s*卷.*", clean):
        return True
    if re.fullmatch(r"^\$\d+(?:\.\d+)?$", clean):
        return True
    if re.fullmatch(r"^[A-Z .'-]{3,}$", clean):
        return True
    if lowered.startswith("作者：") or lowered.startswith("by "):
        return False
    if "订阅" in clean or "客户服务" in clean or "广告" in clean:
        return True
    return False


def translated_page_lines(text: str) -> list[str]:
    lines: list[str] = []
    for raw_line in text.replace("\r\n", "\n").replace("\r", "\n").splitlines():
        parts = [compact_text(part) for part in re.split(r"\s{8,}", raw_line.rstrip())]
        segments = [part for part in parts if part]
        if not segments:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        for segment in segments:
            if is_navigation_line(segment) or is_translated_furniture_line(segment):
                if lines and lines[-1] != "":
                    lines.append("")
                continue
            lines.append(segment)
    while lines and lines[-1] == "":
        lines.pop()
    return lines


def is_byline_line(line: str) -> bool:
    clean = compact_text(line)
    return bool(re.fullmatch(r"(作者[:：]\s*.+|By\s+.+)", clean, re.IGNORECASE))


def looks_like_headline(line: str) -> bool:
    clean = compact_text(line)
    if len(clean) < 8 or len(clean) > 42:
        return False
    if clean.endswith("。") and len(clean) > 16:
        return False
    if "——" in clean or clean.startswith("——"):
        return False
    if clean.count("，") >= 2 or clean.count("。") >= 1:
        return False
    if clean.startswith(("作者：", "作者:", "By ")):
        return False
    if any(marker in clean for marker in ("nytimes.com", "@", "http", "请访问", "欢迎访问", "订阅")):
        return False
    if is_translated_furniture_line(clean):
        return False
    if sum(1 for ch in clean if ch.isdigit()) > 4:
        return False
    meaningful_chars = sum(1 for ch in clean if ch.isalpha() or "\u4e00" <= ch <= "\u9fff")
    if meaningful_chars < 6:
        return False
    return True


def looks_like_story_body(line: str) -> bool:
    clean = compact_text(line)
    if len(clean) >= 28:
        return True
    if "——" in clean:
        return True
    if clean.endswith(("。", "？", "！")):
        return True
    return False


def build_translated_block(title_lines: list[str], byline: str, body_lines: list[str], block_index: int) -> dict[str, object] | None:
    title = compact_text(" ".join(title_lines))
    body_text = normalize_text("\n".join(body_lines))
    if not title or len(body_text) < 60:
        return None
    return {
        "block_index": block_index,
        "block_kind": "article_block",
        "title": title,
        "byline": byline,
        "body_text": body_text,
        "text": normalize_text("\n".join([title] + ([byline] if byline else []) + body_lines)),
    }


def bbox_overlap_ratio(left: dict[str, object], right: dict[str, object]) -> float:
    left_min = float(left.get("x_min", 0.0) or 0.0)
    left_max = float(left.get("x_max", 0.0) or 0.0)
    right_min = float(right.get("x_min", 0.0) or 0.0)
    right_max = float(right.get("x_max", 0.0) or 0.0)
    intersection = max(0.0, min(left_max, right_max) - max(left_min, right_min))
    left_width = max(1.0, left_max - left_min)
    right_width = max(1.0, right_max - right_min)
    return intersection / min(left_width, right_width)


def extract_translated_bbox_article_blocks(blocks: list[dict[str, object]], *, page_number: int) -> list[dict[str, object]]:
    if page_number > 10:
        return []

    normalized_blocks: list[dict[str, object]] = []
    for raw_block in blocks:
        text = normalize_text(str(raw_block.get("text", "")))
        if not text or is_navigation_line(text) or is_translated_furniture_line(text):
            continue
        block = dict(raw_block)
        block["text"] = text
        block["x_min"] = float(raw_block.get("x_min", 0.0) or 0.0)
        block["x_max"] = float(raw_block.get("x_max", 0.0) or 0.0)
        block["y_min"] = float(raw_block.get("y_min", 0.0) or 0.0)
        block["y_max"] = float(raw_block.get("y_max", 0.0) or 0.0)
        block["width"] = float(block["x_max"]) - float(block["x_min"])
        block["height"] = float(block["y_max"]) - float(block["y_min"])
        normalized_blocks.append(block)

    body_blocks = [
        block
        for block in sorted(normalized_blocks, key=lambda item: (float(item["x_min"]), float(item["y_min"])))
        if len(str(block["text"])) >= 40
        and float(block["width"]) >= 80.0
        and float(block["height"]) >= 18.0
        and not is_byline_line(str(block["text"]))
        and "图片来源" not in str(block["text"])
        and "来源：" not in str(block["text"])
    ]
    headline_blocks = [
        block
        for block in sorted(normalized_blocks, key=lambda item: (float(item["y_min"]), float(item["x_min"])))
        if looks_like_headline(str(block["text"])) and float(block["height"]) <= 36.0
    ]
    byline_blocks = [
        block
        for block in normalized_blocks
        if is_byline_line(str(block["text"]))
    ]

    clusters: list[list[dict[str, object]]] = []
    for block in body_blocks:
        attached = False
        for cluster in reversed(clusters):
            last = cluster[-1]
            y_gap = float(block["y_min"]) - float(last["y_max"])
            if 0.0 <= y_gap <= 44.0 and bbox_overlap_ratio(block, last) >= 0.55:
                intervening_headline = any(
                    float(last["y_max"]) <= float(headline["y_min"]) <= float(block["y_min"])
                    and bbox_overlap_ratio(headline, block) >= 0.35
                    for headline in headline_blocks
                )
                if intervening_headline:
                    continue
                cluster.append(block)
                attached = True
                break
        if not attached:
            clusters.append([block])

    article_blocks: list[dict[str, object]] = []
    block_index = 0
    bad_title_markers = (
        "图片来源",
        "来源：",
        "读者专栏",
        "来自评论论坛",
        "服务指南",
        "今日语录",
        "互动报道",
        "音频",
        "视频",
        "美联社",
        "NEW YORK TIMES",
        "为《纽约时报》",
    )
    for cluster in clusters:
        body_text = normalize_text("\n".join(str(item["text"]) for item in cluster))
        if len(body_text) < 100:
            continue
        cluster_box = {
            "x_min": min(float(item["x_min"]) for item in cluster),
            "x_max": max(float(item["x_max"]) for item in cluster),
            "y_min": min(float(item["y_min"]) for item in cluster),
            "y_max": max(float(item["y_max"]) for item in cluster),
        }

        matching_headlines = [
            block
            for block in headline_blocks
            if float(block["y_max"]) <= float(cluster_box["y_min"])
            and float(cluster_box["y_min"]) - float(block["y_max"]) <= 120.0
            and bbox_overlap_ratio(block, cluster_box) >= 0.35
        ]
        matching_headlines.sort(key=lambda item: (float(cluster_box["y_min"]) - float(item["y_max"]), -float(item["width"])))
        title = ""
        if matching_headlines:
            nearest = matching_headlines[0]
            grouped_headlines = [
                block
                for block in matching_headlines
                if float(block["y_max"]) <= float(nearest["y_max"])
                and float(nearest["y_min"]) - float(block["y_max"]) <= 60.0
            ]
            grouped_headlines.sort(key=lambda item: (float(item["y_min"]), float(item["x_min"])))
            title = compact_text(" ".join(str(item["text"]) for item in grouped_headlines[:2]))

        matching_bylines = [
            block
            for block in byline_blocks
            if float(block["y_max"]) <= float(cluster_box["y_min"])
            and float(cluster_box["y_min"]) - float(block["y_max"]) <= 70.0
            and bbox_overlap_ratio(block, cluster_box) >= 0.45
        ]
        matching_bylines.sort(key=lambda item: float(cluster_box["y_min"]) - float(item["y_max"]))
        byline = str(matching_bylines[0]["text"]) if matching_bylines else ""

        if not title:
            title = article_title_guess([line.strip() for line in body_text.splitlines() if line.strip()])
        if not title:
            continue
        if any(marker in title for marker in bad_title_markers):
            continue
        if re.search(r"\b[A-Z]\d+\b", title):
            continue
        if len(title) > 72:
            continue
        if not byline and len(body_text) < 220:
            continue

        block_index += 1
        article_blocks.append(
            {
                "block_index": block_index,
                "block_kind": "article_block",
                "title": title,
                "byline": byline,
                "body_text": body_text,
                "text": normalize_text("\n".join(part for part in [title, byline, body_text] if part)),
            }
        )

    deduped: dict[str, dict[str, object]] = {}
    for block in article_blocks:
        title_key = re.sub(r"\s+", " ", str(block.get("title", "")).strip().lower())
        existing = deduped.get(title_key)
        if existing is None or len(str(block.get("body_text", ""))) > len(str(existing.get("body_text", ""))):
            deduped[title_key] = block

    return list(deduped.values())


def extract_translated_article_blocks(text: str, *, page_number: int) -> list[dict[str, object]]:
    if page_number > 10:
        return []

    lines = translated_page_lines(text)
    blocks: list[dict[str, object]] = []
    index = 0
    block_index = 0

    while index < len(lines):
        line = lines[index]
        if not line:
            index += 1
            continue
        if not looks_like_headline(line):
            index += 1
            continue

        title_lines = [line]
        cursor = index + 1
        while cursor < len(lines):
            next_line = lines[cursor]
            if not next_line:
                cursor += 1
                break
            if is_byline_line(next_line) or looks_like_story_body(next_line):
                break
            if looks_like_headline(next_line) and len(title_lines) < 2:
                title_lines.append(next_line)
                cursor += 1
                continue
            break

        byline = ""
        if cursor < len(lines) and is_byline_line(lines[cursor]):
            byline = lines[cursor]
            cursor += 1

        body_lines: list[str] = []
        while cursor < len(lines):
            candidate_line = lines[cursor]
            if not candidate_line:
                if body_lines:
                    cursor += 1
                    break
                cursor += 1
                continue
            if looks_like_headline(candidate_line) and body_lines and len(compact_text(" ".join(body_lines))) >= 80:
                break
            if is_translated_furniture_line(candidate_line) or is_navigation_line(candidate_line):
                cursor += 1
                if body_lines:
                    break
                continue
            body_lines.append(candidate_line)
            cursor += 1

        block_index += 1
        block = build_translated_block(title_lines, byline, body_lines, block_index)
        if block is not None:
            blocks.append(block)
        index = cursor if cursor > index else index + 1

    return blocks


def _extract_bbox_blocks_pymupdf(pdf_path: Path) -> dict[int, list[dict[str, object]]]:
    """Build page blocks from PyMuPDF when pdftotext bbox-layout is unavailable."""
    try:
        import pymupdf
        doc = pymupdf.open(str(pdf_path))
        pages: dict[int, list[dict[str, object]]] = {}
        for page_num, page in enumerate(doc, start=1):
            blocks_data = []
            blocks = page.get_text("blocks")
            for b in blocks:
                x0, y0, x1, y1, text, *_ = b
                text = text.strip()
                if text:
                    blocks_data.append({"text": text, "x_min": x0, "x_max": x1, "y_min": y0, "y_max": y1})
            pages[page_num] = blocks_data
        doc.close()
        return pages
    except Exception:
        return {}

def extract_bbox_page_blocks(pdf_path: Path) -> dict[int, list[dict[str, object]]]:
    namespace = {"x": "http://www.w3.org/1999/xhtml"}
    with tempfile.NamedTemporaryFile(prefix="daily-press-bbox-", suffix=".xml", delete=False) as handle:
        xml_path = Path(handle.name)
    try:
        try:
            run_command(["pdftotext", "-bbox-layout", "-enc", "UTF-8", str(pdf_path), str(xml_path)])
        except FileNotFoundError:
            # pdftotext unavailable; build simple blocks from pymupdf text
            return _extract_bbox_blocks_pymupdf(pdf_path)
        root = ET.fromstring(xml_path.read_text(encoding="utf-8", errors="replace"))
    finally:
        if xml_path.exists():
            xml_path.unlink()

    pages: dict[int, list[dict[str, object]]] = {}
    for page_number, page in enumerate(root.findall(".//x:page", namespace), start=1):
        page_blocks: list[dict[str, object]] = []
        for block in page.findall(".//x:block", namespace):
            words = [word.text or "" for word in block.findall(".//x:word", namespace)]
            text = compact_text(" ".join(words))
            if not text:
                continue
            page_blocks.append(
                {
                    "text": text,
                    "x_min": float(block.attrib.get("xMin", 0.0) or 0.0),
                    "x_max": float(block.attrib.get("xMax", 0.0) or 0.0),
                    "y_min": float(block.attrib.get("yMin", 0.0) or 0.0),
                    "y_max": float(block.attrib.get("yMax", 0.0) or 0.0),
                }
            )
        pages[page_number] = page_blocks
    return pages


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
        weird_penalty = sum(1 for ch in clean if ch in "_|<>~=\\/[]{}") * 0.45
        length_bonus = min(len(clean), 120) / 12.0
        position_bonus = max(0.0, 2.0 - index * 0.1)
        score = length_bonus + position_bonus + upper_ratio * 2.0 - digits * 0.1 - punctuation_penalty - weird_penalty
        lowered = clean.lower()
        if clean.endswith("."):
            score -= 1.2
        if len(clean.split()) >= 5 and not clean.endswith("."):
            score += 0.5
        if len(clean) > 90:
            score -= (len(clean) - 90) / 14.0
        if clean.count(",") >= 2:
            score -= 0.8
        if re.search(r"\bby\b", lowered) and len(clean) > 55:
            score -= 0.5
        if (
            "the new york times" in lowered
            or re.search(r"\b(mon|tues|wednes|thurs|fri|satur|sun)day\b", lowered)
            or "vol." in lowered
            or re.search(r"\bno\.\s*\d+", lowered)
            or re.search(r"\b[a-z]?\s*a\d+\b", lowered)
        ):
            score -= 2.0
        if re.match(r"^[A-Z][A-Z .'-]{2,24}\s+[—-]\s+", clean):
            score -= 1.5
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
        if re.fullmatch(r"by\s+.+", lowered) or re.fullmatch(r"作者[:：]\s*.+", clean):
            continue
        body.append(clean)
        if sum(len(part) for part in body) > 300:
            break
    return compact_text(" ".join(body))[:320]


def extract_byline(text: str) -> str:
    for line in text.splitlines():
        clean = line.strip()
        if not clean:
            continue
        if re.fullmatch(r"作者[:：]\s*.+", clean):
            return clean
        if re.fullmatch(r"(?i)by\s+[A-Z][A-Za-z.' -]{2,80}", clean):
            return clean
    match = re.search(r"(?im)\b(By\s+[A-Z][A-Za-z.' -]{2,80})$", text)
    return match.group(1).strip() if match else ""


def load_page_text(page_record: dict[str, object], out_dir: Path) -> str:
    text_rel = page_record.get("text_path") or ""
    if not text_rel:
        return ""
    text_path = out_dir / str(text_rel)
    if not text_path.exists():
        return ""
    return text_path.read_text(encoding="utf-8")


def build_article_candidate(
    page_record: dict[str, object],
    page_text: str,
    topic_map: dict[str, list[str]],
    *,
    block_kind: str = "page_fallback",
    block_index: int = 0,
    source_page_rank: int = 0,
    title_override: str = "",
    byline_override: str = "",
) -> dict[str, object] | None:
    cleaned_text = strip_article_page_furniture(page_text)
    if not cleaned_text:
        return None

    lines = [line.strip() for line in cleaned_text.splitlines() if line.strip()]
    if not lines:
        return None

    title_guess = title_override or article_title_guess(lines)
    byline = byline_override or extract_byline(cleaned_text)
    title = normalize_article_title(title_guess)
    page = int(page_record.get("page", 0) or 0)
    body_lines = list(lines)
    if title and body_lines and normalize_article_title(body_lines[0]) == title:
        body_lines = body_lines[1:]
    if byline and body_lines and body_lines[0] == byline:
        body_lines = body_lines[1:]
    body_text = normalize_text("\n".join(body_lines))
    snippet = snippet_text(body_lines or lines)
    section = section_guess(body_text or cleaned_text)
    matches = topic_matches(topic_map, body_text or cleaned_text, title_guess, snippet)
    topic_tags = [match["topic"] for match in matches]
    importance_hints: list[str] = []
    if title_guess:
        importance_hints.append("headline")
    if section:
        importance_hints.append(f"section:{section}")
    if len(body_text or cleaned_text) >= 500:
        importance_hints.append("long_body")
    if page <= 3:
        importance_hints.append("front_pages")
    for topic in topic_tags:
        importance_hints.append(f"topic:{topic}")

    return enrich_article_record(
        {
        "source_name": page_record.get("source_name", ""),
        "paper_id": page_record.get("paper_id", ""),
        "url": page_record.get("url", ""),
        "page": page,
        "title": title,
        "title_guess": title_guess,
        "title_normalized": title,
        "byline": byline,
        "body_text": body_text or cleaned_text,
        "section_guess": section,
        "topic_tags": sorted(set(topic_tags)),
        "importance_hints": importance_hints,
        "block_index": block_index,
        "block_kind": block_kind,
        "source_page_rank": source_page_rank,
        "text_path": page_record.get("text_path"),
        "ocr_path": page_record.get("ocr_path"),
        }
    )


def article_title_guess(lines: list[str]) -> str:
    skip_phrases = ("正文", "更多正文", "更多内容", "供AI", "阅读理解", "天气", "简报", "深度阅读")
    for line in lines[:8]:
        clean = line.strip()
        if not clean:
            continue
        if any(phrase in clean for phrase in skip_phrases):
            continue
        if len(clean) > 60:
            continue
        if clean.endswith("。") and len(clean) > 18:
            continue
        return clean
    return title_candidate(lines[:8])


def should_use_text_layer_fast_path(text: str) -> bool:
    visible_text = normalize_text(text)
    if not visible_text:
        return False
    cjk_chars = count_cjk_chars(visible_text)
    ascii_letters = sum(1 for ch in visible_text if ch.isascii() and ch.isalpha())
    return cjk_chars >= 6 and cjk_chars >= max(1, ascii_letters // 2)


def build_text_layer_page_records(
    *,
    source_name: str,
    paper_slug: str,
    source_url: str,
    out_dir: Path,
    page_paths: dict[int, Path],
    bbox_page_blocks: dict[int, list[dict[str, object]]],
    scan_limit: int,
    topic_map: dict[str, list[str]],
) -> list[dict[str, object]]:
    page_index: list[dict[str, object]] = []
    for page_number in range(1, scan_limit + 1):
        text_path = page_paths.get(page_number)
        page_text = ""
        title = ""
        snippet = ""
        matches: list[dict[str, object]] = []
        section = ""
        if text_path is not None:
            page_text = text_path.read_text(encoding="utf-8")
            lines = translated_page_lines(page_text)
            if not lines:
                lines = [line.strip() for line in normalize_text(page_text).splitlines() if line.strip()]
            title = article_title_guess(lines)
            snippet = snippet_text(lines)
            matches = topic_matches(topic_map, page_text, title, snippet)
            section = section_guess(page_text)
        page_index.append(
            {
                "source_name": source_name,
                "paper_id": paper_slug,
                "url": source_url,
                "page": page_number,
                "preview_path": None,
                "ocr_path": None,
                "text_path": display_path(text_path, out_dir) if text_path is not None else None,
                "bbox_blocks": bbox_page_blocks.get(page_number, []),
                "title": title,
                "snippet": snippet,
                "section_guess": section,
                "opinion_score": 0.0,
                "topic_matches": matches,
                "scan_mode": "text_layer",
            }
        )
    return page_index


def build_article_candidates(
    page_index: list[dict[str, object]],
    out_dir: Path,
    topic_map: dict[str, list[str]],
) -> list[dict[str, object]]:
    candidates: list[dict[str, object]] = []
    for page_record in page_index:
        page_text = load_page_text(page_record, out_dir)
        if not page_text:
            continue
        page_number = int(page_record.get("page", 0) or 0)
        if page_number <= 10:
            bbox_blocks = page_record.get("bbox_blocks") or []
            if isinstance(bbox_blocks, list) and bbox_blocks:
                blocks = extract_translated_bbox_article_blocks(bbox_blocks, page_number=page_number)
                for block in blocks:
                    candidate = build_article_candidate(
                        page_record,
                        str(block.get("text", "")),
                        topic_map,
                        block_kind=str(block.get("block_kind", "article_block")),
                        block_index=int(block.get("block_index", 0) or 0),
                        source_page_rank=int(block.get("block_index", 0) or 0),
                        title_override=str(block.get("title", "")),
                        byline_override=str(block.get("byline", "")),
                    )
                    if candidate is not None:
                        candidates.append(candidate)
                if blocks:
                    continue

            blocks = extract_translated_article_blocks(page_text, page_number=page_number)
            for block in blocks:
                candidate = build_article_candidate(
                    page_record,
                    str(block.get("text", "")),
                    topic_map,
                    block_kind=str(block.get("block_kind", "article_block")),
                    block_index=int(block.get("block_index", 0) or 0),
                    source_page_rank=int(block.get("block_index", 0) or 0),
                    title_override=str(block.get("title", "")),
                    byline_override=str(block.get("byline", "")),
                )
                if candidate is not None:
                    candidates.append(candidate)
            if blocks:
                continue

        candidate = build_article_candidate(
            page_record,
            page_text,
            topic_map,
            block_kind="page_fallback",
            block_index=0,
            source_page_rank=0,
        )
        if candidate is not None:
            candidates.append(candidate)
    candidates = [enrich_article_record(candidate) for candidate in candidates]
    candidates.sort(key=lambda item: (-float(item.get("priority_score", 0.0) or 0.0), int(item["page"]), int(item.get("block_index", 0) or 0)))
    return candidates


def write_articles_json(path: Path, run_date: str, articles: list[dict[str, object]]) -> None:
    payload = {
        "run_date": run_date,
        "articles": [enrich_article_record(article) for article in articles],
    }
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def score_summary_candidate(article: dict[str, object]) -> float:
    return compute_article_priority_score(article)


def summarize_article_candidate(article: dict[str, object]) -> dict[str, object]:
    summary_article = enrich_article_record(article)
    body_text = str(article.get("body_text", "")).strip()
    excerpt = str(article.get("summary_text", "")).strip()
    if not excerpt and body_text:
        lines = [line.strip() for line in body_text.splitlines() if line.strip()]
        if lines:
            excerpt = compact_text(" ".join(lines[:2]))[:220]
        else:
            excerpt = compact_text(body_text)[:220]
    summary_article["summary_text"] = excerpt
    summary_article["summary_score"] = float(summary_article.get("priority_score", 0.0) or 0.0)
    return summary_article


def select_summary_articles(
    articles: list[dict[str, object]],
    *,
    min_items: int = 5,
    max_items: int = 10,
) -> list[dict[str, object]]:
    ranked = sorted(
        enumerate(articles),
        key=lambda item: (
            -score_summary_candidate(item[1]),
            int(item[1].get("page", 0) or 0),
            item[0],
        ),
    )
    selected: list[dict[str, object]] = []
    seen_pages: set[int] = set()
    for index, _ in ranked:
        candidate = summarize_article_candidate(articles[index])
        if len(selected) >= min_items and float(candidate.get("summary_score", 0.0) or 0.0) < 9.0:
            break
        page = int(candidate.get("page", 0) or 0)
        if page in seen_pages:
            continue
        seen_pages.add(page)
        selected.append(candidate)
        if len(selected) >= max_items:
            break
    if len(selected) < min_items:
        return selected
    return selected


def render_summary_markdown(summary_payload: dict[str, object]) -> str:
    lines = [f"# Daily Summary {summary_payload['run_date']}", ""]
    for paper in summary_payload.get("papers", []):
        lines.append(f"## {paper.get('source_name') or paper.get('paper_id')}")
        lines.append(
            f"Selected {paper.get('selected_count', 0)} of {paper.get('article_count', 0)} article candidates."
        )
        selected_articles = paper.get("selected_articles", [])
        if selected_articles:
            lines.append("")
            for article in selected_articles:
                page = article.get("page", "")
                title = article.get("title_guess") or "[no title]"
                summary_text = article.get("summary_text") or article.get("body_text") or ""
                topic_tags = ", ".join(article.get("topic_tags", [])) if article.get("topic_tags") else "-"
                lines.append(f"- Page {page}: {title}")
                lines.append(f"  Tags: {topic_tags}")
                if summary_text:
                    lines.append(f"  {summary_text}")
        lines.append("")
    return "\n".join(lines).strip() + "\n"


def build_daily_brief_payload(run_date: date, summary_papers: list[dict[str, object]]) -> dict[str, object]:
    brief_papers: list[dict[str, object]] = []
    for paper in summary_papers:
        brief_articles: list[dict[str, object]] = []
        for article in paper.get("selected_articles", []):
            enriched = enrich_article_record(article)
            brief_articles.append(
                {
                    "article_id": enriched.get("article_id"),
                    "page": int(enriched.get("page", 0) or 0),
                    "title": str(enriched.get("title") or enriched.get("title_guess") or "").strip(),
                    "byline": str(enriched.get("byline") or "").strip(),
                    "priority_score": float(enriched.get("priority_score", 0.0) or 0.0),
                    "summary_text": str(enriched.get("summary_text") or enriched.get("body_text") or "").strip(),
                    "topic_tags": [str(tag) for tag in enriched.get("topic_tags", []) if str(tag).strip()],
                    "text_path": enriched.get("text_path"),
                    "url": enriched.get("url") or paper.get("url"),
                }
            )
        brief_papers.append(
            {
                "source_name": paper.get("source_name") or "",
                "paper_id": paper.get("paper_id") or "",
                "selected_count": len(brief_articles),
                "articles": brief_articles,
            }
        )
    return {
        "run_date": run_date.isoformat(),
        "papers": brief_papers,
    }


def write_summary_outputs(
    out_dir: Path,
    run_date: date,
    paper_results: list[dict[str, object]],
    summary_articles: list[dict[str, object]],
) -> dict[str, object]:
    summary_papers: list[dict[str, object]] = []
    for paper_result in paper_results:
        summary_candidates = list(
            paper_result.get("summary_candidates")
            or paper_result.get("article_candidates")
            or paper_result.get("candidate_articles")
            or []
        )
        selected_articles = list(
            paper_result.get("summary_selected")
            or paper_result.get("selected_articles")
            or []
        )
        if not selected_articles and summary_candidates:
            selected_articles = select_summary_articles(summary_candidates)
        elif selected_articles:
            selected_articles = select_summary_articles(selected_articles)
        summary_papers.append(
            {
                "source_name": paper_result.get("source_name") or paper_result.get("paper", {}).get("source_name", ""),
                "paper_id": paper_result.get("paper_id") or paper_result.get("paper", {}).get("paper_id", ""),
                "url": paper_result.get("url") or paper_result.get("paper", {}).get("url", ""),
                "status": paper_result.get("status") or paper_result.get("paper", {}).get("status", ""),
                "article_count": int(
                    paper_result.get("article_count")
                    or paper_result.get("candidate_count")
                    or len(summary_candidates)
                ),
                "candidate_count": len(summary_candidates),
                "selected_count": len(selected_articles),
                "selected_articles": selected_articles,
            }
        )

    flat_articles: list[dict[str, object]] = []
    for paper in summary_papers:
        flat_articles.extend(list(paper.get("selected_articles", [])))

    payload = {
        "run_date": run_date.isoformat(),
        "papers": summary_papers,
        "articles": flat_articles,
    }
    summary_json_path = out_dir / "summary.json"
    summary_json_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    summary_md_path = out_dir / "summary.md"
    summary_md_path.write_text(render_summary_markdown(payload), encoding="utf-8")
    daily_brief_path = out_dir / "daily_brief.json"
    daily_brief_path.write_text(
        json.dumps(build_daily_brief_payload(run_date, summary_papers), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return payload


def score_ocr_candidate_text(text: str, *, prefer_title: bool = False) -> float:
    normalized = normalize_text(text)
    if not normalized:
        return -999.0
    lowered = normalized.lower()
    lines = [line.strip() for line in normalized.splitlines() if line.strip()]
    title = title_candidate(lines)
    byline = extract_byline(normalized)
    word_count = len(re.findall(r"\b\w+\b", normalized))
    alpha_words = len(re.findall(r"\b[a-zA-Z]{3,}\b", normalized))
    score = 0.0

    if title:
        score += min(len(title), 120) / 24.0
        if title.endswith("."):
            score -= 0.8
    if byline:
        score += 1.2
    if word_count >= 40:
        score += 1.0
    if word_count >= 90:
        score += 0.6
    if alpha_words >= 20:
        score += 0.5
    if prefer_title:
        score += 0.8 if 18 <= len(title) <= 140 else -0.2
    masthead_hits = 0
    for pattern in (
        "the new york times",
        "wednesday, march",
        "vol.",
        "all the news that's fit to print",
    ):
        masthead_hits += lowered.count(pattern)
    score -= masthead_hits * 0.8
    if re.search(r"\b[a-z]?\s*a\d+\b", lowered):
        score -= 0.5
    if re.search(r"\bno\.\s*\d+", lowered):
        score -= 0.4
    return score


def choose_best_ocr_candidate(candidates: list[dict[str, object]], *, prefer_title: bool = False) -> dict[str, object]:
    if not candidates:
        return {"text": "", "psm": None, "variant": "", "score": -999.0}

    best: dict[str, object] | None = None
    best_score = -999.0
    for candidate in candidates:
        text = normalize_text(str(candidate.get("text", "")))
        score = score_ocr_candidate_text(text, prefer_title=prefer_title)
        scored = dict(candidate)
        scored["text"] = text
        scored["score"] = score
        if score > best_score:
            best = scored
            best_score = score
    return best or {"text": "", "psm": None, "variant": "", "score": -999.0}


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
    if " " in term or any(ord(ch) > 127 for ch in term):
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


def select_review_targets(
    opinion_candidates: list[dict[str, object]],
    topic_hits: list[dict[str, object]],
    min_topic_score: float = REVIEW_MIN_TOPIC_SCORE,
) -> list[dict[str, object]]:
    targets: dict[int, dict[str, object]] = {}

    for candidate in opinion_candidates:
        page = int(candidate["page"])
        target = targets.setdefault(
            page,
            {
                "page": page,
                "triggers": [],
                "topic_tags": [],
                "primary_trigger": "opinion",
            },
        )
        if "opinion" not in target["triggers"]:
            target["triggers"].append("opinion")
        target["primary_trigger"] = "opinion"
        for topic in candidate.get("topic_tags", []):
            if topic and topic not in target["topic_tags"]:
                target["topic_tags"].append(topic)

    for hit in topic_hits:
        score = float(hit.get("score", 0.0) or 0.0)
        if score < min_topic_score:
            continue
        page = int(hit["page"])
        topic = str(hit.get("topic", "")).strip()
        if not topic:
            continue
        target = targets.setdefault(
            page,
            {
                "page": page,
                "triggers": [],
                "topic_tags": [],
                "primary_trigger": f"topic:{topic}",
                "primary_score": score,
            },
        )
        trigger = f"topic:{topic}"
        if trigger not in target["triggers"]:
            target["triggers"].append(trigger)
        if topic not in target["topic_tags"]:
            target["topic_tags"].append(topic)
        if target["primary_trigger"] != "opinion" and score >= float(target.get("primary_score", 0.0) or 0.0):
            target["primary_trigger"] = trigger
            target["primary_score"] = score

    results = sorted(targets.values(), key=lambda item: int(item["page"]))
    for item in results:
        item["topic_tags"] = sorted(item["topic_tags"])
        item.pop("primary_score", None)
    return results


def build_review_candidate(
    *,
    source_name: str,
    paper_id: str,
    url: str,
    page: int,
    trigger: str,
    crop_kind: str,
    crop_rank: int,
    title: str,
    snippet: str,
    section_guess: str,
    topic_tags: list[str],
    confidence: float,
    ocr_path: str,
    preview_path: str,
    byline: str = "",
    triggers: list[str] | None = None,
) -> dict[str, object]:
    return {
        "source_name": source_name,
        "paper_id": paper_id,
        "url": url,
        "page": page,
        "trigger": trigger,
        "triggers": list(triggers or [trigger]),
        "crop_kind": crop_kind,
        "crop_rank": crop_rank,
        "title": title,
        "byline": byline,
        "snippet": snippet,
        "section_guess": section_guess,
        "topic_tags": sorted(set(topic_tags)),
        "confidence": round(max(0.0, min(1.0, confidence)), 3),
        "ocr_path": ocr_path,
        "preview_path": preview_path,
    }


def review_crop_specs(image_size: tuple[int, int]) -> list[dict[str, object]]:
    width, height = image_size
    specs = [{"kind": "full", "rank": 0, "box": (0, 0, width, height)}]
    if width >= 1200:
        overlap = max(30, width // 40)
        mid = width // 2
        specs.append({"kind": "left", "rank": 1, "box": (0, 0, min(width, mid + overlap), height)})
        specs.append({"kind": "right", "rank": 2, "box": (max(0, mid - overlap), 0, width, height)})
    if height >= 1800:
        specs.append({"kind": "upper", "rank": 3, "box": (0, 0, width, int(height * 0.6))})
    return specs


def review_confidence(
    text: str,
    title: str,
    snippet: str,
    section: str,
    byline: str,
    matches: list[dict[str, object]],
    triggers: list[str],
) -> float:
    score = 0.0
    word_count = len(re.findall(r"\b\w+\b", text))
    digit_count = len(re.findall(r"\d", text))
    if len(title) >= 20:
        score += 0.2
    elif len(title) >= 10:
        score += 0.1
    if snippet:
        score += 0.1
    if byline:
        score += 0.15
    if section:
        score += 0.15
    if matches:
        score += min(0.2, 0.08 * len(matches))
    if "opinion" in triggers:
        score += 0.15
    if word_count >= 120:
        score += 0.15
    elif word_count >= 60:
        score += 0.08
    if digit_count > max(10, word_count // 5):
        score -= 0.15
    lowered_title = title.lower()
    if lowered_title.startswith("the new york times") or lowered_title.startswith("a") and len(title) < 16:
        score -= 0.08
    return max(0.0, min(1.0, score))


def crop_image_to_path(image_path: Path, box: tuple[int, int, int, int], dest_path: Path) -> Path:
    if Image is None:
        return image_path
    ensure_dir(dest_path.parent)
    with Image.open(image_path) as img:
        left, top, right, bottom = box
        if (left, top, right, bottom) == (0, 0, img.size[0], img.size[1]):
            shutil.copy2(image_path, dest_path)
            return dest_path
        cropped = img.crop((left, top, right, bottom))
        cropped.save(dest_path)
    return dest_path


def review_page_candidates(
    *,
    source_name: str,
    paper_slug: str,
    source: str,
    page_record: dict[str, object],
    target: dict[str, object],
    out_dir: Path,
    topic_map: dict[str, list[str]],
    paper_errors: list[dict[str, object]],
) -> list[dict[str, object]]:
    preview_ref = out_dir / str(page_record["preview_path"])
    base_ocr_ref = out_dir / str(page_record["ocr_path"])
    review_preview_dir = ensure_dir(out_dir / "previews" / paper_slug / "reviews")
    review_ocr_dir = ensure_dir(out_dir / "ocr" / paper_slug / "reviews")
    candidates: list[dict[str, object]] = []

    if not preview_ref.exists():
        paper_errors.append(
            {
                "source": source,
                "paper": paper_slug,
                "page": page_record["page"],
                "stage": "review",
                "message": f"missing preview image: {preview_ref}",
            }
        )
        return candidates

    if Image is None:
        specs = [{"kind": "full", "rank": 0, "box": None}]
    else:
        with Image.open(preview_ref) as img:
            specs = review_crop_specs(img.size)

    with tempfile.TemporaryDirectory(prefix=f"{paper_slug}-review-") as tmp_root:
        tmp_dir = Path(tmp_root)
        for spec in specs:
            crop_kind = str(spec["kind"])
            crop_rank = int(spec["rank"])
            preview_filename = f"page-{int(page_record['page']):03d}-{crop_kind}.png"
            preview_path = review_preview_dir / preview_filename
            ocr_path = review_ocr_dir / f"page-{int(page_record['page']):03d}-{crop_kind}.txt"
            try:
                if spec["box"] is None:
                    crop_preview_path = preview_ref
                else:
                    crop_preview_path = crop_image_to_path(preview_ref, spec["box"], preview_path)
                variants = prepare_ocr_variants(crop_preview_path, tmp_dir / f"{crop_kind}-{crop_rank}")
                texts: list[str] = []
                for variant in variants:
                    best = best_ocr_text_for_image_variant(variant, prefer_title=(crop_kind == "upper"))
                    if best.get("text"):
                        texts.append(str(best["text"]))
                merged_text = merge_ocr_texts(texts)
                if not merged_text:
                    continue
                ocr_path.write_text(merged_text + "\n", encoding="utf-8")
                raw_lines = [line.strip() for line in merged_text.splitlines() if line.strip()]
                title = title_candidate(raw_lines)
                snippet = snippet_text(raw_lines)
                section = section_guess(merged_text)
                byline = extract_byline(merged_text)
                matches = topic_matches(topic_map, merged_text, title, snippet)
                topic_tags = list(target.get("topic_tags", []))
                for match in matches:
                    if match["topic"] not in topic_tags:
                        topic_tags.append(match["topic"])
                confidence = review_confidence(
                    merged_text,
                    title,
                    snippet,
                    section,
                    byline,
                    matches,
                    list(target.get("triggers", [])),
                )
                candidate = build_review_candidate(
                    source_name=source_name,
                    paper_id=paper_slug,
                    url=source,
                    page=int(page_record["page"]),
                    trigger=str(target.get("primary_trigger", "opinion")),
                    triggers=list(target.get("triggers", [])),
                    crop_kind=crop_kind,
                    crop_rank=crop_rank,
                    title=title,
                    byline=byline,
                    snippet=snippet,
                    section_guess=section,
                    topic_tags=topic_tags,
                    confidence=confidence,
                    ocr_path=str(ocr_path.relative_to(out_dir)),
                    preview_path=str(crop_preview_path.relative_to(out_dir)),
                )
                if candidate["title"] or candidate["snippet"]:
                    candidates.append(candidate)
            except Exception as exc:
                paper_errors.append(
                    {
                        "source": source,
                        "paper": paper_slug,
                        "page": page_record["page"],
                        "stage": "review",
                        "message": f"{crop_kind}: {exc}",
                    }
                )

    candidates.sort(key=lambda item: (float(item["confidence"]), -int(item["crop_rank"])), reverse=True)
    best_by_key: dict[tuple[str, str], dict[str, object]] = {}
    for candidate in candidates:
        key = (str(candidate["crop_kind"]), str(candidate["title"]))
        existing = best_by_key.get(key)
        if existing is None or float(candidate["confidence"]) > float(existing["confidence"]):
            best_by_key[key] = candidate
    deduped = sorted(best_by_key.values(), key=lambda item: (float(item["confidence"]), -int(item["crop_rank"])), reverse=True)
    return deduped[:3]


def build_review_fallback_candidate(
    *,
    source_name: str,
    paper_slug: str,
    source: str,
    page_record: dict[str, object],
    target: dict[str, object],
) -> dict[str, object]:
    page_matches = page_record.get("topic_matches", [])
    topic_tags = list(target.get("topic_tags", []))
    for match in page_matches:
        topic = match.get("topic")
        if topic and topic not in topic_tags:
            topic_tags.append(str(topic))
    return build_review_candidate(
        source_name=source_name,
        paper_id=paper_slug,
        url=source,
        page=int(page_record["page"]),
        trigger=str(target.get("primary_trigger", "opinion")),
        triggers=list(target.get("triggers", [])),
        crop_kind="full",
        crop_rank=0,
        title=str(page_record.get("title", "")),
        byline="",
        snippet=str(page_record.get("snippet", "")),
        section_guess=str(page_record.get("section_guess", "")),
        topic_tags=topic_tags,
        confidence=max(float(page_record.get("opinion_score", 0.0) or 0.0), 0.35),
        ocr_path=str(page_record.get("ocr_path", "")),
        preview_path=str(page_record.get("preview_path", "")),
    )


def sharpen_binary_image(gray: "Image.Image") -> "Image.Image":
    if ImageFilter is None:
        return gray
    sharpened = gray.filter(ImageFilter.SHARPEN)
    return sharpened.point(lambda px: 255 if px > 168 else 0)


def maybe_upscale(gray: "Image.Image") -> "Image.Image":
    width, height = gray.size
    if max(width, height) >= 2200:
        return gray
    scale = 1.25
    resample = getattr(Image, "Resampling", Image)
    lanczos = getattr(resample, "LANCZOS", Image.LANCZOS)
    return gray.resize((int(width * scale), int(height * scale)), lanczos)


def save_preprocessed_panel(panel: "Image.Image", panel_name: str, work_dir: Path) -> list[dict[str, object]]:
    ensure_dir(work_dir)
    gray = maybe_upscale(ImageOps.autocontrast(panel.convert("L")))
    binary = sharpen_binary_image(gray)

    variants: list[dict[str, object]] = []
    gray_path = work_dir / f"{panel_name}-gray.png"
    gray.save(gray_path)
    variants.append({"path": gray_path, "panel": panel_name, "variant": "gray"})

    binary_path = work_dir / f"{panel_name}-binary.png"
    binary.save(binary_path)
    variants.append({"path": binary_path, "panel": panel_name, "variant": "binary_sharp"})
    return variants


def prepare_ocr_variants(image_path: Path, work_dir: Path) -> list[dict[str, object]]:
    if Image is None or ImageOps is None:
        return [{"path": image_path, "panel": "full", "variant": "source"}]

    ensure_dir(work_dir)
    variants: list[dict[str, object]] = []
    with Image.open(image_path) as img:
        variants.extend(save_preprocessed_panel(img, "full", work_dir))

        width, height = img.size
        if width >= 1.25 * height and width >= 1400:
            overlap = max(40, width // 40)
            mid = width // 2
            left = img.crop((0, 0, min(width, mid + overlap), height))
            right = img.crop((max(0, mid - overlap), 0, width, height))
            variants.extend(save_preprocessed_panel(left, "left", work_dir))
            variants.extend(save_preprocessed_panel(right, "right", work_dir))
    return variants


def best_ocr_text_for_image_variant(image_variant: dict[str, object], *, prefer_title: bool = False) -> dict[str, object]:
    image_path = Path(str(image_variant["path"]))
    psm_values = [7, 6] if prefer_title else [6, 4]
    candidates: list[dict[str, object]] = []
    for psm in psm_values:
        text = ocr_image(image_path, psm=psm)
        candidates.append(
            {
                "text": text,
                "psm": psm,
                "variant": image_variant.get("variant", ""),
                "panel": image_variant.get("panel", "full"),
                "path": str(image_path),
            }
        )
    return choose_best_ocr_candidate(candidates, prefer_title=prefer_title)


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
    source: str | dict[str, object],
    out_dir: Path,
    dpi: int,
    max_pages: int | None,
    topic_map: dict[str, list[str]],
) -> dict[str, object]:
    if isinstance(source, dict):
        source_record = dict(source)
        source_url = str(source_record.get("url") or source_record.get("url_template") or "").strip()
        source_name = str(source_record.get("source_name") or infer_source_name(source_url or str(source_record))).strip()
    else:
        source_record = {"source_name": infer_source_name(source), "url": source, "enabled": True}
        source_url = source
        source_name = infer_source_name(source)

    paper_slug = safe_slug(source_url or source)
    pdf_dir = ensure_dir(out_dir / "pdfs")
    ocr_dir = ensure_dir(out_dir / "ocr" / paper_slug)
    preview_dir = ensure_dir(out_dir / "previews" / paper_slug)

    pdf_path = pdf_dir / f"{paper_slug}.pdf"
    paper_errors: list[dict[str, object]] = []

    downloaded_path, download_error = download_or_copy_source(source_url or source, pdf_path)
    if download_error:
        return {
            "paper": {
                "source_name": source_name,
                "paper_id": paper_slug,
                "url": source_url or source,
                "source_record": source_record,
                "local_pdf": None,
                "page_count": 0,
                "scanned_pages": 0,
                "status": "download_failed",
                "text_layer_status": "unavailable",
                "text_layer_reason": download_error,
                "text_layer_score": 0.0,
                "text_layer_char_count": 0,
                "text_layer_line_count": 0,
            },
            "page_index": [],
            "opinion_candidates": [],
            "topic_hits": [],
            "review_candidates": [],
            "article_candidates": [],
            "errors": [{"source": source_url or source, "paper": paper_slug, "stage": "download", "message": download_error}],
        }

    pdf_path = downloaded_path or pdf_path
    try:
        page_count, page_count_source = get_page_count(pdf_path)
        if page_count is None:
            page_limit = max_pages if max_pages is not None else 200
            paper_errors.append(
                {
                    "source": source_url or source,
                    "paper": paper_slug,
                    "stage": "page_count",
                    "message": page_count_source or "unknown page count",
                }
            )
        else:
            page_limit = min(page_count, max_pages) if max_pages is not None else page_count

        text_layer = extract_text_layer(pdf_path)
        text_layer_status = str(text_layer.get("status", "unavailable"))
        text_layer_reason = str(text_layer.get("reason", ""))
        text_layer_score = float(text_layer.get("score", 0.0) or 0.0)
        text_layer_char_count = int(text_layer.get("char_count", 0) or 0)
        text_layer_line_count = int(text_layer.get("line_count", 0) or 0)
        text_layer_dir = ensure_dir(out_dir / "text" / paper_slug)
        text_layer_page_paths: dict[int, Path] = {}
        text_layer_page_count = 0
        bbox_page_blocks: dict[int, list[dict[str, object]]] = {}
        raw_text = ""
        use_text_layer_fast_path = False
        if text_layer_status == "available":
            raw_text = str(text_layer.get("raw_text") or text_layer.get("text") or "")
            text_layer_page_paths = write_text_layer_artifacts(raw_text, text_layer_dir)
            text_layer_page_count = len(text_layer_page_paths)
            use_text_layer_fast_path = should_use_text_layer_fast_path(raw_text)
            try:
                bbox_page_blocks = extract_bbox_page_blocks(pdf_path)
            except Exception as exc:
                paper_errors.append(
                    {
                        "source": source_url or source,
                        "paper": paper_slug,
                        "stage": "bbox",
                        "message": str(exc),
                    }
                )
        if text_layer_status != "available":
            paper_errors.append(
                {
                    "source": source_url or source,
                    "paper": paper_slug,
                    "stage": "text_layer",
                    "message": text_layer_reason or "text layer unavailable",
                }
            )

        page_index: list[dict[str, object]] = []
        opinion_candidates: list[dict[str, object]] = []
        topic_hits: list[dict[str, object]] = []
        review_candidates: list[dict[str, object]] = []
        scan_limit = page_limit if page_limit is not None else (max_pages or 200)
        if use_text_layer_fast_path:
            page_index = build_text_layer_page_records(
                source_name=source_name,
                paper_slug=paper_slug,
                source_url=source_url or source,
                out_dir=out_dir,
                page_paths=text_layer_page_paths,
                bbox_page_blocks=bbox_page_blocks,
                scan_limit=scan_limit,
                topic_map=topic_map,
            )
        else:
            with tempfile.TemporaryDirectory(prefix=f"{paper_slug}-") as tmp_root:
                tmp_dir = Path(tmp_root)
                for page_number in range(1, scan_limit + 1):
                    preview_stem = preview_dir / f"page-{page_number:03d}"
                    ocr_path = ocr_dir / f"page-{page_number:03d}.txt"
                    page_record: dict[str, object] = {
                        "source_name": source_name,
                        "paper_id": paper_slug,
                        "url": source_url or source,
                        "page": page_number,
                        "preview_path": str(preview_stem.with_suffix(".png").relative_to(out_dir)),
                        "ocr_path": str(ocr_path.relative_to(out_dir)),
                        "text_path": display_path(text_layer_page_paths[page_number], out_dir) if page_number in text_layer_page_paths else None,
                        "bbox_blocks": bbox_page_blocks.get(page_number, []),
                    }
                    try:
                        image_path = render_page(pdf_path, page_number, preview_stem, dpi)
                        variants = prepare_ocr_variants(image_path, tmp_dir / f"page-{page_number:03d}")
                        variant_texts: list[str] = []
                        ocr_variant_errors = 0
                        for variant in variants:
                            try:
                                best = best_ocr_text_for_image_variant(variant, prefer_title=False)
                                if best.get("text"):
                                    variant_texts.append(str(best["text"]))
                            except Exception as exc:
                                ocr_variant_errors += 1
                                paper_errors.append(
                                    {
                                        "source": source_url or source,
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
                                        "source": source_url or source,
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
                                    "url": source_url or source,
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
                                    "url": source_url or source,
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
                                "source": source_url or source,
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
                                "source": source_url or source,
                                "paper": paper_slug,
                                "page": page_number,
                                "stage": "page",
                                "message": str(exc),
                            }
                        )
                        continue

        page_records = {int(item["page"]): item for item in page_index}
        if not use_text_layer_fast_path:
            for target in select_review_targets(opinion_candidates, topic_hits):
                page_record = page_records.get(int(target["page"]))
                if page_record is None:
                    continue
                reviewed = review_page_candidates(
                    source_name=source_name,
                    paper_slug=paper_slug,
                    source=source_url or source,
                    page_record=page_record,
                    target=target,
                    out_dir=out_dir,
                    topic_map=topic_map,
                    paper_errors=paper_errors,
                )
                if reviewed:
                    review_candidates.extend(reviewed)
                else:
                    review_candidates.append(
                        build_review_fallback_candidate(
                            source_name=source_name,
                            paper_slug=paper_slug,
                            source=source_url or source,
                            page_record=page_record,
                            target=target,
                        )
                    )

        article_candidates = build_article_candidates(page_index, out_dir, topic_map)
        paper_summary = {
            "source_name": source_name,
            "paper_id": paper_slug,
            "url": source_url or source,
            "source_record": source_record,
            "local_pdf": None,
            "page_count": page_count,
            "scanned_pages": len(page_index),
            "status": "ok" if not paper_errors else "ok_with_errors",
            "page_count_source": page_count_source,
            "text_layer_status": text_layer_status,
            "text_layer_reason": text_layer_reason,
            "text_layer_score": text_layer_score,
            "text_layer_char_count": text_layer_char_count,
            "text_layer_line_count": text_layer_line_count,
            "text_layer_dir": display_path(text_layer_dir, out_dir) if text_layer_status == "available" else None,
            "text_layer_page_count": text_layer_page_count,
            "article_count": len(article_candidates),
            "scan_mode": "text_layer" if use_text_layer_fast_path else "ocr",
        }
        write_preview_summary(preview_dir / "summary.txt", paper_summary, page_index, opinion_candidates, topic_hits, review_candidates)
        return {
            "paper": paper_summary,
            "page_index": page_index,
            "opinion_candidates": opinion_candidates,
            "topic_hits": topic_hits,
            "review_candidates": review_candidates,
            "article_candidates": article_candidates,
            "errors": paper_errors,
        }
    finally:
        try:
            if pdf_path.exists():
                pdf_path.unlink()
        except Exception:
            pass


def write_preview_summary(
    path: Path,
    paper_summary: dict[str, object],
    page_index: list[dict[str, object]],
    opinion_candidates: list[dict[str, object]],
    topic_hits: list[dict[str, object]],
    review_candidates: list[dict[str, object]],
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
    review_pages = Counter(item["page"] for item in review_candidates)
    for page in page_index:
        page_num = page["page"]
        hits = [topic for (hit_page, topic), count in topic_pages.items() if hit_page == page_num and count > 0]
        lines.append(
            f"- page {page_num:03d}: {page.get('title') or '[no title]'} | "
            f"opinion={'yes' if page_num in opinion_pages else 'no'} | "
            f"topics={', '.join(sorted(set(hits))) if hits else '-'} | "
            f"reviews={review_pages.get(page_num, 0)}"
        )
        snippet = page.get("snippet")
        if snippet:
            lines.append(f"  snippet: {snippet}")
    if review_candidates:
        lines.extend(["", "review_candidates:"])
        for candidate in review_candidates:
            lines.append(
                f"- page {int(candidate['page']):03d} [{candidate['crop_kind']}] "
                f"{candidate.get('title') or '[no title]'} | trigger={candidate['trigger']} | "
                f"confidence={candidate['confidence']}"
            )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    out_dir = Path(args.out_dir)
    ensure_dir(out_dir)
    ensure_dir(out_dir / "pdfs")
    ensure_dir(out_dir / "ocr")
    ensure_dir(out_dir / "previews")

    try:
        run_date = date.fromisoformat(args.run_date) if args.run_date else date.today()
    except ValueError:
        print(f"Invalid --run-date: {args.run_date}", file=sys.stderr)
        return 2

    source_config_path = Path(args.source_config) if args.source_config else None
    if source_config_path is not None and not source_config_path.exists():
        print(f"Missing --source-config file: {source_config_path}", file=sys.stderr)
        return 2

    urls_path = Path(args.urls) if args.urls else None
    if urls_path is not None and not urls_path.exists():
        print(f"Missing --urls file: {urls_path}", file=sys.stderr)
        return 2

    if source_config_path is None and urls_path is None:
        print("Provide either --urls or --source-config", file=sys.stderr)
        return 2

    try:
        sources = collect_sources(urls_path=urls_path, source_config_path=source_config_path, run_date=run_date)
    except (ValueError, json.JSONDecodeError) as exc:
        if source_config_path is not None:
            print(f"Invalid --source-config: {source_config_path} ({exc})", file=sys.stderr)
        else:
            print(str(exc), file=sys.stderr)
        return 2

    if not sources:
        source_label = "--source-config" if args.source_config else "--urls"
        print(f"No sources found in {source_label}", file=sys.stderr)
        return 2

    topic_map = normalize_topic_terms(args.topics)
    results: dict[str, object] = {
        "run_date": run_date.isoformat(),
        "inputs": sources,
        "papers": [],
        "page_index": [],
        "opinion_candidates": [],
        "topic_hits": [],
        "review_candidates": [],
        "articles": [],
        "summary": {},
        "errors": [],
    }
    paper_results: list[dict[str, object]] = []

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
        results["review_candidates"].extend(paper_result["review_candidates"])
        results["articles"].extend(paper_result.get("article_candidates", []))
        results["errors"].extend(paper_result["errors"])
        paper_results.append(paper_result)

    summary_papers: list[dict[str, object]] = []
    summary_articles: list[dict[str, object]] = []
    for paper_result in paper_results:
        paper_info = dict(paper_result["paper"])
        paper_articles = [item for item in paper_result.get("article_candidates", []) if item.get("paper_id") == paper_info.get("paper_id")]
        selected_articles = select_summary_articles(paper_articles)
        paper_info["candidate_count"] = len(paper_articles)
        paper_info["selected_count"] = len(selected_articles)
        paper_info["summary_candidates"] = paper_articles
        paper_info["summary_selected"] = selected_articles
        summary_papers.append(paper_info)
        summary_articles.extend(selected_articles)

    summary_payload = write_summary_outputs(out_dir, run_date, summary_papers, summary_articles)
    results["summary"] = summary_payload

    results_path = out_dir / "results.json"
    results_path.write_text(json.dumps(results, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    articles_path = out_dir / "articles.json"
    write_articles_json(articles_path, run_date.isoformat(), list(results["articles"]))
    print(f"Wrote {results_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
