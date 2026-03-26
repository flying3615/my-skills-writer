# Daily Press Scanner Executable Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn `daily-press-scanner` into a runnable local skill with a script that downloads newspaper PDF URLs, performs local OCR-only scanning, identifies opinion-style pages and topic hits, and writes structured JSON plus debug artifacts.

**Architecture:** Keep the skill split into two layers. The Python script handles deterministic local work only: download, render, OCR, heuristic topic detection, opinion candidate detection, and JSON/debug output. The `SKILL.md` explains when to use the script, how to run it, what the output means, and how the assistant should interpret `results.json` instead of redoing OCR inside the model.

**Tech Stack:** Python 3.12, `pypdf`, `Pillow`, `pdftoppm`, `tesseract`, Markdown, JSON.

---

### Task 1: Add script directory and define CLI contract

**Files:**
- Create: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py`
- Modify: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/SKILL.md`

**Step 1: Define CLI arguments**

The script should support:

```text
python3 daily-press-scanner/scripts/scan.py \
  --urls urls.txt \
  --topics tariffs,ai,china,fed,war,markets \
  --out-dir ./out
```

Required behavior:
- `--urls`: newline-delimited PDF URLs
- `--topics`: optional comma-separated topic list
- `--out-dir`: output directory root
- optional `--max-pages`: limit quick scan pages per paper
- optional `--dpi`: OCR render DPI

**Step 2: Define output directory structure**

The script must create:

```text
out/
  results.json
  pdfs/
  ocr/
  previews/
```

**Step 3: Keep the script dependency-light**

Do not call remote APIs.
Do not depend on MoneyPrinter.
Do not require API keys.

### Task 2: Implement deterministic local pipeline

**Files:**
- Create: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py`

**Step 1: Download PDFs**

For each URL:
- infer a stable local filename
- save under `out/pdfs/`
- record download failures into `errors`

**Step 2: Read page count**

Use `pypdf.PdfReader` to get page count even when pages have no text layer.

**Step 3: Render and OCR pages**

For each scanned page up to `--max-pages`:
- render page image with `pdftoppm`
- preprocess with Pillow
- split wide page into left/right OCR chunks when needed
- run local `tesseract` with English
- save raw OCR text under `out/ocr/<paper>/page-xxx.txt`

**Step 4: Build page-level fast index**

For each OCR page:
- derive a title-like line
- extract a short snippet from early text
- tag entities/keywords heuristically
- classify whether page looks like opinion/commentary

### Task 3: Implement topic and opinion heuristics

**Files:**
- Create: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py`

**Step 1: Topic matching**

Create a small built-in keyword map, for example:
- `tariffs`: tariff, trade, duty, import, export
- `ai`: ai, artificial intelligence, chip, model, Nvidia, OpenAI
- `china`: china, beijing, xi, yuan, property
- `fed`: inflation, rates, powell, federal reserve
- `war`: missile, strike, gaza, ukraine, iran, israel
- `markets`: stocks, yields, bonds, market, equities

Support user-provided topics by:
- exact lowercased keyword
- singular/plural loose contains

**Step 2: Opinion candidate detection**

Use simple deterministic signals:
- opinion words in OCR text: opinion, editorial, analysis, column, review, comment
- title-like lines near `By ...`
- high ratio of prose versus tables/numbers

**Step 3: Score and rank**

Each `topic_hit` should include:
- `topic`
- `score`
- `matched_terms`

Each `opinion_candidate` should include:
- `confidence`
- `section_guess`

### Task 4: Write results and preview artifacts

**Files:**
- Create: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py`

**Step 1: Write `results.json`**

Top-level structure:

```json
{
  "run_date": "",
  "inputs": [],
  "papers": [],
  "page_index": [],
  "opinion_candidates": [],
  "topic_hits": [],
  "errors": []
}
```

**Step 2: Write human-inspectable previews**

Under `out/previews/`, write per-paper text summaries for debugging:
- top title-like line per page
- snippet
- opinion guess
- topic hits

**Step 3: Make failures non-fatal**

Bad PDF, OCR failure, or page-level failure must be appended to `errors` without aborting the batch.

### Task 5: Update the skill instructions

**Files:**
- Modify: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/SKILL.md`
- Modify: `/Users/yufei/Documents/git/my-skill-writer/README.md`

**Step 1: Replace abstract-only guidance with executable usage**

Add:
- dependency list
- exact run commands
- explanation of `results.json`
- explanation that the assistant should consume the JSON instead of repeating OCR

**Step 2: Document local prerequisites**

State that the environment must provide:
- `python3`
- `pdftoppm`
- `tesseract`

**Step 3: Keep README discoverable**

Update the `Daily Press Scanner` entry so it explicitly says this skill now includes a local scanning script.

### Task 6: Verify

**Files:**
- Verify: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py`
- Verify: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/SKILL.md`
- Verify: `/Users/yufei/Documents/git/my-skill-writer/README.md`

**Step 1: Syntax check**

Run:

```bash
python3 -m py_compile /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py
```

Expected: no output

**Step 2: Smoke test with a tiny URL file**

Run:

```bash
python3 /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py \
  --urls /tmp/press_urls.txt \
  --topics tariffs,ai \
  --out-dir /tmp/press_scan_out \
  --max-pages 2
```

Expected:
- `results.json` exists
- `pdfs/`, `ocr/`, `previews/` are created
- JSON has `papers`, `page_index`, `opinion_candidates`, `topic_hits`, `errors`

**Step 3: Review git diff**

Run:

```bash
git -C /Users/yufei/Documents/git/my-skill-writer diff -- README.md daily-press-scanner/SKILL.md daily-press-scanner/scripts/scan.py docs/plans/2026-03-26-daily-press-scanner-executable.md
```

**Step 4: Commit**

```bash
git -C /Users/yufei/Documents/git/my-skill-writer add README.md daily-press-scanner/SKILL.md daily-press-scanner/scripts/scan.py docs/plans/2026-03-26-daily-press-scanner-executable.md
git -C /Users/yufei/Documents/git/my-skill-writer commit -m "Add executable daily press scanner skill"
```
