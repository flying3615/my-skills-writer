# Macro Market Report Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new `macro-market-report` skill that generates a Chinese terminal report for major macro assets using `yfinance`, including latest price and 1-day, 5-day, and 1-month percentage changes.

**Architecture:** The skill will contain one Python script that defines the default asset basket, downloads recent daily history in bulk, derives per-asset metrics, and renders a grouped plain-text report. Tests will validate data extraction, return calculations, and report formatting without relying on live network responses.

**Tech Stack:** Python 3, `yfinance`, standard library `argparse`, optional `pytest`

---

### Task 1: Add failing tests for report calculations and formatting

**Files:**
- Create: `macro-market-report/tests/test_market_report.py`
- Test: `macro-market-report/tests/test_market_report.py`

**Step 1: Write the failing test**

Add tests that expect:
- the script can extract close series from a mocked multi-ticker download frame
- 1D, 5D, and 1M percentage changes are computed correctly
- report rendering includes grouped category headers and `N/A` when history is insufficient

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest macro-market-report/tests/test_market_report.py -q`
Expected: FAIL because `macro-market-report/scripts/market_report.py` does not exist yet

**Step 3: Write minimal implementation**

Create `macro-market-report/scripts/market_report.py` with:
- default asset metadata
- history extraction helpers
- percentage-change helpers
- report rendering helpers

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest macro-market-report/tests/test_market_report.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add macro-market-report/tests/test_market_report.py macro-market-report/scripts/market_report.py
git commit -m "feat: add macro market report core"
```

### Task 2: Add the skill definition and usage guidance

**Files:**
- Create: `macro-market-report/SKILL.md`
- Modify: `README.md`

**Step 1: Write the failing test**

Add or update tests and checks that expect:
- the new skill exists with valid frontmatter
- the skill instructions reference the correct script path and describe the intended trigger conditions

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest macro-market-report/tests/test_market_report.py -q`
Expected: FAIL if the skill metadata contract is not implemented yet

**Step 3: Write minimal implementation**

Create `macro-market-report/SKILL.md` with:
- concise trigger-focused frontmatter
- dependency note for `yfinance`
- example prompts
- execution command
- usage notes for default basket and optional extra tickers

Update `README.md` to list the new skill and its purpose.

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest macro-market-report/tests/test_market_report.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add macro-market-report/SKILL.md README.md
git commit -m "feat: document macro market report skill"
```

### Task 3: Verify CLI behavior

**Files:**
- Modify: `macro-market-report/scripts/market_report.py`
- Test: `macro-market-report/tests/test_market_report.py`

**Step 1: Write the failing test**

Add a CLI-oriented test that expects:
- `--help` prints usage
- optional `--extra` tickers merge into the default basket
- failed tickers appear in the report footer instead of crashing

**Step 2: Run test to verify it fails**

Run: `python3 -m pytest macro-market-report/tests/test_market_report.py -q`
Expected: FAIL until CLI helpers and failure tracking are complete

**Step 3: Write minimal implementation**

Add CLI parsing and merge logic with:
- optional `--extra`
- optional `--tickers-only`
- deterministic rendering of failure lines

**Step 4: Run test to verify it passes**

Run: `python3 -m pytest macro-market-report/tests/test_market_report.py -q`
Expected: PASS

**Step 5: Commit**

```bash
git add macro-market-report/scripts/market_report.py macro-market-report/tests/test_market_report.py
git commit -m "feat: add macro market report cli options"
```

### Task 4: End-to-end verification

**Files:**
- Verify: `macro-market-report/scripts/market_report.py`
- Verify: `macro-market-report/SKILL.md`
- Verify: `README.md`

**Step 1: Run automated tests**

Run: `python3 -m pytest macro-market-report/tests/test_market_report.py -q`
Expected: PASS

**Step 2: Run CLI help**

Run: `python3 macro-market-report/scripts/market_report.py --help`
Expected: usage text

**Step 3: Run live report if dependencies exist**

Run: `python3 macro-market-report/scripts/market_report.py`
Expected: grouped Chinese market report, or a clear dependency message if `yfinance` is not installed

**Step 4: Review docs**

Check that `README.md` and `macro-market-report/SKILL.md` agree on:
- script path
- dependency note
- default basket purpose

**Step 5: Commit**

```bash
git add docs/plans/2026-03-29-macro-market-report-design.md docs/plans/2026-03-29-macro-market-report.md
git commit -m "docs: add macro market report design and plan"
```
