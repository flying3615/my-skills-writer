import importlib.util
import json
import io
import unittest
from contextlib import redirect_stderr
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock


EXTRACT_MODULE_PATH = Path("/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/extract.py")


def load_extract_module():
    spec = importlib.util.spec_from_file_location("daily_press_extract", EXTRACT_MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class SourceConfigTests(unittest.TestCase):
    def setUp(self):
        self.extract = load_extract_module()

    def test_collect_sources_expands_source_config_with_run_date(self):
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sources.json"
            config_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "source_name": "New York Times",
                                "url_template": "https://example.com/nyt-{month}-{day}.pdf",
                                "edition": "international",
                            },
                            {
                                "source_name": "Disabled",
                                "url_template": "https://example.com/disabled-{month}-{day}.pdf",
                                "enabled": False,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            sources = self.extract.collect_sources(
                url=None,
                urls_path=None,
                source_config_path=config_path,
                run_date=date(2026, 3, 29),
            )

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["source_name"], "New York Times")
        self.assertEqual(sources[0]["edition"], "international")
        self.assertEqual(sources[0]["run_date"], "2026-03-29")
        self.assertEqual(sources[0]["url"], "https://example.com/nyt-3-29.pdf")


class ProcessPaperTests(unittest.TestCase):
    def setUp(self):
        self.extract = load_extract_module()

    def test_process_paper_resets_existing_text_dir_before_writing(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            source = {
                "source_name": "New York Times",
                "url": "https://example.com/nyt-3-29.pdf",
            }
            paper_id = self.extract.safe_slug(source["url"])
            stale_dir = out_dir / "text" / paper_id
            stale_dir.mkdir(parents=True, exist_ok=True)
            stale_file = stale_dir / "page-999.txt"
            stale_file.write_text("stale", encoding="utf-8")
            fake_pdf = Path(tmpdir) / "downloaded.pdf"
            fake_pdf.write_text("pdf placeholder", encoding="utf-8")

            with (
                mock.patch.object(self.extract, "download_or_copy_source", return_value=(fake_pdf, None)),
                mock.patch.object(
                    self.extract,
                    "extract_text",
                    return_value={
                        "status": "ok",
                        "method": "pdftotext",
                        "pages": 1,
                        "page_list": [{"page": 1, "path": f"text/{paper_id}/page-001.txt", "chars": 12}],
                    },
                ),
            ):
                result = self.extract.process_paper(source, out_dir)
                self.assertFalse(stale_file.exists())

        self.assertEqual(result["text_dir"], f"text/{paper_id}")

    def test_process_paper_deletes_downloaded_pdf_after_extraction(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            fake_pdf = Path(tmpdir) / "downloaded.pdf"
            fake_pdf.write_text("pdf placeholder", encoding="utf-8")

            with (
                mock.patch.object(self.extract, "download_or_copy_source", return_value=(fake_pdf, None)),
                mock.patch.object(
                    self.extract,
                    "extract_text",
                    return_value={
                        "status": "ok",
                        "method": "pdftotext",
                        "pages": 1,
                        "page_list": [{"page": 1, "path": "text/paper/page-001.txt", "chars": 12}],
                    },
                ),
            ):
                result = self.extract.process_paper(
                    {
                        "source_name": "New York Times",
                        "url": "https://example.com/nyt-3-29.pdf",
                        "edition": "international",
                    },
                    out_dir,
                )

        self.assertFalse(fake_pdf.exists())
        self.assertIsNone(result["local_pdf"])
        self.assertEqual(result["status"], "ok")

    def test_process_paper_returns_stable_metadata(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            fake_pdf = Path(tmpdir) / "downloaded.pdf"
            fake_pdf.write_text("pdf placeholder", encoding="utf-8")

            with (
                mock.patch.object(self.extract, "download_or_copy_source", return_value=(fake_pdf, None)),
                mock.patch.object(
                    self.extract,
                    "extract_text",
                    return_value={
                        "status": "ok",
                        "method": "pymupdf",
                        "pages": 2,
                        "page_list": [
                            {"page": 1, "path": "text/nyt/page-001.txt", "chars": 100},
                            {"page": 2, "path": "text/nyt/page-002.txt", "chars": 120},
                        ],
                    },
                ),
            ):
                result = self.extract.process_paper(
                    {
                        "source_name": "New York Times",
                        "url": "https://example.com/nyt-3-29.pdf",
                        "edition": "international",
                        "run_date": "2026-03-29",
                    },
                    out_dir,
                )

        self.assertEqual(result["source_name"], "New York Times")
        self.assertEqual(result["url"], "https://example.com/nyt-3-29.pdf")
        self.assertEqual(result["source_record"]["edition"], "international")
        self.assertEqual(result["pages"], 2)
        self.assertEqual(result["method"], "pymupdf")
        self.assertEqual(result["text_dir"], f"text/{result['paper_id']}")
        self.assertIsInstance(result["page_list"], list)
        self.assertEqual(result["page_list"][0]["page"], 1)
        self.assertEqual(result["page_list"][0]["path"], "text/nyt/page-001.txt")

    def test_process_paper_removes_partial_pdf_when_download_fails(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)

            def fake_download(_source, dest):
                dest.write_text("partial pdf", encoding="utf-8")
                return None, "download failed"

            with mock.patch.object(self.extract, "download_or_copy_source", side_effect=fake_download):
                result = self.extract.process_paper(
                    {
                        "source_name": "New York Times",
                        "url": "https://example.com/nyt-3-29.pdf",
                    },
                    out_dir,
                )

            self.assertEqual(result["status"], "download_failed")
            self.assertFalse((out_dir / "pdfs" / f"{result['paper_id']}.pdf").exists())

    def test_safe_slug_is_stable_for_same_input(self):
        first = self.extract.safe_slug("https://example.com/nyt-3-29.pdf")
        second = self.extract.safe_slug("https://example.com/nyt-3-29.pdf")

        self.assertEqual(first, second)
        self.assertRegex(first, r"^nyt-3-29-[0-9a-f]{10}$")


class MainTests(unittest.TestCase):
    def setUp(self):
        self.extract = load_extract_module()

    def test_main_writes_results_json_with_stable_paper_metadata(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            stderr = io.StringIO()
            process_result = {
                "source_name": "New York Times",
                "paper_id": "nyt-abc123",
                "url": "https://example.com/nyt-3-29.pdf",
                "source_record": {
                    "source_name": "New York Times",
                    "url": "https://example.com/nyt-3-29.pdf",
                    "run_date": "2026-03-29",
                },
                "local_pdf": None,
                "status": "ok",
                "method": "pdftotext",
                "pages": 1,
                "page_list": [{"page": 1, "path": "text/nyt-abc123/page-001.txt", "chars": 24}],
                "text_dir": "text/nyt-abc123",
                "error": "",
            }

            with mock.patch.object(self.extract, "process_paper", return_value=process_result):
                with mock.patch(
                    "sys.argv",
                    [
                        "extract.py",
                        "--url",
                        "https://example.com/nyt-3-29.pdf",
                        "--out-dir",
                        str(out_dir),
                        "--run-date",
                        "2026-03-29",
                    ],
                ), redirect_stderr(stderr):
                    exit_code = self.extract.main()

            self.assertEqual(exit_code, 0)
            payload = json.loads((out_dir / "results.json").read_text(encoding="utf-8"))

        self.assertEqual(payload["run_date"], "2026-03-29")
        self.assertEqual(payload["papers"], [process_result])
        self.assertEqual(payload["inputs"][0]["url"], "https://example.com/nyt-3-29.pdf")


if __name__ == "__main__":
    unittest.main()
