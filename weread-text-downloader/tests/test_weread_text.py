import asyncio
import importlib.util
import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


SCRIPT_PATH = Path("/Users/yufei/Documents/git/my-skill-writer/weread-text-downloader/scripts/weread_text.py")


def load_module():
    spec = importlib.util.spec_from_file_location("weread_text_downloader", SCRIPT_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class HtmlToTextTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_html_pages_to_text_preserves_chapter_text_with_block_breaks(self):
        html_pages = [
            "<section><h1>Chapter One</h1><p>First paragraph.</p><p>Second paragraph.</p></section>",
            "<section><p>Third paragraph.</p></section>",
        ]

        text = self.module.html_pages_to_text(html_pages)

        self.assertIn("Chapter One", text)
        self.assertIn("First paragraph.", text)
        self.assertIn("Second paragraph.", text)
        self.assertIn("Third paragraph.", text)
        self.assertNotIn("<p>", text)


class OutputWriterTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_write_book_output_creates_metadata_toc_and_chapter_files(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            result_dir = self.module.write_book_output(
                book_info={
                    "title": "Sample Book",
                    "bookId": "book-123",
                    "author": "Test Author",
                },
                chapter_infos=[
                    {"chapterUid": 1, "title": "Opening"},
                    {"chapterUid": 2, "title": "Ending"},
                ],
                chapter_texts=[
                    {"chapter_uid": 1, "title": "Opening", "text": "Opening text."},
                    {"chapter_uid": 2, "title": "Ending", "text": "Ending text."},
                ],
                out_dir=out_dir,
            )

            metadata = json.loads((result_dir / "metadata.json").read_text(encoding="utf-8"))
            toc = json.loads((result_dir / "toc.json").read_text(encoding="utf-8"))
            chapter_files = sorted((result_dir / "chapters").glob("*.txt"))

        self.assertEqual(result_dir.name, "sample-book")
        self.assertEqual(metadata["title"], "Sample Book")
        self.assertEqual(metadata["author"], "Test Author")
        self.assertEqual(len(toc), 2)
        self.assertEqual(chapter_files[0].name, "001-opening.txt")
        self.assertEqual(chapter_files[1].name, "002-ending.txt")


class CliTests(unittest.TestCase):
    def setUp(self):
        self.module = load_module()

    def test_run_cli_routes_download_command(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "books"

            async def fake_download(**kwargs):
                return out_dir / "sample-book"

            with mock.patch.object(self.module, "download_book_text", side_effect=fake_download) as mocked:
                exit_code = self.module.run_cli(
                    ["download", "Sample Book", "--out-dir", str(out_dir), "--headless", "--verbose"]
                )

        self.assertEqual(exit_code, 0)
        self.assertEqual(mocked.call_count, 1)
        called = mocked.call_args.kwargs
        self.assertEqual(called["book_name"], "Sample Book")
        self.assertEqual(called["out_dir"], out_dir)
        self.assertTrue(called["headless"])
        self.assertTrue(called["verbose"])
        self.assertEqual(called["delay"], 2.0)


if __name__ == "__main__":
    unittest.main()
