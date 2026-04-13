#!/usr/bin/env python3
from __future__ import annotations

import argparse
import asyncio
import base64
import json
import logging
import re
from html.parser import HTMLParser
from io import BytesIO
from pathlib import Path
from typing import Any


logger = logging.getLogger("weread-text")
if not logger.handlers:
    logging.basicConfig(format="%(message)s", level=logging.INFO)

BLOCK_TAGS = {
    "address",
    "article",
    "aside",
    "blockquote",
    "br",
    "div",
    "dl",
    "dt",
    "dd",
    "figcaption",
    "figure",
    "footer",
    "h1",
    "h2",
    "h3",
    "h4",
    "h5",
    "h6",
    "header",
    "hr",
    "li",
    "main",
    "nav",
    "ol",
    "p",
    "pre",
    "section",
    "table",
    "tbody",
    "td",
    "th",
    "thead",
    "tr",
    "ul",
}


class TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag.lower() == "br":
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        stripped = data.strip()
        if not stripped:
            if self.parts and not self.parts[-1].endswith((" ", "\n")):
                self.parts.append(" ")
            return
        if self.parts and not self.parts[-1].endswith((" ", "\n")):
            self.parts.append(" ")
        self.parts.append(stripped)

    def as_text(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Download WeRead books as chapter-based text")
    subparsers = parser.add_subparsers(dest="command", required=True)

    download_parser = subparsers.add_parser("download", help="Download one book into chapter txt files")
    download_parser.add_argument("book_name", help="Book title to search in the WeRead bookshelf")
    download_parser.add_argument("--out-dir", default="out", help="Root output directory")
    download_parser.add_argument("--headless", action="store_true", help="Run browser in headless mode")
    download_parser.add_argument("--delay", type=float, default=2.0, help="Delay in seconds after chapter switches")
    download_parser.add_argument("--verbose", action="store_true", help="Show progress logs")
    return parser.parse_args(argv)


def slugify(value: str, fallback: str = "book") -> str:
    slug = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-._")
    return slug or fallback


def html_pages_to_text(html_pages: list[str]) -> str:
    parser = TextExtractor()
    for html in html_pages:
        parser.feed(html)
        parser.close()
        parser = _reset_parser(parser)
    text = parser.as_text()
    return text


def _reset_parser(parser: TextExtractor) -> TextExtractor:
    replacement = TextExtractor()
    replacement.parts = parser.parts
    return replacement


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_book_output(
    *,
    book_info: dict[str, Any],
    chapter_infos: list[dict[str, Any]],
    chapter_texts: list[dict[str, Any]],
    out_dir: Path,
) -> Path:
    book_dir = ensure_dir(out_dir / slugify(str(book_info.get("title") or ""), "book"))
    chapters_dir = ensure_dir(book_dir / "chapters")

    metadata = dict(book_info)
    metadata["chapter_count"] = len(chapter_texts)
    (book_dir / "metadata.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    (book_dir / "toc.json").write_text(
        json.dumps(chapter_infos, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    for index, chapter in enumerate(chapter_texts, start=1):
        title = str(chapter.get("title") or f"chapter-{index}")
        filename = f"{index:03d}-{slugify(title, f'chapter-{index}')}.txt"
        (chapters_dir / filename).write_text(str(chapter.get("text") or "").strip() + "\n", encoding="utf-8")

    return book_dir


def _generate_qrcode(base64_str: str) -> None:
    try:
        from PIL import Image
        from pyzbar import pyzbar
        from qrcode import QRCode
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "Headless login requires pillow, pyzbar, and qrcode. "
            "Install them or run without --headless."
        ) from exc

    image = Image.open(BytesIO(base64.b64decode(base64_str)))
    login_url = pyzbar.decode(image)[0].data.decode()
    qrcode = QRCode()
    qrcode.add_data(data=login_url)
    qrcode.print_ascii(invert=False)


async def _launch_browser(headless: bool):
    try:
        from pyppeteer import launch
    except ModuleNotFoundError as exc:
        raise RuntimeError("pyppeteer is required. Install it with `pip install pyppeteer`.") from exc

    browser = await launch(headless=headless, logLevel="ERROR")
    page = await browser.newPage()
    await page.goto("https://weread.qq.com/#login")

    if headless:
        logger.info("The QR code expires in about 60 seconds.")
        elements = await page.xpath('//img[@alt="扫码登录"]')
        if not elements:
            await browser.close()
            raise RuntimeError("Could not find the WeRead login QR code.")
        image_base64 = await (await elements[0].getProperty("src")).jsonValue()
        _generate_qrcode(str(image_base64)[22:])

    await page.waitForSelector(".wr_avatar.navBar_avatar")
    logger.info("Login successful.")
    return browser, page


async def _reader_state(page) -> dict[str, Any]:
    return await page.Jeval(
        "#app",
        """(elm) => {
            return elm.__vue__.$store.state.reader
        }""",
    )


async def _open_book(page, book_name: str) -> dict[str, Any]:
    await page.click(".bookshelf_preview_header_link")
    book_links = await page.xpath('//a[@class="shelfBook"]')
    for link in book_links:
        text = await (await link.getProperty("text")).jsonValue()
        if book_name in str(text):
            href = await (await link.getProperty("href")).jsonValue()
            await page.goto(str(href))
            return await _reader_state(page)
    raise RuntimeError(f'Could not find "{book_name}" in the bookshelf.')


async def download_book_text(
    *,
    book_name: str,
    out_dir: Path,
    headless: bool = False,
    delay: float = 2.0,
    verbose: bool = False,
) -> Path:
    browser = None
    try:
        browser, page = await _launch_browser(headless=headless)
        state = await _open_book(page, book_name)
        book_info = dict(state["bookInfo"])
        chapter_infos = list(state["chapterInfos"])
        chapter_texts: list[dict[str, Any]] = []

        for index, chapter in enumerate(chapter_infos, start=1):
            chapter_uid = chapter["chapterUid"]
            await page.Jeval(
                "#routerView",
                """(elm, uid) => {
                    elm.__vue__.changeChapter({ chapterUid: uid })
                }""",
                chapter_uid,
            )
            await asyncio.sleep(delay)
            chapter_state = await _reader_state(page)
            title = str(chapter.get("title") or chapter_state["currentChapter"].get("title") or f"chapter-{index}")
            text = html_pages_to_text(list(chapter_state.get("chapterContentHtml") or []))
            chapter_texts.append(
                {
                    "chapter_uid": chapter_uid,
                    "title": title,
                    "text": text,
                }
            )
            if verbose:
                logger.info("Downloaded chapter %s: %s", index, title)

        result_dir = write_book_output(
            book_info=book_info,
            chapter_infos=chapter_infos,
            chapter_texts=chapter_texts,
            out_dir=out_dir,
        )
        logger.info("Saved chapter text to %s", result_dir)
        return result_dir
    finally:
        if browser is not None:
            await browser.close()


def run_cli(argv: list[str] | None = None) -> int:
    args = parse_args(argv or [])
    if args.command == "download":
        asyncio.run(
            download_book_text(
                book_name=args.book_name,
                out_dir=Path(args.out_dir),
                headless=args.headless,
                delay=args.delay,
                verbose=args.verbose,
            )
        )
        return 0
    raise SystemExit(2)


def main() -> int:
    return run_cli()


if __name__ == "__main__":
    raise SystemExit(main())
