# WeRead Text Downloader Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new CLI-first `weread-text-downloader` tool and skill that exports purchased WeRead books as chapter-based plain text for AI reading.

**Architecture:** The tool uses browser automation to access the WeRead web reader, fetch book and chapter data from the page state, convert chapter HTML into plain text, and write a stable text-first output contract. The skill documents the CLI workflow and expected output.

**Tech Stack:** Python 3, `pyppeteer`, standard library HTML parsing and JSON output, unittest, markdown skill docs

---

### Task 1: Write the design and implementation docs

**Files:**
- Create: `docs/plans/2026-04-13-weread-text-downloader-design.md`
- Create: `docs/plans/2026-04-13-weread-text-downloader.md`

**Step 1: Record the approved design**

Document:
- CLI-only interface
- chapter-based text output
- no intermediate `rdata.zip`
- no `epub` generation

**Step 2: Record the implementation plan**

Document the script, tests, skill files, and validation steps.

### Task 2: Define the output contract with tests

**Files:**
- Create: `weread-text-downloader/tests/test_weread_text.py`

**Step 1: Write failing tests**

Cover:
- HTML page fragments convert to stable plain text
- output writing creates `metadata.json`, `toc.json`, and `chapters/*.txt`
- CLI argument handling routes to the download workflow

**Step 2: Run the tests to verify they fail**

Run:

```bash
python3 -m unittest weread-text-downloader/tests/test_weread_text.py -v
```

Expected: FAIL because the script does not exist yet.

### Task 3: Implement the downloader script

**Files:**
- Create: `weread-text-downloader/scripts/weread_text.py`

**Step 1: Implement the plain-text pipeline**

Add:
- CLI argument parsing
- browser launch and login
- book lookup
- chapter iteration
- HTML-to-text conversion
- output writing

**Step 2: Keep the interface minimal**

Support:
- `download <book name>`
- `--out-dir`
- `--headless`
- `--delay`
- `--verbose`

### Task 4: Add the skill and repository documentation

**Files:**
- Create: `weread-text-downloader/SKILL.md`
- Modify: `README.md`

**Step 1: Write the skill**

Document:
- dependencies
- CLI usage
- output structure
- operating assumptions

**Step 2: Update README**

Add the new skill entry and the repository structure lines.

### Task 5: Validate the implementation

**Files:**
- Verify: `weread-text-downloader/scripts/weread_text.py`
- Verify: `weread-text-downloader/tests/test_weread_text.py`
- Verify: `weread-text-downloader/SKILL.md`
- Verify: `README.md`

**Step 1: Run tests**

```bash
python3 -m unittest weread-text-downloader/tests/test_weread_text.py -v
```

**Step 2: Run syntax validation**

```bash
python3 -m py_compile weread-text-downloader/scripts/weread_text.py
```
