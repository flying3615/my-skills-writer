# Translated Press Fast Path Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Skip unnecessary OCR work for translated PDFs with usable text layers and add a compact daily automation payload.

**Architecture:** `process_paper()` will branch into a text-layer fast path before the old render/OCR loop. Summary generation remains the source of truth, and a new `daily_brief.json` will be derived from the selected summary articles to keep downstream automation simple and stable.

**Tech Stack:** Python 3, `pdftotext`, JSON, local unittest

---

### Task 1: Add regression tests for the translated fast path

**Files:**
- Modify: `daily-press-scanner/tests/test_scan.py`
- Test: `daily-press-scanner/tests/test_scan.py`

**Step 1: Write the failing test**

Add a test that sets `extract_text_layer()` to `available`, then asserts `process_paper()` completes without calling `render_page()`, `prepare_ocr_variants()`, or `best_ocr_text_for_image_variant()`.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: FAIL because `process_paper()` still enters the OCR/render loop.

**Step 3: Write minimal implementation**

Add a text-layer fast path in `process_paper()` that builds page records from `text_layer_page_paths` and `bbox_page_blocks`, then skips OCR-only stages.

**Step 4: Run test to verify it passes**

Run the same unittest command and confirm the new test passes.

### Task 2: Add regression tests for the automation brief output

**Files:**
- Modify: `daily-press-scanner/tests/test_scan.py`
- Modify: `daily-press-scanner/scripts/scan.py`
- Test: `daily-press-scanner/tests/test_scan.py`

**Step 1: Write the failing test**

Add a test that calls summary output generation and asserts `daily_brief.json` exists with:

- `run_date`
- `papers`
- per paper `source_name`, `paper_id`, `selected_count`, `articles`
- per article `page`, `title`, `summary_text`, `topic_tags`, `text_path`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: FAIL because `daily_brief.json` is not yet written.

**Step 3: Write minimal implementation**

Add a helper that derives a compact automation payload from the selected summary articles and write it next to `summary.json`.

**Step 4: Run test to verify it passes**

Run the same unittest command and confirm the new test passes.

### Task 3: Update docs and run full verification

**Files:**
- Modify: `daily-press-scanner/SKILL.md`
- Modify: `daily-press-scanner/scripts/scan.py`
- Modify: `daily-press-scanner/tests/test_scan.py`

**Step 1: Update docs**

Document the translated fast path and the new `daily_brief.json` artifact.

**Step 2: Run verification**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: PASS

Run: `python3 -m py_compile /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py`

Expected: PASS

**Step 3: Stop without commit**

Do not commit unless the user explicitly asks for one.
