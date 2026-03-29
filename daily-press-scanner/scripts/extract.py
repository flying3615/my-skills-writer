#!/usr/bin/env python3
"""Lightweight PDF text extractor for translated Chinese newspapers.

Only does: download → extract text layer → write page-level text files.
Article identification and summarization is left to the AI agent.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import ssl as _ssl
import sys
from datetime import date
from pathlib import Path
from urllib.parse import unquote, urlparse
from urllib.request import Request, urlopen


def safe_slug(s: str) -> str:
    return hashlib.md5(s.encode()).hexdigest()[:12]


def infer_source_name(url: str) -> str:
    name = Path(urlparse(url).path).stem
    return unquote(name) if name else "unknown"


def download_pdf(url: str, dest: Path) -> tuple[Path | None, str | None]:
    """Download PDF with SSL fallback."""
    try:
        dest.parent.mkdir(parents=True, exist_ok=True)
        req = Request(url, headers={"User-Agent": "Mozilla/5.0"})
        ctx = _ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = _ssl.CERT_NONE
        with urlopen(req, timeout=120, context=ctx) as resp, dest.open("wb") as f:
            shutil.copyfileobj(resp, f)
        return dest, None
    except Exception as e:
        return None, str(e)


def extract_text_pymupdf(pdf_path: Path, text_dir: Path) -> dict:
    """Extract text using PyMuPDF, write page-level files."""
    try:
        import pymupdf
    except ImportError:
        return {"status": "error", "reason": "pymupdf not installed (pip install pymupdf)"}

    doc = pymupdf.open(str(pdf_path))
    text_dir.mkdir(parents=True, exist_ok=True)
    pages = []
    for i, page in enumerate(doc, start=1):
        text = page.get_text()
        out_path = text_dir / f"page-{i:03d}.txt"
        out_path.write_text(text, encoding="utf-8")
        pages.append({"page": i, "path": str(out_path), "chars": len(text)})
    doc.close()
    return {"status": "ok", "pages": len(pages), "page_list": pages}


def extract_text_pdftotext(pdf_path: Path, text_dir: Path) -> dict:
    """Extract text using pdftotext (poppler), write page-level files."""
    import subprocess
    import tempfile
    text_dir.mkdir(parents=True, exist_ok=True)

    # Extract all text with form-feed page separators
    with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
        tmp_path = tmp.name
    try:
        result = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", str(pdf_path), tmp_path],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            return {"status": "error", "reason": result.stderr.strip() or "pdftotext failed"}

        raw = Path(tmp_path).read_text(encoding="utf-8", errors="replace")
        page_texts = raw.split("\f")
        pages = []
        for i, pt in enumerate(page_texts, start=1):
            pt = pt.strip()
            if not pt:
                continue
            out_path = text_dir / f"page-{i:03d}.txt"
            out_path.write_text(pt, encoding="utf-8")
            pages.append({"page": i, "path": str(out_path), "chars": len(pt)})
        return {"status": "ok", "pages": len(pages), "page_list": pages}
    except FileNotFoundError:
        return {"status": "unavailable", "reason": "pdftotext not found"}
    except subprocess.TimeoutExpired:
        return {"status": "error", "reason": "pdftotext timed out"}
    finally:
        Path(tmp_path).unlink(missing_ok=True)


def extract_text(pdf_path: Path, text_dir: Path) -> dict:
    """Try pdftotext first, fallback to pymupdf."""
    result = extract_text_pdftotext(pdf_path, text_dir)
    if result["status"] == "ok":
        result["method"] = "pdftotext"
        return result
    # Fallback to pymupdf
    result2 = extract_text_pymupdf(pdf_path, text_dir)
    if result2["status"] == "ok":
        result2["method"] = "pymupdf"
        result2["pdftotext_status"] = result.get("status")
        result2["pdftotext_reason"] = result.get("reason")
        return result2
    return {"status": "error", "reason": f"pdftotext: {result.get('reason')}; pymupdf: {result2.get('reason')}"}


def process_one(url: str, out_dir: Path) -> dict:
    paper_slug = safe_slug(url)
    source_name = infer_source_name(url)
    pdf_dir = out_dir / "pdfs"
    text_dir = out_dir / "text" / paper_slug

    # Download
    pdf_path = pdf_dir / f"{paper_slug}.pdf"
    dl_path, dl_err = download_pdf(url, pdf_path)
    if dl_err:
        return {"source_name": source_name, "url": url, "status": "download_failed", "error": dl_err}
    pdf_path = dl_path or pdf_path

    # Extract text
    ext = extract_text(pdf_path, text_dir)
    return {
        "source_name": source_name,
        "url": url,
        "status": "ok" if ext["status"] == "ok" else "extraction_failed",
        "method": ext.get("method", "none"),
        "pages": ext.get("pages", 0),
        "page_list": ext.get("page_list", []),
        "text_dir": str(text_dir),
        "error": ext.get("reason"),
    }


def main():
    parser = argparse.ArgumentParser(description="Extract text from translated newspaper PDFs")
    parser.add_argument("--urls", type=Path, help="File with one URL per line")
    parser.add_argument("--url", type=str, help="Single PDF URL")
    parser.add_argument("--out-dir", type=Path, default="./out", help="Output directory")
    parser.add_argument("--run-date", type=str, default=None, help="Run date (YYYY-MM-DD)")
    args = parser.parse_args()

    if args.run_date:
        args.out_dir = args.out_dir / args.run_date

    urls = []
    if args.url:
        urls.append(args.url)
    elif args.urls:
        urls = [l.strip() for l in args.urls.read_text().splitlines() if l.strip()]
    else:
        parser.error("Provide --url or --urls")

    results = []
    for url in urls:
        print(f"Processing: {url}", file=sys.stderr)
        r = process_one(url, args.out_dir)
        results.append(r)
        status = r.get("status", "unknown")
        method = r.get("method", "none")
        pages = r.get("pages", 0)
        print(f"  → {status} ({method}, {pages} pages)", file=sys.stderr)

    out_path = args.out_dir / "results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"run_date": args.run_date, "papers": results}, ensure_ascii=False, indent=2))
    print(f"\nWrote {out_path}", file=sys.stderr)


if __name__ == "__main__":
    main()
