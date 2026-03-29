from __future__ import annotations

import argparse
import sys
from collections import defaultdict
from datetime import datetime

try:
    import pandas as pd
except ImportError as exc:  # pragma: no cover
    raise SystemExit("❌ 错误: 缺少 pandas，请先安装依赖。") from exc

try:
    import yfinance as yf
except ImportError:  # pragma: no cover
    yf = None


DEFAULT_ASSETS = [
    {"category": "商品", "label": "WTI原油", "ticker": "CL=F"},
    {"category": "商品", "label": "布伦特原油", "ticker": "BZ=F"},
    {"category": "商品", "label": "黄金", "ticker": "GC=F"},
    {"category": "商品", "label": "白银", "ticker": "SI=F"},
    {"category": "商品", "label": "天然气", "ticker": "NG=F"},
    {"category": "商品", "label": "铜", "ticker": "HG=F"},
    {"category": "股指", "label": "标普500", "ticker": "^GSPC"},
    {"category": "股指", "label": "纳指", "ticker": "^IXIC"},
    {"category": "股指", "label": "道指", "ticker": "^DJI"},
    {"category": "股指", "label": "罗素2000", "ticker": "^RUT"},
    {"category": "波动率", "label": "VIX", "ticker": "^VIX"},
    {"category": "外汇", "label": "美元指数", "ticker": "DX-Y.NYB"},
    {"category": "外汇", "label": "欧元/美元", "ticker": "EURUSD=X"},
    {"category": "外汇", "label": "美元/日元", "ticker": "JPY=X"},
    {"category": "美债", "label": "13周美债收益率", "ticker": "^IRX"},
    {"category": "美债", "label": "5年美债收益率", "ticker": "^FVX"},
    {"category": "美债", "label": "10年美债收益率", "ticker": "^TNX"},
    {"category": "美债", "label": "30年美债收益率", "ticker": "^TYX"},
    {"category": "加密", "label": "比特币", "ticker": "BTC-USD"},
    {"category": "加密", "label": "以太坊", "ticker": "ETH-USD"},
]

CATEGORY_ORDER = ["商品", "股指", "波动率", "外汇", "美债", "加密", "扩展"]
CHANGE_WINDOWS = {
    "change_1d": 1,
    "change_5d": 5,
    "change_1m": 21,
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="生成宏观市场报表 (yfinance)")
    parser.add_argument(
        "--extra",
        default="",
        help="额外 ticker，使用逗号分隔，例如 TLT,SLV,SOL-USD",
    )
    parser.add_argument(
        "--period",
        default="3mo",
        help="下载历史区间，默认 3mo，用于计算 1日/5日/1个月涨跌幅",
    )
    return parser.parse_args(argv)


def build_asset_list(extra: str = "") -> list[dict[str, str]]:
    assets = [asset.copy() for asset in DEFAULT_ASSETS]
    seen = {asset["ticker"] for asset in assets}
    for ticker in parse_extra_tickers(extra):
        if ticker in seen:
            continue
        assets.append({"category": "扩展", "label": ticker, "ticker": ticker})
        seen.add(ticker)
    return assets


def parse_extra_tickers(extra: str) -> list[str]:
    if not extra.strip():
        return []
    tickers = []
    for raw in extra.split(","):
        ticker = raw.strip().upper()
        if ticker:
            tickers.append(ticker)
    return tickers


def download_history(tickers: list[str], period: str = "3mo") -> pd.DataFrame:
    if yf is None:
        raise RuntimeError("未安装 yfinance。请运行: pip install yfinance")
    return yf.download(
        tickers=tickers,
        period=period,
        interval="1d",
        group_by="ticker",
        auto_adjust=False,
        progress=False,
        threads=False,
    )


def extract_close_series(history: pd.DataFrame, ticker: str) -> pd.Series | None:
    if history is None or history.empty:
        return None

    columns = history.columns
    frame: pd.DataFrame | pd.Series

    if isinstance(columns, pd.MultiIndex):
        level_zero = columns.get_level_values(0)
        level_last = columns.get_level_values(-1)
        if ticker in level_zero:
            frame = history[ticker]
        elif ticker in level_last:
            frame = history.xs(ticker, axis=1, level=-1)
        else:
            return None
    else:
        frame = history

    if isinstance(frame, pd.Series):
        series = frame
    elif "Close" in frame.columns:
        series = frame["Close"]
    elif "Adj Close" in frame.columns:
        series = frame["Adj Close"]
    else:
        return None

    series = pd.to_numeric(series, errors="coerce").dropna()
    if series.empty:
        return None
    return series


def calculate_change_pct(series: pd.Series, periods: int) -> float | None:
    clean = pd.to_numeric(series, errors="coerce").dropna()
    if len(clean) <= periods:
        return None

    latest = float(clean.iloc[-1])
    previous = float(clean.iloc[-periods - 1])
    if previous == 0:
        return None
    return (latest / previous - 1.0) * 100.0


def build_asset_rows(
    assets: list[dict[str, str]],
    history: pd.DataFrame,
) -> tuple[list[dict[str, object]], list[str]]:
    rows: list[dict[str, object]] = []
    failures: list[str] = []

    for asset in assets:
        close_series = extract_close_series(history, asset["ticker"])
        if close_series is None:
            failures.append(asset["ticker"])
            continue

        latest = float(close_series.iloc[-1])
        date_value = close_series.index[-1]
        date_text = getattr(date_value, "strftime", lambda _fmt: str(date_value))("%Y-%m-%d")
        row = {
            "category": asset["category"],
            "label": asset["label"],
            "ticker": asset["ticker"],
            "latest": latest,
            "date": date_text,
        }
        for field_name, periods in CHANGE_WINDOWS.items():
            row[field_name] = calculate_change_pct(close_series, periods)
        rows.append(row)

    return rows, failures


def format_price(value: float | None) -> str:
    if value is None:
        return "N/A"
    return f"{value:,.2f}"


def format_pct(value: float | None) -> str:
    if value is None:
        return "N/A"
    sign = "+" if value > 0 else ""
    return f"{sign}{value:.2f}%"


def build_summary_lines(rows: list[dict[str, object]]) -> list[str]:
    if not rows:
        return ["- 当前没有可用数据"]

    daily_rows = [row for row in rows if row.get("change_1d") is not None]
    summary: list[str] = []

    if daily_rows:
        strongest = max(daily_rows, key=lambda item: float(item["change_1d"]))
        weakest = min(daily_rows, key=lambda item: float(item["change_1d"]))
        summary.append(
            f"- 1日最强: {strongest['label']} ({strongest['ticker']}) {format_pct(strongest['change_1d'])}"
        )
        summary.append(
            f"- 1日最弱: {weakest['label']} ({weakest['ticker']}) {format_pct(weakest['change_1d'])}"
        )

    marker_map = {
        "^VIX": "VIX",
        "^TNX": "10年美债收益率",
        "DX-Y.NYB": "美元指数",
        "BTC-USD": "比特币",
    }
    row_by_ticker = {str(row["ticker"]): row for row in rows}
    for ticker, label in marker_map.items():
        row = row_by_ticker.get(ticker)
        if row:
            summary.append(
                f"- 观察点: {label} 报 {format_price(row['latest'])}，1日 {format_pct(row['change_1d'])}"
            )

    return summary


def render_report(
    rows: list[dict[str, object]],
    failures: list[str],
    generated_at: str | None = None,
) -> str:
    generated_at = generated_at or datetime.now().strftime("%Y-%m-%d %H:%M")
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["category"])].append(row)

    lines = [
        "宏观市场报表",
        f"生成时间: {generated_at}",
        "",
        "摘要",
        *build_summary_lines(rows),
        "",
    ]

    for category in CATEGORY_ORDER:
        category_rows = grouped.get(category)
        if not category_rows:
            continue

        lines.append(f"【{category}】")
        lines.append("资产 | Ticker | 最新价格 | 1日 | 5日 | 1个月 | 日期")
        lines.append("-" * 72)
        for row in category_rows:
            lines.append(
                " | ".join(
                    [
                        str(row["label"]),
                        str(row["ticker"]),
                        format_price(row["latest"]),
                        format_pct(row["change_1d"]),
                        format_pct(row["change_5d"]),
                        format_pct(row["change_1m"]),
                        str(row["date"]),
                    ]
                )
            )
        lines.append("")

    if failures:
        lines.append("未成功获取的 ticker")
        for ticker in failures:
            lines.append(f"- {ticker}")

    return "\n".join(lines).rstrip() + "\n"


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    assets = build_asset_list(args.extra)
    tickers = [asset["ticker"] for asset in assets]

    try:
        history = download_history(tickers, args.period)
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1
    except Exception as exc:  # pragma: no cover
        print(f"❌ 获取市场数据失败: {exc}", file=sys.stderr)
        return 1

    rows, failures = build_asset_rows(assets, history)
    if not rows:
        print("❌ 未获取到任何可用市场数据。")
        return 1

    report = render_report(rows, failures)
    print(report, end="")
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
