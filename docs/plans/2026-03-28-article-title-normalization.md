# Article Title Normalization Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Make article retrieval more robust by normalizing common title punctuation and width variants before building `article_id` and lookup keys.

**Architecture:** Keep raw `title` readable, but strengthen `title_normalized` using light Unicode and punctuation canonicalization. Reuse the same normalized title everywhere that powers `article_id` and `lookup_keys`.

**Tech Stack:** Python 3, `unicodedata`, local unittest

---

### Task 1: Add failing normalization tests

**Files:**
- Modify: `daily-press-scanner/tests/test_scan.py`
- Test: `daily-press-scanner/tests/test_scan.py`

**Step 1: Write the failing test**

Add tests asserting:
- `normalize_article_title()` canonicalizes punctuation/width variants
- the same article title with variant punctuation/width yields the same `article_id`

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: FAIL because normalization is still whitespace-only.

### Task 2: Implement minimal canonicalization

**Files:**
- Modify: `daily-press-scanner/scripts/scan.py`
- Modify: `daily-press-scanner/tests/test_scan.py`

**Step 1: Write minimal implementation**

Use `unicodedata.normalize("NFKC", ...)` and a small punctuation translation map in `normalize_article_title()`.

**Step 2: Run tests to verify they pass**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: PASS

### Task 3: Verify and commit

**Files:**
- Modify: `daily-press-scanner/scripts/scan.py`
- Modify: `daily-press-scanner/tests/test_scan.py`
- Create: `docs/plans/2026-03-28-article-title-normalization-design.md`
- Create: `docs/plans/2026-03-28-article-title-normalization.md`

**Step 1: Run verification**

Run: `python3 -m py_compile /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py`

Expected: PASS

**Step 2: Commit only this fix and its docs if verification passes**
