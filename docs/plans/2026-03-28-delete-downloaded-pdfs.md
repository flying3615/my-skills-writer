# Delete Downloaded PDFs Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Remove downloaded working-copy PDFs after each paper finishes processing.

**Architecture:** Keep the download/copy step unchanged for processing, then delete the working PDF in a `finally` block inside `process_paper()`. Outputs keep the source URL but no longer advertise a deleted `local_pdf` path.

**Tech Stack:** Python 3, local unittest

---

### Task 1: Add failing cleanup test

**Files:**
- Modify: `daily-press-scanner/tests/test_scan.py`
- Test: `daily-press-scanner/tests/test_scan.py`

**Step 1: Write the failing test**

Add a test asserting that a downloaded PDF copy is deleted after `process_paper()` completes and that `paper["local_pdf"]` is `None`.

**Step 2: Run test to verify it fails**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: FAIL because the PDF copy still exists and `local_pdf` still points at it.

### Task 2: Implement minimal cleanup

**Files:**
- Modify: `daily-press-scanner/scripts/scan.py`
- Modify: `daily-press-scanner/tests/test_scan.py`

**Step 1: Write minimal implementation**

Delete the downloaded PDF copy in `process_paper()` after processing is complete, regardless of success or failure, and set `local_pdf` to `None`.

**Step 2: Run tests to verify they pass**

Run: `python3 -m unittest /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/tests/test_scan.py -v`

Expected: PASS

### Task 3: Verify

**Files:**
- Modify: `daily-press-scanner/scripts/scan.py`
- Modify: `daily-press-scanner/tests/test_scan.py`

**Step 1: Run verification**

Run: `python3 -m py_compile /Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/scripts/scan.py`

Expected: PASS
