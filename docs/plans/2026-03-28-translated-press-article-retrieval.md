# Translated Press Article Retrieval Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Turn translated press outputs into a two-stage system: browse important articles first, then retrieve full article text by stable identity.

**Architecture:** Keep article extraction local and deterministic. Add stable `article_id`, normalized lookup fields, and a first-class `priority_score` to the article schema. Derive `daily_brief.json` from the ranked article store so downstream AI can browse by summary and then retrieve full text from `articles.json`.

**Tech Stack:** Python 3, JSON, local unittest

---

### Task 1: Add failing tests for stable article identity

**Files:**
- Modify: `daily-press-scanner/tests/test_scan.py`
- Modify: `daily-press-scanner/scripts/scan.py`
- Test: `daily-press-scanner/tests/test_scan.py`

**Step 1: Write the failing test**

Add tests asserting that built article candidates include:

- `article_id`
- `title`
- `title_normalized`
- `lookup_keys`

Also add a test that running candidate generation twice over the same input produces the same `article_id`.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: FAIL because those fields are not yet guaranteed.

**Step 3: Write minimal implementation**

Add helper functions to normalize article titles and generate a deterministic `article_id` from paper metadata plus block position.

**Step 4: Run test to verify it passes**

Run the same unittest command and confirm the new tests pass.

### Task 2: Add failing tests for retrieval-friendly output payloads

**Files:**
- Modify: `daily-press-scanner/tests/test_scan.py`
- Modify: `daily-press-scanner/scripts/scan.py`
- Test: `daily-press-scanner/tests/test_scan.py`

**Step 1: Write the failing test**

Add tests asserting:

- `articles.json` includes `article_id`, `priority_score`, `title_normalized`, `lookup_keys`
- `daily_brief.json` includes `article_id`, `byline`, `priority_score`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: FAIL because the payloads are not yet carrying those fields consistently.

**Step 3: Write minimal implementation**

Promote the existing ranking score into `priority_score`, enrich article payloads, and derive the brief payload from those enriched article records.

**Step 4: Run test to verify it passes**

Run the same unittest command and confirm the new tests pass.

### Task 3: Update docs and verify

**Files:**
- Modify: `daily-press-scanner/SKILL.md`
- Modify: `daily-press-scanner/scripts/scan.py`
- Modify: `daily-press-scanner/tests/test_scan.py`

**Step 1: Update docs**

Document the two-stage browse-then-expand workflow and the key article retrieval fields.

**Step 2: Run verification**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: PASS

Run: `python3 -m py_compile /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py`

Expected: PASS

**Step 3: Stop without commit**

Do not commit unless the user explicitly asks for one.
