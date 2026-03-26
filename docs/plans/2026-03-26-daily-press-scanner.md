# Daily Press Scanner Skill Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a reusable skill that guides an AI assistant to scan batches of scanned newspaper PDFs from URL inputs, prioritize opinion/commentary pages and topic hits, and output structured JSON for downstream workflows.

**Architecture:** Create one new skill folder with a concise `SKILL.md` that describes triggers, workflow, OCR-first scanning strategy, JSON output shape, and constraints. Update the repository `README.md` so the new skill is listed and discoverable.

**Tech Stack:** Markdown, repository skill conventions, JSON schema examples.

---

### Task 1: Inspect repository conventions

**Files:**
- Modify: `/Users/yufei/Documents/git/my-skill-writer/README.md`
- Create: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/SKILL.md`

**Step 1: Review existing skill style**

Read:
- `/Users/yufei/Documents/git/my-skill-writer/news-summarizer/SKILL.md`
- `/Users/yufei/Documents/git/my-skill-writer/stock-value-scanner/SKILL.md`
- `/Users/yufei/Documents/git/my-skill-writer/README.md`

**Step 2: Define minimal skill scope**

Document the skill around:
- URL-based PDF batch input
- OCR-first fast scan
- Opinion/commentary prioritization
- Topic-hit detection
- Structured JSON output
- Explicit non-goals: no video generation, no full article stitching by default

**Step 3: Commit plan artifact**

Commit later with implementation changes.

### Task 2: Add the new skill document

**Files:**
- Create: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/SKILL.md`

**Step 1: Write frontmatter**

Use a CSO-friendly frontmatter:
- `name: daily-press-scanner`
- description beginning with `Use when...`

**Step 2: Write the skill body**

Include sections for:
- Overview
- When to use
- Inputs
- Output JSON shape
- Fast scan workflow
- Deep extract workflow
- Topic matching rules
- Error handling
- Non-goals

**Step 3: Include concrete examples**

Add example prompts and one JSON example showing:
- `papers`
- `opinion_candidates`
- `topic_hits`
- `errors`

### Task 3: Update repository discovery docs

**Files:**
- Modify: `/Users/yufei/Documents/git/my-skill-writer/README.md`

**Step 1: Add a new section entry**

Add `Daily Press Scanner` to the included skills list with a short Chinese description.

**Step 2: Keep directory structure up to date**

Extend the tree example to include `daily-press-scanner/`.

### Task 4: Verify and summarize

**Files:**
- Verify: `/Users/yufei/Documents/git/my-skill-writer/daily-press-scanner/SKILL.md`
- Verify: `/Users/yufei/Documents/git/my-skill-writer/README.md`

**Step 1: Sanity-check wording**

Confirm the skill is concise, trigger-oriented, and not coupled to MoneyPrinter.

**Step 2: Verify git diff**

Run:
```bash
git -C /Users/yufei/Documents/git/my-skill-writer diff -- README.md daily-press-scanner/SKILL.md docs/plans/2026-03-26-daily-press-scanner.md
```

**Step 3: Commit when requested**

Suggested commit:
```bash
git -C /Users/yufei/Documents/git/my-skill-writer add README.md daily-press-scanner/SKILL.md docs/plans/2026-03-26-daily-press-scanner.md
git -C /Users/yufei/Documents/git/my-skill-writer commit -m "Add daily press scanner skill"
```
