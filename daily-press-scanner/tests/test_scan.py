import importlib.util
import json
import unittest
from datetime import date
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
from contextlib import redirect_stderr
import io


MODULE_PATH = Path("/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py")


def load_scan_module():
    spec = importlib.util.spec_from_file_location("daily_press_scan", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


class ReviewTargetSelectionTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_select_review_targets_merges_opinion_and_high_score_topics(self):
        opinion_candidates = [
            {"page": 2, "confidence": 0.8},
            {"page": 3, "confidence": 0.7},
        ]
        topic_hits = [
            {"page": 3, "topic": "ai", "score": 0.7},
            {"page": 8, "topic": "war", "score": 1.0},
            {"page": 10, "topic": "markets", "score": 0.4},
        ]

        targets = self.scan.select_review_targets(opinion_candidates, topic_hits, min_topic_score=0.5)

        self.assertEqual([item["page"] for item in targets], [2, 3, 8])
        self.assertEqual(targets[0]["triggers"], ["opinion"])
        self.assertEqual(targets[1]["triggers"], ["opinion", "topic:ai"])
        self.assertEqual(targets[2]["triggers"], ["topic:war"])

    def test_select_review_targets_keeps_unique_topic_tags_per_page(self):
        targets = self.scan.select_review_targets(
            opinion_candidates=[],
            topic_hits=[
                {"page": 9, "topic": "war", "score": 0.8},
                {"page": 9, "topic": "war", "score": 0.9},
                {"page": 9, "topic": "china", "score": 0.7},
            ],
            min_topic_score=0.5,
        )

        self.assertEqual(len(targets), 1)
        self.assertEqual(targets[0]["page"], 9)
        self.assertEqual(targets[0]["topic_tags"], ["china", "war"])

    def test_select_review_targets_uses_highest_scoring_topic_as_primary_trigger(self):
        targets = self.scan.select_review_targets(
            opinion_candidates=[],
            topic_hits=[
                {"page": 1, "topic": "war", "score": 1.0},
                {"page": 1, "topic": "china", "score": 0.5},
            ],
            min_topic_score=0.5,
        )

        self.assertEqual(targets[0]["primary_trigger"], "topic:war")


class ReviewCandidateFormattingTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_build_review_candidate_includes_required_fields(self):
        candidate = self.scan.build_review_candidate(
            source_name="The New York Times",
            paper_id="nyt-2026-03-25",
            url="https://example.com/nyt.pdf",
            page=8,
            trigger="topic:war",
            crop_kind="left",
            crop_rank=1,
            title="Iran Sustains Attacks Across the Middle East",
            snippet="Iran sustained attacks across the region, targeting six countries.",
            section_guess="analysis",
            topic_tags=["war"],
            confidence=0.88,
            ocr_path="previews/nyt/reviews/page-008-left.txt",
            preview_path="previews/nyt/reviews/page-008-left.png",
            byline="By Example Reporter",
        )

        self.assertEqual(candidate["page"], 8)
        self.assertEqual(candidate["trigger"], "topic:war")
        self.assertEqual(candidate["crop_kind"], "left")
        self.assertEqual(candidate["crop_rank"], 1)
        self.assertEqual(candidate["title"], "Iran Sustains Attacks Across the Middle East")
        self.assertEqual(candidate["byline"], "By Example Reporter")
        self.assertEqual(candidate["topic_tags"], ["war"])
        self.assertEqual(candidate["ocr_path"], "previews/nyt/reviews/page-008-left.txt")
        self.assertEqual(candidate["preview_path"], "previews/nyt/reviews/page-008-left.png")

    def test_build_review_candidate_defaults_to_full_page_fallback(self):
        candidate = self.scan.build_review_candidate(
            source_name="The New York Times",
            paper_id="nyt-2026-03-25",
            url="https://example.com/nyt.pdf",
            page=3,
            trigger="opinion",
            crop_kind="full",
            crop_rank=0,
            title="Reader Corner",
            snippet="Have you used A.I. for advice on a romantic relationship?",
            section_guess="analysis",
            topic_tags=["ai", "china"],
            confidence=0.64,
            ocr_path="ocr/nyt/page-003.txt",
            preview_path="previews/nyt/page-003.png",
        )

        self.assertEqual(candidate["crop_kind"], "full")
        self.assertEqual(candidate["crop_rank"], 0)
        self.assertEqual(candidate["byline"], "")
        self.assertEqual(candidate["section_guess"], "analysis")


class TitleExtractionTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_title_candidate_prefers_article_headline_over_masthead(self):
        lines = [
            "THE NEW YORK TIMES INTERNATIONAL WEDNESDAY, MARCH 25, 2026 N A7",
            "Saudi Prince Said to Urge U.S. to Continue Iran War",
            "By JULIAN E. BARNES",
            "WASHINGTON — Saudi Arabia's de facto leader has been pushing President Trump.",
        ]

        title = self.scan.title_candidate(lines)

        self.assertEqual(title, "Saudi Prince Said to Urge U.S. to Continue Iran War")


class CliDefaultsTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_parse_args_defaults_max_pages_to_30(self):
        with mock.patch(
            "sys.argv",
            [
                "scan.py",
                "--urls",
                "/tmp/urls.txt",
                "--out-dir",
                "/tmp/out",
            ],
        ):
            args = self.scan.parse_args()

        self.assertEqual(args.max_pages, 30)

    def test_parse_args_defaults_dpi_to_300(self):
        with mock.patch(
            "sys.argv",
            [
                "scan.py",
                "--urls",
                "/tmp/urls.txt",
                "--out-dir",
                "/tmp/out",
            ],
        ):
            args = self.scan.parse_args()

        self.assertEqual(args.dpi, 300)


class SourceConfigTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_load_translated_source_config_skips_disabled_sources(self):
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sources.json"
            config_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "source_name": "New York Times",
                                "url_template": "https://example.com/nyt-{month}-{day}.pdf",
                                "enabled": True,
                            },
                            {
                                "source_name": "Financial Times",
                                "url_template": "https://example.com/ft-{month}-{day}.pdf",
                                "enabled": False,
                            },
                        ]
                    }
                ),
                encoding="utf-8",
            )

            sources = self.scan.load_translated_source_config(config_path)

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["source_name"], "New York Times")
        self.assertEqual(sources[0]["url_template"], "https://example.com/nyt-{month}-{day}.pdf")

    def test_resolve_translated_source_urls_formats_month_and_day(self):
        sources = [
            {
                "source_name": "New York Times",
                "url_template": "https://example.com/nyt-{month}-{day}.pdf",
                "enabled": True,
            }
        ]

        resolved = self.scan.resolve_translated_source_urls(sources, date(2026, 3, 7))

        self.assertEqual(len(resolved), 1)
        self.assertEqual(resolved[0]["url"], "https://example.com/nyt-3-7.pdf")
        self.assertEqual(resolved[0]["source_name"], "New York Times")

    def test_resolve_translated_source_urls_preserves_metadata(self):
        sources = [
            {
                "source_name": "New York Times",
                "url_template": "https://example.com/nyt-{month}-{day}.pdf",
                "enabled": True,
                "edition": "international",
            }
        ]

        resolved = self.scan.resolve_translated_source_urls(sources, date(2026, 3, 7))

        self.assertEqual(resolved[0]["source_name"], "New York Times")
        self.assertEqual(resolved[0]["edition"], "international")
        self.assertEqual(resolved[0]["url"], "https://example.com/nyt-3-7.pdf")

    def test_parse_args_accepts_source_config_and_run_date(self):
        with mock.patch(
            "sys.argv",
            [
                "scan.py",
                "--urls",
                "/tmp/urls.txt",
                "--out-dir",
                "/tmp/out",
                "--source-config",
                "/tmp/sources.json",
                "--run-date",
                "2026-03-27",
            ],
        ):
            args = self.scan.parse_args()

        self.assertEqual(args.source_config, "/tmp/sources.json")
        self.assertEqual(args.run_date, "2026-03-27")

    def test_main_returns_cli_error_for_invalid_run_date(self):
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sources.json"
            config_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "source_name": "New York Times",
                                "url_template": "https://example.com/nyt-{month}-{day}.pdf",
                                "enabled": True,
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            stderr = io.StringIO()
            with mock.patch(
                "sys.argv",
                [
                    "scan.py",
                    "--out-dir",
                    str(Path(tmpdir) / "out"),
                    "--source-config",
                    str(config_path),
                    "--run-date",
                    "not-a-date",
                ],
            ), redirect_stderr(stderr):
                exit_code = self.scan.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("Invalid --run-date", stderr.getvalue())

    def test_main_returns_cli_error_for_malformed_source_config(self):
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sources.json"
            config_path.write_text("{not valid json", encoding="utf-8")

            stderr = io.StringIO()
            with mock.patch(
                "sys.argv",
                [
                    "scan.py",
                    "--out-dir",
                    str(Path(tmpdir) / "out"),
                    "--source-config",
                    str(config_path),
                    "--run-date",
                    "2026-03-27",
                ],
            ), redirect_stderr(stderr):
                exit_code = self.scan.main()

        self.assertEqual(exit_code, 2)
        self.assertIn("Invalid --source-config", stderr.getvalue())

    def test_collect_sources_preserves_config_records(self):
        with TemporaryDirectory() as tmpdir:
            config_path = Path(tmpdir) / "sources.json"
            config_path.write_text(
                json.dumps(
                    {
                        "sources": [
                            {
                                "source_name": "New York Times",
                                "url_template": "https://example.com/nyt-{month}-{day}.pdf",
                                "enabled": True,
                                "edition": "international",
                            }
                        ]
                    }
                ),
                encoding="utf-8",
            )

            sources = self.scan.collect_sources(
                urls_path=None,
                source_config_path=config_path,
                run_date=date(2026, 3, 27),
            )

        self.assertEqual(len(sources), 1)
        self.assertEqual(sources[0]["source_name"], "New York Times")
        self.assertEqual(sources[0]["edition"], "international")
        self.assertEqual(sources[0]["url"], "https://example.com/nyt-3-27.pdf")


class TextLayerExtractionTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_score_text_layer_output_prefers_real_text_over_empty_output(self):
        strong_text = "《金融时报》\n战争冲击波引发滞胀阴影\n市场“乒乓”震荡带来的深远启示\n"
        empty_text = " \n \f \n"

        self.assertGreater(self.scan.score_text_layer_output(strong_text), self.scan.score_text_layer_output(empty_text))

    def test_extract_text_layer_marks_strong_output_available(self):
        strong_text = "\f".join(
            [
                "《金融时报》\n战争冲击波引发滞胀阴影\n市场“乒乓”震荡带来的深远启示",
                "丹麦大选爆冷，首相权力遭削弱\n海外政党捐赠设限及加密货币禁令",
            ]
        )

        with mock.patch.object(self.scan, "run_command", return_value=mock.Mock(stdout=strong_text, stderr="")):
            result = self.scan.extract_text_layer(Path("/tmp/fake-paper.pdf"))

        self.assertEqual(result["status"], "available")
        self.assertGreater(result["score"], 0.2)
        self.assertGreater(result["char_count"], 0)

    def test_extract_text_layer_marks_empty_output_unavailable(self):
        with mock.patch.object(self.scan, "run_command", return_value=mock.Mock(stdout="   \n", stderr="")):
            result = self.scan.extract_text_layer(Path("/tmp/fake-paper.pdf"))

        self.assertEqual(result["status"], "unavailable")
        self.assertEqual(result["reason"], "empty text layer")
        self.assertEqual(result["char_count"], 0)

    def test_process_paper_records_text_layer_failure_metadata(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            fake_pdf = Path(tmpdir) / "paper.pdf"

            with (
                mock.patch.object(self.scan, "download_or_copy_source", return_value=(fake_pdf, None)),
                mock.patch.object(self.scan, "get_page_count", return_value=(1, "pypdf")),
                mock.patch.object(self.scan, "extract_text_layer", return_value={
                    "status": "unavailable",
                    "reason": "empty text layer",
                    "score": 0.0,
                    "char_count": 0,
                    "line_count": 0,
                    "text_path": None,
                }),
                mock.patch.object(self.scan, "render_page", return_value=Path(tmpdir) / "page-001.png"),
                mock.patch.object(self.scan, "prepare_ocr_variants", return_value=[{"path": Path(tmpdir) / "page-001.png", "panel": "full", "variant": "source"}]),
                mock.patch.object(self.scan, "best_ocr_text_for_image_variant", return_value={"text": "headline\nbody", "psm": 6, "variant": "source", "panel": "full", "path": str(Path(tmpdir) / "page-001.png")}),
            ):
                result = self.scan.process_paper(
                    source="https://example.com/paper.pdf",
                    out_dir=out_dir,
                    dpi=300,
                    max_pages=1,
                    topic_map={},
                )

        self.assertEqual(result["paper"]["text_layer_status"], "unavailable")
        self.assertEqual(result["paper"]["text_layer_reason"], "empty text layer")
        self.assertTrue(any(item["stage"] == "text_layer" for item in result["errors"]))

    def test_process_paper_writes_text_layer_page_artifacts(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            fake_pdf = Path(tmpdir) / "paper.pdf"
            strong_text = "\f".join(
                [
                    "第一页标题\n第一页正文\n",
                    "第二页标题\n第二页正文\n",
                ]
            )

            with (
                mock.patch.object(self.scan, "download_or_copy_source", return_value=(fake_pdf, None)),
                mock.patch.object(self.scan, "get_page_count", return_value=(2, "pypdf")),
                mock.patch.object(self.scan, "extract_text_layer", return_value={
                    "status": "available",
                    "reason": "",
                    "score": 1.0,
                    "char_count": 20,
                    "line_count": 4,
                    "text": strong_text,
                    "raw_text": strong_text,
                }),
                mock.patch.object(self.scan, "render_page", side_effect=[Path(tmpdir) / "page-001.png", Path(tmpdir) / "page-002.png"]),
                mock.patch.object(self.scan, "prepare_ocr_variants", return_value=[{"path": Path(tmpdir) / "page-001.png", "panel": "full", "variant": "source"}]),
                mock.patch.object(self.scan, "best_ocr_text_for_image_variant", return_value={"text": "headline\nbody", "psm": 6, "variant": "source", "panel": "full", "path": str(Path(tmpdir) / "page-001.png")}),
            ):
                result = self.scan.process_paper(
                    source="https://example.com/paper.pdf",
                    out_dir=out_dir,
                    dpi=300,
                    max_pages=1,
                    topic_map={},
                )

            self.assertEqual(result["paper"]["text_layer_status"], "available")
            self.assertEqual(result["paper"]["text_layer_page_count"], 2)
            self.assertIsNotNone(result["paper"]["text_layer_dir"])
            text_dir = out_dir / str(result["paper"]["text_layer_dir"])
            self.assertTrue((text_dir / "page-001.txt").exists())
            self.assertTrue((text_dir / "page-002.txt").exists())
            self.assertEqual(result["page_index"][0]["text_path"], str((text_dir / "page-001.txt").relative_to(out_dir)))

    def test_process_paper_deletes_downloaded_pdf_after_processing(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            fake_pdf = Path(tmpdir) / "paper.pdf"
            fake_pdf.write_text("pdf placeholder", encoding="utf-8")
            strong_text = "第一页标题\n第一页正文\n"

            with (
                mock.patch.object(self.scan, "download_or_copy_source", return_value=(fake_pdf, None)),
                mock.patch.object(self.scan, "get_page_count", return_value=(1, "pypdf")),
                mock.patch.object(self.scan, "extract_text_layer", return_value={
                    "status": "available",
                    "reason": "",
                    "score": 1.0,
                    "char_count": 8,
                    "line_count": 2,
                    "text": strong_text,
                    "raw_text": strong_text,
                }),
                mock.patch.object(self.scan, "extract_bbox_page_blocks", return_value={}),
            ):
                result = self.scan.process_paper(
                    source="https://example.com/paper.pdf",
                    out_dir=out_dir,
                    dpi=300,
                    max_pages=1,
                    topic_map={},
                )

            self.assertFalse(fake_pdf.exists())
            self.assertIsNone(result["paper"]["local_pdf"])

    def test_process_paper_skips_ocr_when_text_layer_is_available(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            fake_pdf = Path(tmpdir) / "paper.pdf"
            strong_text = "第一页标题\n第一页正文\n"

            render_mock = mock.Mock(name="render_page")
            prepare_mock = mock.Mock(name="prepare_ocr_variants")
            best_mock = mock.Mock(name="best_ocr_text_for_image_variant")

            with (
                mock.patch.object(self.scan, "download_or_copy_source", return_value=(fake_pdf, None)),
                mock.patch.object(self.scan, "get_page_count", return_value=(1, "pypdf")),
                mock.patch.object(self.scan, "extract_text_layer", return_value={
                    "status": "available",
                    "reason": "",
                    "score": 1.0,
                    "char_count": 8,
                    "line_count": 2,
                    "text": strong_text,
                    "raw_text": strong_text,
                }),
                mock.patch.object(self.scan, "extract_bbox_page_blocks", return_value={}),
                mock.patch.object(self.scan, "render_page", render_mock),
                mock.patch.object(self.scan, "prepare_ocr_variants", prepare_mock),
                mock.patch.object(self.scan, "best_ocr_text_for_image_variant", best_mock),
            ):
                result = self.scan.process_paper(
                    source="https://example.com/paper.pdf",
                    out_dir=out_dir,
                    dpi=300,
                    max_pages=1,
                    topic_map={},
                )

            self.assertEqual(result["paper"]["text_layer_status"], "available")
            self.assertEqual(result["paper"]["scanned_pages"], 1)
            self.assertEqual(result["page_index"][0]["page"], 1)
            self.assertIsNotNone(result["page_index"][0]["text_path"])
            render_mock.assert_not_called()
            prepare_mock.assert_not_called()
            best_mock.assert_not_called()

    def test_process_paper_preserves_text_layer_page_numbers_across_blank_pages(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            fake_pdf = Path(tmpdir) / "paper.pdf"
            strong_text = "\f".join(
                [
                    "第一页标题\n第一页正文\n",
                    "   \n",
                    "第三页标题\n第三页正文\n",
                ]
            )

            with (
                mock.patch.object(self.scan, "download_or_copy_source", return_value=(fake_pdf, None)),
                mock.patch.object(self.scan, "get_page_count", return_value=(3, "pypdf")),
                mock.patch.object(self.scan, "extract_text_layer", return_value={
                    "status": "available",
                    "reason": "",
                    "score": 1.0,
                    "char_count": 20,
                    "line_count": 4,
                    "text": strong_text,
                    "raw_text": strong_text,
                }),
                mock.patch.object(
                    self.scan,
                    "render_page",
                    side_effect=[
                        Path(tmpdir) / "page-001.png",
                        Path(tmpdir) / "page-002.png",
                        Path(tmpdir) / "page-003.png",
                    ],
                ),
                mock.patch.object(
                    self.scan,
                    "prepare_ocr_variants",
                    return_value=[{"path": Path(tmpdir) / "page-001.png", "panel": "full", "variant": "source"}],
                ),
                mock.patch.object(
                    self.scan,
                    "best_ocr_text_for_image_variant",
                    return_value={"text": "headline\nbody", "psm": 6, "variant": "source", "panel": "full", "path": str(Path(tmpdir) / "page-001.png")},
                ),
            ):
                result = self.scan.process_paper(
                    source="https://example.com/paper.pdf",
                    out_dir=out_dir,
                    dpi=300,
                    max_pages=3,
                    topic_map={},
                )

            text_dir = out_dir / str(result["paper"]["text_layer_dir"])
            self.assertTrue((text_dir / "page-001.txt").exists())
            self.assertFalse((text_dir / "page-002.txt").exists())
            self.assertTrue((text_dir / "page-003.txt").exists())
            self.assertEqual(result["page_index"][2]["text_path"], str((text_dir / "page-003.txt").relative_to(out_dir)))

    def test_write_text_layer_artifacts_preserves_wide_layout_gaps(self):
        with TemporaryDirectory() as tmpdir:
            text_dir = Path(tmpdir) / "text"
            raw_text = "标题一          标题二\n正文甲          正文乙\n"

            self.scan.write_text_layer_artifacts(raw_text, text_dir)

            written = (text_dir / "page-001.txt").read_text(encoding="utf-8")
            self.assertIn("标题一          标题二", written)


class ArticleCandidateTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_normalize_article_title_canonicalizes_width_and_punctuation_variants(self):
        title = "来自地球的“红色警报”：我们将走向何方？ ＡＩ—教育…"

        normalized = self.scan.normalize_article_title(title)

        self.assertEqual(normalized, '来自地球的"红色警报":我们将走向何方?AI-教育...')

    def test_strip_article_page_furniture_removes_masthead_and_weather_lines(self):
        raw_text = "\n".join(
            [
                "《纽约时报》",
                "2026年3月26日，星期四",
                "战争冲击波引发滞胀阴影",
                "市场“乒乓”震荡带来的深远启示",
                "天气",
                "今日，微风，气温回升，多云间晴",
            ]
        )

        cleaned = self.scan.strip_article_page_furniture(raw_text)

        self.assertNotIn("《纽约时报》", cleaned)
        self.assertNotIn("2026年3月26日，星期四", cleaned)
        self.assertNotIn("天气", cleaned)
        self.assertIn("战争冲击波引发滞胀阴影", cleaned)
        self.assertIn("市场“乒乓”震荡带来的深远启示", cleaned)

    def test_build_article_candidates_from_page_records_creates_structured_records(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            text_dir = out_dir / "text" / "nyt-2026-03-26"
            text_dir.mkdir(parents=True, exist_ok=True)
            text_path = text_dir / "page-001.txt"
            text_path.write_text(
                "\n".join(
                    [
                        "《纽约时报》",
                        "2026年3月26日，星期四",
                        "战争冲击波引发滞胀阴影",
                        "伊朗与以色列局势持续升级",
                        "更多正文内容在这里，供AI阅读理解。",
                    ]
                ),
                encoding="utf-8",
            )

            page_index = [
                {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/nyt.pdf",
                    "page": 1,
                    "text_path": str(text_path.relative_to(out_dir)),
                }
            ]

            candidates = self.scan.build_article_candidates(page_index, out_dir, self.scan.normalize_topic_terms(""))

        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0]["page"], 1)
        self.assertEqual(candidates[0]["title_guess"], "战争冲击波引发滞胀阴影")
        self.assertIn("伊朗与以色列局势持续升级", candidates[0]["body_text"])
        self.assertNotIn("战争冲击波引发滞胀阴影", candidates[0]["body_text"])
        self.assertIn("headline", candidates[0]["importance_hints"])
        self.assertIn("war", candidates[0]["topic_tags"])

    def test_build_article_candidates_assigns_stable_article_identity_fields(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            text_dir = out_dir / "text" / "nyt-2026-03-26"
            text_dir.mkdir(parents=True, exist_ok=True)
            text_path = text_dir / "page-001.txt"
            text_path.write_text(
                "\n".join(
                    [
                        "《纽约时报》",
                        "战争冲击波引发滞胀阴影",
                        "作者：TONY ROMM",
                        "华盛顿 —— 随着与伊朗的开战导致全球石油和天然气价格飙升，特朗普总统对这种负面影响不屑一顾。",
                        "经济学家表示，美国普通家庭和企业若要看到持续攀升的能源成本出现实质性回落，可能仍需数周甚至数月之久。",
                    ]
                ),
                encoding="utf-8",
            )

            page_index = [
                {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/nyt.pdf",
                    "page": 1,
                    "text_path": str(text_path.relative_to(out_dir)),
                }
            ]

            candidates = self.scan.build_article_candidates(page_index, out_dir, self.scan.normalize_topic_terms(""))

        self.assertEqual(len(candidates), 1)
        candidate = candidates[0]
        self.assertIn("article_id", candidate)
        self.assertIn("title", candidate)
        self.assertIn("title_normalized", candidate)
        self.assertIn("lookup_keys", candidate)
        self.assertEqual(candidate["title"], candidate["title_guess"])
        self.assertEqual(candidate["title_normalized"], "战争冲击波引发滞胀阴影")
        self.assertIn(candidate["article_id"], candidate["lookup_keys"])
        self.assertIn("page:1", candidate["lookup_keys"])
        self.assertIn("title:战争冲击波引发滞胀阴影", candidate["lookup_keys"])

    def test_build_article_candidates_generates_stable_article_id_for_same_input(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            text_dir = out_dir / "text" / "nyt-2026-03-26"
            text_dir.mkdir(parents=True, exist_ok=True)
            text_path = text_dir / "page-001.txt"
            text_path.write_text(
                "\n".join(
                    [
                        "《纽约时报》",
                        "战争冲击波引发滞胀阴影",
                        "作者：TONY ROMM",
                        "华盛顿 —— 随着与伊朗的开战导致全球石油和天然气价格飙升，特朗普总统对这种负面影响不屑一顾。",
                        "经济学家表示，美国普通家庭和企业若要看到持续攀升的能源成本出现实质性回落，可能仍需数周甚至数月之久。",
                    ]
                ),
                encoding="utf-8",
            )

            page_index = [
                {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/nyt.pdf",
                    "page": 1,
                    "text_path": str(text_path.relative_to(out_dir)),
                }
            ]

            first = self.scan.build_article_candidates(page_index, out_dir, self.scan.normalize_topic_terms(""))
            second = self.scan.build_article_candidates(page_index, out_dir, self.scan.normalize_topic_terms(""))

        self.assertEqual(first[0]["article_id"], second[0]["article_id"])

    def test_build_article_candidates_normalize_title_variants_to_same_article_id(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            text_dir = out_dir / "text" / "nyt-2026-03-26"
            text_dir.mkdir(parents=True, exist_ok=True)

            first_path = text_dir / "page-001.txt"
            first_path.write_text(
                "\n".join(
                    [
                        "《纽约时报》",
                        "来自地球的“红色警报”：我们将走向何方？",
                        "作者：Reporter",
                        "正文内容足够长，用来生成稳定文章标识和正文抽取结果。",
                        "第二段正文继续补足长度，避免被过滤掉。",
                    ]
                ),
                encoding="utf-8",
            )
            second_path = text_dir / "page-002.txt"
            second_path.write_text(
                "\n".join(
                    [
                        "《纽约时报》",
                        '来自地球的"红色警报":我们将走向何方?',
                        "作者：Reporter",
                        "正文内容足够长，用来生成稳定文章标识和正文抽取结果。",
                        "第二段正文继续补足长度，避免被过滤掉。",
                    ]
                ),
                encoding="utf-8",
            )

            first_candidates = self.scan.build_article_candidates(
                [
                    {
                        "source_name": "纽约时报",
                        "paper_id": "nyt-2026-03-26",
                        "url": "https://example.com/nyt.pdf",
                        "page": 1,
                        "text_path": str(first_path.relative_to(out_dir)),
                    }
                ],
                out_dir,
                self.scan.normalize_topic_terms(""),
            )
            second_candidates = self.scan.build_article_candidates(
                [
                    {
                        "source_name": "纽约时报",
                        "paper_id": "nyt-2026-03-26",
                        "url": "https://example.com/nyt.pdf",
                        "page": 1,
                        "text_path": str(second_path.relative_to(out_dir)),
                    }
                ],
                out_dir,
                self.scan.normalize_topic_terms(""),
            )

        self.assertEqual(first_candidates[0]["title_normalized"], second_candidates[0]["title_normalized"])
        self.assertEqual(first_candidates[0]["article_id"], second_candidates[0]["article_id"])

    def test_build_article_candidates_skips_pages_without_text_path(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            ocr_dir = out_dir / "ocr" / "nyt-2026-03-26"
            ocr_dir.mkdir(parents=True, exist_ok=True)
            ocr_path = ocr_dir / "page-001.txt"
            ocr_path.write_text("OCR 噪声内容\n", encoding="utf-8")

            page_index = [
                {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/nyt.pdf",
                    "page": 1,
                    "ocr_path": str(ocr_path.relative_to(out_dir)),
                    "text_path": None,
                }
            ]

            candidates = self.scan.build_article_candidates(page_index, out_dir, self.scan.normalize_topic_terms(""))

        self.assertEqual(candidates, [])

    def test_main_writes_articles_json(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            urls_path = Path(tmpdir) / "urls.txt"
            urls_path.write_text("https://example.com/paper.pdf\n", encoding="utf-8")

            paper_result = {
                "paper": {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/paper.pdf",
                    "source_record": {"source_name": "纽约时报", "url": "https://example.com/paper.pdf"},
                    "local_pdf": "pdfs/nyt-2026-03-26.pdf",
                    "page_count": 1,
                    "scanned_pages": 1,
                    "status": "ok",
                    "page_count_source": "pypdf",
                    "text_layer_status": "available",
                    "text_layer_reason": "",
                    "text_layer_score": 1.0,
                    "text_layer_char_count": 100,
                    "text_layer_line_count": 10,
                    "text_layer_dir": "text/nyt-2026-03-26",
                    "text_layer_page_count": 1,
                },
                "page_index": [
                    {
                        "source_name": "纽约时报",
                        "paper_id": "nyt-2026-03-26",
                        "url": "https://example.com/paper.pdf",
                        "page": 1,
                        "preview_path": "previews/nyt-2026-03-26/page-001.png",
                        "ocr_path": "ocr/nyt-2026-03-26/page-001.txt",
                        "text_path": "text/nyt-2026-03-26/page-001.txt",
                    }
                ],
                "opinion_candidates": [],
                "topic_hits": [],
                "review_candidates": [],
                "article_candidates": [
                    {
                        "source_name": "纽约时报",
                        "paper_id": "nyt-2026-03-26",
                        "url": "https://example.com/paper.pdf",
                        "page": 1,
                        "title_guess": "战争冲击波引发滞胀阴影",
                        "body_text": "战争冲击波引发滞胀阴影\n更多正文内容",
                        "section_guess": "",
                        "topic_tags": ["war"],
                        "importance_hints": ["headline"],
                        "text_path": "text/nyt-2026-03-26/page-001.txt",
                    }
                ],
                "errors": [],
            }

            with (
                mock.patch.object(self.scan, "process_paper", return_value=paper_result),
                mock.patch.object(self.scan, "collect_sources", return_value=[{"source_name": "纽约时报", "url": "https://example.com/paper.pdf"}]),
                mock.patch.object(self.scan, "normalize_topic_terms", return_value={}),
                mock.patch.object(self.scan, "read_source_lines", return_value=["https://example.com/paper.pdf"]),
            ):
                with mock.patch("sys.argv", ["scan.py", "--urls", str(urls_path), "--out-dir", str(out_dir)]):
                    exit_code = self.scan.main()

            self.assertEqual(exit_code, 0)
            articles_path = out_dir / "articles.json"
            self.assertTrue(articles_path.exists())
            payload = json.loads(articles_path.read_text(encoding="utf-8"))
            self.assertEqual(payload["articles"][0]["page"], 1)
            self.assertEqual(payload["articles"][0]["title_guess"], "战争冲击波引发滞胀阴影")
            self.assertIn("article_id", payload["articles"][0])
            self.assertIn("title_normalized", payload["articles"][0])
            self.assertIn("lookup_keys", payload["articles"][0])
            self.assertIn("priority_score", payload["articles"][0])
            self.assertTrue((out_dir / "summary.json").exists())
            self.assertTrue((out_dir / "summary.md").exists())

    def test_extract_translated_article_blocks_splits_front_page_and_filters_service_lines(self):
        page_text = "\n".join(
            [
                "《纽约时报》",
                "天气",
                "今日，微风，气温回升，多云间晴",
                "高昂油价或将比战争更持久",
                "作者：TONY ROMM",
                "华盛顿 —— 随着与伊朗的开战导致全球石油和天然气价格飙升，特朗普总统对这种负面影响不屑一顾。",
                "经济学家表示，美国普通家庭和企业若要看到持续攀升的能源成本出现实质性回落，可能仍需数周甚至数月之久。",
                "下转A8版",
                "Meta与YouTube被判赔偿600万美元",
                "作者：Cecilia Kang",
                "华盛顿 —— 陪审团周三判定，社交媒体公司 Meta 及视频流媒体平台 YouTube 的成瘾性设计特征对一名年轻用户造成了伤害。",
                "这一里程碑式的裁决可能会使社交媒体公司因用户福祉问题面临更多诉讼。",
                "服务指南",
                "请访问 nytimes.com/thedaily 收听本期节目。",
            ]
        )

        blocks = self.scan.extract_translated_article_blocks(page_text, page_number=1)

        self.assertEqual([block["title"] for block in blocks], ["高昂油价或将比战争更持久", "Meta与YouTube被判赔偿600万美元"])
        self.assertTrue(all("服务指南" not in block["body_text"] for block in blocks))
        self.assertTrue(all("天气" not in block["body_text"] for block in blocks))

    def test_translated_page_lines_split_wide_gaps_into_segments(self):
        page_text = "\n".join(
            [
                "标题一          标题二",
                "正文甲          正文乙",
            ]
        )

        lines = self.scan.translated_page_lines(page_text)

        self.assertEqual(lines, ["标题一", "标题二", "正文甲", "正文乙"])

    def test_extract_translated_bbox_article_blocks_merges_body_blocks_with_nearby_headline(self):
        blocks = [
            {"x_min": 40.0, "x_max": 120.0, "y_min": 20.0, "y_max": 30.0, "text": "天气"},
            {"x_min": 400.0, "x_max": 560.0, "y_min": 100.0, "y_max": 120.0, "text": "高昂油价或将比战争更持久"},
            {"x_min": 410.0, "x_max": 520.0, "y_min": 126.0, "y_max": 138.0, "text": "作者：TONY ROMM"},
            {"x_min": 402.0, "x_max": 558.0, "y_min": 150.0, "y_max": 210.0, "text": "华盛顿 —— 随着与伊朗的开战导致全球石油和天然气价格飙升，特朗普总统对这种负面影响不屑一顾。"},
            {"x_min": 404.0, "x_max": 559.0, "y_min": 214.0, "y_max": 278.0, "text": "经济学家和行业高管表示，美国普通家庭和企业若要看到持续攀升的能源成本出现实质性回落，可能仍需数周甚至数月之久。"},
        ]

        article_blocks = self.scan.extract_translated_bbox_article_blocks(blocks, page_number=1)

        self.assertEqual(len(article_blocks), 1)
        self.assertEqual(article_blocks[0]["title"], "高昂油价或将比战争更持久")
        self.assertEqual(article_blocks[0]["byline"], "作者：TONY ROMM")
        self.assertIn("经济学家和行业高管表示", article_blocks[0]["body_text"])

    def test_build_article_candidates_uses_front_page_blocks_and_late_page_fallback(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            text_dir = out_dir / "text" / "nyt-2026-03-26"
            text_dir.mkdir(parents=True, exist_ok=True)

            front_page_text = text_dir / "page-001.txt"
            front_page_text.write_text(
                "\n".join(
                    [
                        "《纽约时报》",
                        "高昂油价或将比战争更持久",
                        "作者：TONY ROMM",
                        "华盛顿 —— 随着与伊朗的开战导致全球石油和天然气价格飙升，特朗普总统对这种负面影响不屑一顾。",
                        "经济学家表示，美国普通家庭和企业若要看到持续攀升的能源成本出现实质性回落，可能仍需数周甚至数月之久。",
                        "下转A8版",
                        "Meta与YouTube被判赔偿600万美元",
                        "作者：Cecilia Kang",
                        "华盛顿 —— 陪审团周三判定，社交媒体公司 Meta 及视频流媒体平台 YouTube 的成瘾性设计特征对一名年轻用户造成了伤害。",
                    ]
                ),
                encoding="utf-8",
            )
            late_page_text = text_dir / "page-012.txt"
            late_page_text.write_text(
                "\n".join(
                    [
                        "被忽视且未受控制的糖尿病正给非洲带来新风险",
                        "作者：STEPHANIE NOLEN",
                        "喀麦隆马鲁阿 —— 波莱特·久格医生抵达她位于喀麦隆北部的糖尿病诊所时，旭日尚未升起。",
                    ]
                ),
                encoding="utf-8",
            )

            page_index = [
                {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/nyt.pdf",
                    "page": 1,
                    "text_path": str(front_page_text.relative_to(out_dir)),
                },
                {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/nyt.pdf",
                    "page": 12,
                    "text_path": str(late_page_text.relative_to(out_dir)),
                },
            ]

            candidates = self.scan.build_article_candidates(page_index, out_dir, self.scan.normalize_topic_terms(""))

        self.assertEqual([candidate["title_guess"] for candidate in candidates], ["高昂油价或将比战争更持久", "Meta与YouTube被判赔偿600万美元", "被忽视且未受控制的糖尿病正给非洲带来新风险"])
        self.assertEqual([candidate["block_kind"] for candidate in candidates], ["article_block", "article_block", "page_fallback"])
        self.assertEqual([candidate["block_index"] for candidate in candidates], [1, 2, 0])


class SummaryContractTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_select_summary_articles_limits_per_paper_to_ten_items(self):
        articles = [
            {
                "source_name": "纽约时报",
                "paper_id": "nyt-2026-03-26",
                "url": "https://example.com/paper.pdf",
                "page": index,
                "title_guess": f"标题 {index}",
                "body_text": f"正文 {index}",
                "section_guess": "",
                "topic_tags": ["war"] if index % 2 == 0 else [],
                "importance_hints": ["headline"] if index <= 3 else [],
                "text_path": f"text/nyt-2026-03-26/page-{index:03d}.txt",
            }
            for index in range(1, 13)
        ]

        selected = self.scan.select_summary_articles(articles)

        self.assertLessEqual(len(selected), 10)
        self.assertGreaterEqual(len(selected), 5)
        self.assertEqual(len({item["page"] for item in selected}), len(selected))
        self.assertTrue(all(item["page"] <= 12 for item in selected))

    def test_write_summary_outputs_json_and_markdown(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            summary_articles = [
                {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/paper.pdf",
                    "page": 1,
                    "title_guess": "战争冲击波引发滞胀阴影",
                    "body_text": "正文",
                    "section_guess": "",
                    "topic_tags": ["war"],
                    "importance_hints": ["headline"],
                    "text_path": "text/nyt-2026-03-26/page-001.txt",
                }
            ]
            paper_result = {
                "source_name": "纽约时报",
                "paper_id": "nyt-2026-03-26",
                "url": "https://example.com/paper.pdf",
                "status": "ok",
                "article_count": 1,
                "summary_candidates": summary_articles,
                "summary_selected": summary_articles,
            }

            self.scan.write_summary_outputs(out_dir, date(2026, 3, 27), [paper_result], summary_articles)

            summary_json = out_dir / "summary.json"
            summary_md = out_dir / "summary.md"
            self.assertTrue(summary_json.exists())
            self.assertTrue(summary_md.exists())

            payload = json.loads(summary_json.read_text(encoding="utf-8"))
            self.assertEqual(payload["run_date"], "2026-03-27")
            self.assertEqual(len(payload["papers"]), 1)
            self.assertEqual(payload["papers"][0]["selected_count"], 1)
            self.assertIn("战争冲击波引发滞胀阴影", summary_md.read_text(encoding="utf-8"))
            self.assertTrue((out_dir / "daily_brief.json").exists())

    def test_write_summary_outputs_clamps_selected_articles_and_derives_flat_articles(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            selected_articles = [
                {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/paper.pdf",
                    "page": index,
                    "title_guess": f"标题 {index}",
                    "body_text": f"正文 {index}",
                    "section_guess": "",
                    "topic_tags": [],
                    "importance_hints": ["headline"],
                    "text_path": f"text/nyt-2026-03-26/page-{index:03d}.txt",
                }
                for index in range(1, 13)
            ]
            paper_result = {
                "source_name": "纽约时报",
                "paper_id": "nyt-2026-03-26",
                "url": "https://example.com/paper.pdf",
                "status": "ok",
                "article_count": 12,
                "summary_candidates": selected_articles,
                "summary_selected": selected_articles,
            }

            self.scan.write_summary_outputs(
                out_dir,
                date(2026, 3, 27),
                [paper_result],
                [{"page": 999, "title_guess": "错误占位", "body_text": "不应写出"}],
            )

            payload = json.loads((out_dir / "summary.json").read_text(encoding="utf-8"))
            self.assertLessEqual(payload["papers"][0]["selected_count"], 10)
            self.assertEqual(len(payload["articles"]), payload["papers"][0]["selected_count"])
            self.assertNotIn(999, [item["page"] for item in payload["articles"]])

    def test_write_summary_outputs_writes_daily_brief_contract(self):
        with TemporaryDirectory() as tmpdir:
            out_dir = Path(tmpdir) / "out"
            out_dir.mkdir(parents=True, exist_ok=True)
            summary_articles = [
                {
                    "source_name": "纽约时报",
                    "paper_id": "nyt-2026-03-26",
                    "url": "https://example.com/paper.pdf",
                    "article_id": "nyt-2026-03-26:p1:page_fallback:0:test",
                    "page": 1,
                    "title": "战争冲击波引发滞胀阴影",
                    "title_guess": "战争冲击波引发滞胀阴影",
                    "title_normalized": "战争冲击波引发滞胀阴影",
                    "byline": "作者：TONY ROMM",
                    "body_text": "正文",
                    "summary_text": "摘要内容",
                    "priority_score": 9.75,
                    "section_guess": "",
                    "topic_tags": ["war"],
                    "importance_hints": ["headline"],
                    "lookup_keys": ["nyt-2026-03-26:p1:page_fallback:0:test", "page:1", "title:战争冲击波引发滞胀阴影"],
                    "text_path": "text/nyt-2026-03-26/page-001.txt",
                }
            ]
            paper_result = {
                "source_name": "纽约时报",
                "paper_id": "nyt-2026-03-26",
                "url": "https://example.com/paper.pdf",
                "status": "ok",
                "article_count": 1,
                "summary_candidates": summary_articles,
                "summary_selected": summary_articles,
            }

            self.scan.write_summary_outputs(out_dir, date(2026, 3, 27), [paper_result], summary_articles)

            brief_payload = json.loads((out_dir / "daily_brief.json").read_text(encoding="utf-8"))
            self.assertEqual(brief_payload["run_date"], "2026-03-27")
            self.assertEqual(len(brief_payload["papers"]), 1)
            self.assertEqual(brief_payload["papers"][0]["source_name"], "纽约时报")
            self.assertEqual(brief_payload["papers"][0]["selected_count"], 1)
            self.assertEqual(len(brief_payload["papers"][0]["articles"]), 1)
            self.assertEqual(brief_payload["papers"][0]["articles"][0]["article_id"], "nyt-2026-03-26:p1:page_fallback:0:test")
            self.assertEqual(brief_payload["papers"][0]["articles"][0]["byline"], "作者：TONY ROMM")
            self.assertEqual(brief_payload["papers"][0]["articles"][0]["priority_score"], 9.75)
            self.assertEqual(brief_payload["papers"][0]["articles"][0]["title"], "战争冲击波引发滞胀阴影")
            self.assertEqual(brief_payload["papers"][0]["articles"][0]["summary_text"], "摘要内容")
            self.assertEqual(brief_payload["papers"][0]["articles"][0]["text_path"], "text/nyt-2026-03-26/page-001.txt")

    def test_select_summary_articles_respects_explicit_priority_score(self):
        articles = [
            {
                "source_name": "纽约时报",
                "paper_id": "nyt-2026-03-26",
                "url": "https://example.com/paper.pdf",
                "page": 1,
                "title_guess": "看似重要但不该优先",
                "body_text": " ".join(["普通正文"] * 120),
                "section_guess": "",
                "topic_tags": [],
                "importance_hints": [],
                "text_path": "text/nyt-2026-03-26/page-001.txt",
                "priority_score": 1.0,
            },
            {
                "source_name": "纽约时报",
                "paper_id": "nyt-2026-03-26",
                "url": "https://example.com/paper.pdf",
                "page": 2,
                "title_guess": "明确更重要的文章",
                "body_text": "短正文",
                "section_guess": "",
                "topic_tags": [],
                "importance_hints": [],
                "text_path": "text/nyt-2026-03-26/page-002.txt",
                "priority_score": 9.5,
            },
        ]

        selected = self.scan.select_summary_articles(articles, min_items=1, max_items=2)

        self.assertEqual(selected[0]["page"], 2)
        self.assertEqual(selected[0]["priority_score"], 9.5)

    def test_enrich_article_record_fills_required_lookup_keys(self):
        record = {
            "source_name": "纽约时报",
            "paper_id": "nyt-2026-03-26",
            "page": 1,
            "title_guess": "战争冲击波引发滞胀阴影",
            "title": "战争冲击波引发滞胀阴影",
            "block_kind": "page_fallback",
            "block_index": 0,
            "lookup_keys": ["custom:key"],
        }

        enriched = self.scan.enrich_article_record(record)

        self.assertIn("article_id", enriched)
        self.assertIn(enriched["article_id"], enriched["lookup_keys"])
        self.assertIn("page:1", enriched["lookup_keys"])
        self.assertIn("title:战争冲击波引发滞胀阴影", enriched["lookup_keys"])
        self.assertIn("block:page_fallback:0", enriched["lookup_keys"])
        self.assertIn("custom:key", enriched["lookup_keys"])

    def test_select_summary_articles_demotes_service_blocks_below_real_articles(self):
        articles = [
            {
                "source_name": "纽约时报",
                "paper_id": "nyt-2026-03-26",
                "url": "https://example.com/paper.pdf",
                "page": 2,
                "title_guess": "时报内幕",
                "body_text": " ".join(["发行人 总编辑 客户服务 订阅信息"] * 80),
                "section_guess": "",
                "topic_tags": [],
                "importance_hints": ["headline", "front_pages", "long_body"],
                "block_kind": "service_block",
                "text_path": "text/nyt-2026-03-26/page-002.txt",
            },
            {
                "source_name": "纽约时报",
                "paper_id": "nyt-2026-03-26",
                "url": "https://example.com/paper.pdf",
                "page": 4,
                "title_guess": "被忽视且未受控制的糖尿病正给非洲带来新风险",
                "body_text": "喀麦隆及非洲大部分地区正在经历一场显著的流行病学转变，人们现在面临死于糖尿病等非传染性疾病的风险。 " * 12,
                "section_guess": "",
                "topic_tags": [],
                "importance_hints": ["headline"],
                "block_kind": "article_block",
                "text_path": "text/nyt-2026-03-26/page-004.txt",
            },
        ]

        selected = self.scan.select_summary_articles(articles, min_items=1, max_items=2)

        self.assertEqual(selected[0]["title_guess"], "被忽视且未受控制的糖尿病正给非洲带来新风险")


class OcrSelectionTests(unittest.TestCase):
    def setUp(self):
        self.scan = load_scan_module()

    def test_choose_best_ocr_candidate_prefers_article_text_over_masthead_noise(self):
        candidates = [
            {
                "text": "THE NEW YORK TIMES WEDNESDAY, MARCH 25, 2026 A17\nVOL. CLXXV NO. 60,834",
                "psm": 6,
                "variant": "gray",
            },
            {
                "text": "New York City Teachers Get Road Map for Using A.I. in Classroom\nBy MATTHEW HAAG\nTeachers can use artificial intelligence to generate ideas for lesson plans.",
                "psm": 7,
                "variant": "binary",
            },
        ]

        best = self.scan.choose_best_ocr_candidate(candidates, prefer_title=True)

        self.assertEqual(best["psm"], 7)
        self.assertIn("Using A.I. in Classroom", best["text"])

    def test_choose_best_ocr_candidate_prefers_body_text_with_byline(self):
        candidates = [
            {
                "text": "THE NEW YORK TIMES NATIONAL WEDNESDAY, MARCH 25, 2026 N A17\nNew York City Teachers Get Road Map",
                "psm": 6,
                "variant": "gray",
            },
            {
                "text": "New York City Teachers Get Road Map for Using A.I. in Classroom\nBy MATTHEW HAAG\nTeachers can use artificial intelligence to generate ideas for lesson plans and draft some documents.",
                "psm": 4,
                "variant": "binary_sharp",
            },
        ]

        best = self.scan.choose_best_ocr_candidate(candidates, prefer_title=False)

        self.assertEqual(best["psm"], 4)
        self.assertIn("By MATTHEW HAAG", best["text"])


if __name__ == "__main__":
    unittest.main()
