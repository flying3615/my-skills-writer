#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
import shutil
import zipfile
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
from xml.etree import ElementTree as ET


CONTAINER_NS = {"container": "urn:oasis:names:tc:opendocument:xmlns:container"}
OPF_NS = {
    "opf": "http://www.idpf.org/2007/opf",
    "dc": "http://purl.org/dc/elements/1.1/",
}

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


class XHTMLTextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self.headings: list[str] = []
        self._tag_stack: list[str] = []
        self._current_heading: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        normalized = tag.lower()
        self._tag_stack.append(normalized)
        if normalized == "br":
            self.parts.append("\n")
        if normalized in {"h1", "h2", "h3"}:
            self._current_heading = []

    def handle_endtag(self, tag: str) -> None:
        normalized = tag.lower()
        if normalized in {"h1", "h2", "h3"} and self._current_heading is not None:
            heading = "".join(self._current_heading).strip()
            if heading:
                self.headings.append(heading)
            self._current_heading = None
        if normalized in BLOCK_TAGS:
            self.parts.append("\n")
        if self._tag_stack:
            self._tag_stack.pop()

    def handle_data(self, data: str) -> None:
        if not data.strip():
            if self.parts and not self.parts[-1].endswith((" ", "\n")):
                self.parts.append(" ")
            return
        if self.parts and not self.parts[-1].endswith((" ", "\n")):
            self.parts.append(" ")
        self.parts.append(data.strip())
        if self._current_heading is not None:
            if self._current_heading and not self._current_heading[-1].endswith(" "):
                self._current_heading.append(" ")
            self._current_heading.append(data.strip())

    def as_text(self) -> str:
        text = "".join(self.parts)
        text = re.sub(r"[ \t]+\n", "\n", text)
        text = re.sub(r"\n{3,}", "\n\n", text)
        text = re.sub(r"[ \t]{2,}", " ", text)
        return text.strip()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract text and structure from an EPUB file")
    parser.add_argument("--epub", required=True, help="Path to the .epub file")
    parser.add_argument("--out-dir", required=True, help="Directory for extracted output")
    return parser.parse_args()


def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path


def reset_dir(path: Path) -> Path:
    shutil.rmtree(path, ignore_errors=True)
    path.mkdir(parents=True, exist_ok=True)
    return path


def slugify(value: str, fallback: str) -> str:
    normalized = re.sub(r"[^A-Za-z0-9._-]+", "-", value.strip().lower()).strip("-._")
    return normalized or fallback


def parse_xml(archive: zipfile.ZipFile, path: str) -> ET.Element:
    with archive.open(path) as handle:
        return ET.parse(handle).getroot()


def read_text_file(archive: zipfile.ZipFile, path: str) -> str:
    with archive.open(path) as handle:
        return handle.read().decode("utf-8", errors="replace")


def resolve_opf_path(archive: zipfile.ZipFile) -> str:
    container_root = parse_xml(archive, "META-INF/container.xml")
    rootfile = container_root.find("container:rootfiles/container:rootfile", CONTAINER_NS)
    if rootfile is None:
        raise ValueError("EPUB container.xml does not define a rootfile")
    full_path = rootfile.attrib.get("full-path", "").strip()
    if not full_path:
        raise ValueError("EPUB rootfile is missing full-path")
    return full_path


def join_epub_path(base_path: str, href: str) -> str:
    return str((PurePosixPath(base_path).parent / href).as_posix())


def extract_metadata(package_root: ET.Element) -> dict[str, str]:
    metadata_root = package_root.find("opf:metadata", OPF_NS)
    if metadata_root is None:
        return {"title": "", "creator": "", "language": "", "identifier": ""}
    return {
        "title": (metadata_root.findtext("dc:title", default="", namespaces=OPF_NS) or "").strip(),
        "creator": (metadata_root.findtext("dc:creator", default="", namespaces=OPF_NS) or "").strip(),
        "language": (metadata_root.findtext("dc:language", default="", namespaces=OPF_NS) or "").strip(),
        "identifier": (metadata_root.findtext("dc:identifier", default="", namespaces=OPF_NS) or "").strip(),
    }


def extract_manifest(package_root: ET.Element, opf_path: str) -> dict[str, dict[str, str]]:
    manifest: dict[str, dict[str, str]] = {}
    manifest_root = package_root.find("opf:manifest", OPF_NS)
    if manifest_root is None:
        return manifest
    for item in manifest_root.findall("opf:item", OPF_NS):
        item_id = item.attrib.get("id", "").strip()
        href = item.attrib.get("href", "").strip()
        if not item_id or not href:
            continue
        manifest[item_id] = {
            "href": href,
            "path": join_epub_path(opf_path, href),
            "media_type": item.attrib.get("media-type", "").strip(),
            "properties": item.attrib.get("properties", "").strip(),
        }
    return manifest


def extract_spine(package_root: ET.Element) -> list[str]:
    spine_root = package_root.find("opf:spine", OPF_NS)
    if spine_root is None:
        return []
    itemrefs: list[str] = []
    for itemref in spine_root.findall("opf:itemref", OPF_NS):
        item_id = itemref.attrib.get("idref", "").strip()
        if item_id:
            itemrefs.append(item_id)
    return itemrefs


def extract_toc(archive: zipfile.ZipFile, manifest: dict[str, dict[str, str]], nav_item_id: str | None) -> list[dict[str, str]]:
    if not nav_item_id or nav_item_id not in manifest:
        return []
    nav_path = manifest[nav_item_id]["path"]
    root = parse_xml(archive, nav_path)
    toc: list[dict[str, str]] = []
    for element in root.iter():
        if element.tag.endswith("a"):
            href = (element.attrib.get("href") or "").strip()
            label = "".join(element.itertext()).strip()
            if href and label:
                toc.append({"label": label, "href": href})
    return toc


def pick_nav_item_id(manifest: dict[str, dict[str, str]]) -> str | None:
    for item_id, item in manifest.items():
        if "nav" in item.get("properties", "").split():
            return item_id
    return None


def extract_document_text(xhtml: str) -> tuple[str, str]:
    parser = XHTMLTextExtractor()
    parser.feed(xhtml)
    parser.close()
    title = parser.headings[0] if parser.headings else ""
    return title, parser.as_text()


def title_from_toc(toc: list[dict[str, str]], href: str) -> str:
    target = href.split("#", 1)[0]
    for item in toc:
        if item["href"].split("#", 1)[0] == target:
            return item["label"]
    return ""


def extract_book(epub_path: Path) -> dict[str, object]:
    with zipfile.ZipFile(epub_path) as archive:
        opf_path = resolve_opf_path(archive)
        package_root = parse_xml(archive, opf_path)
        metadata = extract_metadata(package_root)
        manifest = extract_manifest(package_root, opf_path)
        spine = extract_spine(package_root)
        nav_item_id = pick_nav_item_id(manifest)
        toc = extract_toc(archive, manifest, nav_item_id)

        chapters: list[dict[str, object]] = []
        for index, item_id in enumerate(spine, start=1):
            item = manifest.get(item_id)
            if item is None:
                continue
            if "xhtml" not in item["media_type"] and "html" not in item["media_type"]:
                continue
            xhtml = read_text_file(archive, item["path"])
            heading_title, text = extract_document_text(xhtml)
            href = item["href"]
            title = title_from_toc(toc, href) or heading_title or Path(href).stem.replace("-", " ").strip()
            chapters.append(
                {
                    "index": index,
                    "id": item_id,
                    "href": href,
                    "source_path": item["path"],
                    "title": title,
                    "text": text,
                    "chars": len(text),
                }
            )

    return {
        "metadata": metadata,
        "toc": toc,
        "chapters": chapters,
    }


def write_output(book: dict[str, object], out_dir: Path) -> None:
    reset_dir(out_dir)
    chapters_dir = ensure_dir(out_dir / "chapters")

    metadata = dict(book["metadata"])
    metadata["chapter_count"] = len(book["chapters"])
    (out_dir / "metadata.json").write_text(json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (out_dir / "toc.json").write_text(json.dumps(book["toc"], ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    chapter_manifest: list[dict[str, object]] = []
    for chapter in book["chapters"]:
        index = int(chapter["index"])
        title = str(chapter["title"])
        filename = f"{index:03d}-{slugify(title, f'chapter-{index}')}.txt"
        chapter_path = chapters_dir / filename
        chapter_path.write_text(str(chapter["text"]).strip() + "\n", encoding="utf-8")
        chapter_manifest.append(
            {
                "index": index,
                "title": title,
                "href": chapter["href"],
                "source_path": chapter["source_path"],
                "path": f"chapters/{filename}",
                "chars": chapter["chars"],
            }
        )

    (out_dir / "chapters.json").write_text(json.dumps(chapter_manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    args = parse_args()
    epub_path = Path(args.epub)
    if not epub_path.exists():
        raise SystemExit(f"EPUB not found: {epub_path}")

    out_dir = Path(args.out_dir)
    book = extract_book(epub_path)
    write_output(book, out_dir)
    print(f"Extracted {len(book['chapters'])} chapters to {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
