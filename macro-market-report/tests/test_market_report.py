from __future__ import annotations

import importlib.util
from pathlib import Path

import pandas as pd


MODULE_PATH = (
    Path(__file__).resolve().parents[1] / "scripts" / "market_report.py"
)
SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"
README_PATH = Path(__file__).resolve().parents[2] / "README.md"


def load_module():
    spec = importlib.util.spec_from_file_location("market_report", MODULE_PATH)
    module = importlib.util.module_from_spec(spec)
    assert spec is not None and spec.loader is not None
    spec.loader.exec_module(module)
    return module


def build_history(close_map: dict[str, list[float]]) -> pd.DataFrame:
    dates = pd.date_range("2026-01-01", periods=len(next(iter(close_map.values()))), freq="B")
    data = {}
    for ticker, closes in close_map.items():
        data[(ticker, "Close")] = closes
    frame = pd.DataFrame(data, index=dates)
    frame.columns = pd.MultiIndex.from_tuples(frame.columns)
    return frame


def test_build_asset_rows_calculates_changes_from_history():
    module = load_module()
    history = build_history(
        {
            "GC=F": list(range(100, 122)),
            "BTC-USD": list(range(200, 222)),
        }
    )
    assets = [
        {"category": "商品", "label": "黄金", "ticker": "GC=F"},
        {"category": "加密", "label": "比特币", "ticker": "BTC-USD"},
    ]

    rows, failures = module.build_asset_rows(assets, history)

    assert failures == []
    gold = rows[0]
    assert gold["label"] == "黄金"
    assert gold["latest"] == 121.0
    assert round(gold["change_1d"], 2) == round((121 / 120 - 1) * 100, 2)
    assert round(gold["change_5d"], 2) == round((121 / 116 - 1) * 100, 2)
    assert round(gold["change_1m"], 2) == round((121 / 100 - 1) * 100, 2)


def test_build_asset_rows_marks_missing_periods_as_na():
    module = load_module()
    history = build_history({"^VIX": [18.0, 19.0, 20.0]})
    assets = [{"category": "波动率", "label": "VIX", "ticker": "^VIX"}]

    rows, failures = module.build_asset_rows(assets, history)

    assert failures == []
    assert rows[0]["change_1d"] is not None
    assert rows[0]["change_5d"] is None
    assert rows[0]["change_1m"] is None


def test_render_report_groups_rows_and_failures():
    module = load_module()
    report = module.render_report(
        rows=[
            {
                "category": "商品",
                "label": "黄金",
                "ticker": "GC=F",
                "latest": 3025.5,
                "change_1d": 0.5,
                "change_5d": 1.2,
                "change_1m": 3.8,
                "date": "2026-03-29",
            },
            {
                "category": "加密",
                "label": "比特币",
                "ticker": "BTC-USD",
                "latest": 92500.0,
                "change_1d": -1.0,
                "change_5d": 4.2,
                "change_1m": None,
                "date": "2026-03-29",
            },
        ],
        failures=["DX-Y.NYB"],
        generated_at="2026-03-29 09:00",
    )

    assert "宏观市场报表" in report
    assert "【商品】" in report
    assert "【加密】" in report
    assert "黄金" in report
    assert "比特币" in report
    assert "N/A" in report
    assert "DX-Y.NYB" in report


def test_parse_args_supports_extra_tickers():
    module = load_module()
    args = module.parse_args(["--extra", "SLV,TLT"])

    assert args.extra == "SLV,TLT"


def test_skill_markdown_has_expected_frontmatter_and_command():
    text = SKILL_PATH.read_text(encoding="utf-8")

    assert "name: macro-market-report" in text
    assert "description: Use when" in text
    assert "python3 macro-market-report/scripts/market_report.py" in text
    assert "yfinance" in text


def test_readme_mentions_macro_market_report_skill():
    text = README_PATH.read_text(encoding="utf-8")

    assert "Macro Market Report" in text
    assert "macro-market-report" in text
