import importlib.util
import json
import subprocess
import sys
import unittest
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory


SCRIPT_PATH = Path("/Users/yufei/Documents/git/my-skill-writer/reading-vault-builder/scripts/extract_epub.py")


def load_module():
    spec = importlib.util.spec_from_file_location("reading_vault_extract_epub", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def write_minimal_epub(epub_path: Path) -> None:
    with zipfile.ZipFile(epub_path, "w") as archive:
        archive.writestr("mimetype", "application/epub+zip")
        archive.writestr(
            "META-INF/container.xml",
            """<?xml version="1.0" encoding="UTF-8"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>
""",
        )
        archive.writestr(
            "OEBPS/content.opf",
            """<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" version="3.0" unique-identifier="bookid">
  <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
    <dc:title>Sample EPUB</dc:title>
    <dc:creator>Test Author</dc:creator>
    <dc:language>en</dc:language>
    <dc:identifier id="bookid">urn:uuid:test-book</dc:identifier>
  </metadata>
  <manifest>
    <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
    <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
    <item id="chapter2" href="chapter2.xhtml" media-type="application/xhtml+xml"/>
  </manifest>
  <spine>
    <itemref idref="chapter1"/>
    <itemref idref="chapter2"/>
  </spine>
</package>
""",
        )
        archive.writestr(
            "OEBPS/nav.xhtml",
            """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <nav epub:type="toc" xmlns:epub="http://www.idpf.org/2007/ops">
      <ol>
        <li><a href="chapter1.xhtml">Chapter 1</a></li>
        <li><a href="chapter2.xhtml">Chapter 2</a></li>
      </ol>
    </nav>
  </body>
</html>
""",
        )
        archive.writestr(
            "OEBPS/chapter1.xhtml",
            """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <h1>Chapter 1</h1>
    <p>First paragraph.</p>
    <p>Another sentence.</p>
  </body>
</html>
""",
        )
        archive.writestr(
            "OEBPS/chapter2.xhtml",
            """<?xml version="1.0" encoding="utf-8"?>
<html xmlns="http://www.w3.org/1999/xhtml">
  <body>
    <h1>Chapter 2</h1>
    <p>Second chapter text.</p>
  </body>
</html>
""",
        )


class ExtractEpubModuleTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_extract_book_reads_metadata_and_spine_documents(self):
        with TemporaryDirectory() as tmpdir:
            epub_path = Path(tmpdir) / "sample.epub"
            write_minimal_epub(epub_path)

            book = self.module.extract_book(epub_path)

        self.assertEqual(book["metadata"]["title"], "Sample EPUB")
        self.assertEqual(book["metadata"]["creator"], "Test Author")
        self.assertEqual(book["metadata"]["language"], "en")
        self.assertEqual(len(book["chapters"]), 2)
        self.assertEqual(book["chapters"][0]["title"], "Chapter 1")
        self.assertIn("First paragraph.", book["chapters"][0]["text"])
        self.assertEqual(book["toc"][1]["label"], "Chapter 2")


class ExtractEpubCliTests(unittest.TestCase):
    def test_cli_writes_metadata_toc_and_chapter_text_files(self):
        with TemporaryDirectory() as tmpdir:
            epub_path = Path(tmpdir) / "sample.epub"
            out_dir = Path(tmpdir) / "out"
            write_minimal_epub(epub_path)

            completed = subprocess.run(
                [sys.executable, str(SCRIPT_PATH), "--epub", str(epub_path), "--out-dir", str(out_dir)],
                capture_output=True,
                text=True,
                check=False,
            )

            self.assertEqual(completed.returncode, 0, completed.stderr)

            metadata = json.loads((out_dir / "metadata.json").read_text(encoding="utf-8"))
            toc = json.loads((out_dir / "toc.json").read_text(encoding="utf-8"))
            chapter_files = sorted((out_dir / "chapters").glob("*.txt"))
            first_chapter_text = chapter_files[0].read_text(encoding="utf-8")

            self.assertEqual(metadata["title"], "Sample EPUB")
            self.assertEqual(metadata["creator"], "Test Author")
            self.assertEqual(len(toc), 2)
            self.assertEqual(len(chapter_files), 2)
            self.assertEqual(chapter_files[0].name, "001-chapter-1.txt")
            self.assertIn("First paragraph.", first_chapter_text)


if __name__ == "__main__":
    unittest.main()
