# Macro Market Report Design

**Problem**

The repository already contains a stock-oriented Yahoo Finance skill, but it does not provide a single fast report covering cross-asset macro markets. The user wants a reusable skill that fetches a broad market snapshot with current prices and percentage changes, then prints a readable Chinese report directly in the terminal.

**Approaches**

1. Build one report script with a fixed default asset basket and light optional overrides.
   This keeps the skill simple, fast to trigger, and easy to maintain. It is the recommended approach.

2. Split the implementation into multiple category-specific scripts and compose them through the skill.
   This is more modular, but it adds unnecessary structure for a report whose main value is a single aggregated output.

3. Build a fully config-driven skill with external asset definitions.
   This is flexible, but it introduces extra files and complexity that are not needed for the current use case.

**Recommended Design**

Use approach 1.

- Create a new skill named `macro-market-report`.
- Add a single Python entrypoint at `macro-market-report/scripts/market_report.py`.
- Use `yfinance.download()` to fetch recent daily data for a default cross-asset basket.
- Compute percentage changes from the downloaded close series instead of relying on unstable `info` fields.
- Print a Chinese terminal report with grouped tables, summary highlights, and fetch failures.

**Default Asset Coverage**

- Commodities: WTI crude, Brent crude, gold, silver, natural gas, copper
- Equities: S&P 500, Nasdaq Composite, Dow Jones, Russell 2000
- Volatility: VIX
- FX and dollar: DXY, EUR/USD, USD/JPY
- US rates: 13-week, 5-year, 10-year, 30-year Treasury yields
- Crypto: BTC, ETH

**Data Flow**

1. Resolve the default asset basket and any optional user-supplied tickers.
2. Fetch recent daily history in one bulk `yfinance.download()` call.
3. Normalize the returned frame per ticker.
4. For each asset, derive:
   - latest price
   - data date
   - 1-day change
   - 5-day change
   - 1-month change
5. Group rows by asset class.
6. Render a terminal report with:
   - header and data timestamp
   - short summary observations
   - per-category tables
   - missing-data or failed ticker section

**Report Shape**

- Title line: macro market snapshot date
- Summary section:
  - strongest riser
  - weakest performer
  - notable risk markers such as VIX and Treasury yields
- Category tables with fixed columns:
  - asset
  - ticker
  - latest
  - 1D
  - 5D
  - 1M
  - date
- Failure section for assets with empty or invalid history

**Error Handling**

- If `yfinance` is missing, print a clear installation command and exit non-zero.
- If some tickers fail, continue producing the rest of the report and list failures at the end.
- If the bulk request returns no usable data at all, fail with a clear message.
- If an asset lacks enough history for a given period, print `N/A` for that change field.

**Testing**

- Unit-test the series normalization and percentage-change calculations with mocked market data.
- Unit-test grouped report rendering on a small fixed dataset.
- Verify unknown or empty ticker data does not crash the report.
- Run the script end-to-end with `--help` and, if the environment has `yfinance`, a normal execution.
