# Reading Vault Builder Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new `reading-vault-builder` skill that turns books into an Obsidian reading-notes vault with chapter notes, theme indexes, concept pages, quote tracking, and lightweight comprehension checks.

**Architecture:** The skill is documentation-first. `SKILL.md` defines a single-mode workflow for book sources, while `references/templates.md` provides concrete note templates and `references/quality-checklist.md` provides the final self-review contract. The repository `README.md` is updated so the new skill is discoverable.

**Tech Stack:** Markdown skill docs, repository README, local validation with shell checks

---

### Task 1: Write the design and implementation docs

**Files:**
- Create: `docs/plans/2026-04-13-reading-vault-builder-design.md`
- Create: `docs/plans/2026-04-13-reading-vault-builder.md`

**Step 1: Record the approved design**

Write the user-approved scope:
- single-mode book workflow
- primary `PDF/epub`, secondary `txt/md/url`
- Chinese notes with original terminology preserved
- chapter-first notes with theme indexes
- lightweight comprehension checks only

**Step 2: Record the implementation plan**

Document the files to create, the expected structure, and the validation steps.

### Task 2: Create the skill skeleton and main instructions

**Files:**
- Create: `reading-vault-builder/SKILL.md`

**Step 1: Write the frontmatter**

Add:
- `name: reading-vault-builder`
- a trigger-focused `description` starting with `Use when...`

**Step 2: Write the core workflow**

Include:
- CWD boundary
- supported source formats
- structure-first extraction and mapping
- chapter notes before theme notes
- Chinese output with original terms and quotations preserved
- traceability and anti-hallucination rules

### Task 3: Add supporting references

**Files:**
- Create: `reading-vault-builder/references/templates.md`
- Create: `reading-vault-builder/references/quality-checklist.md`

**Step 1: Add note templates**

Provide templates for:
- book overview
- chapter note
- theme note
- concept/person note
- quote note

**Step 2: Add self-review checklist**

Provide checks for:
- source mapping
- structural completeness
- link completeness
- quote traceability
- language consistency
- lightweight review prompts

### Task 4: Update repository discovery

**Files:**
- Modify: `README.md`

**Step 1: Add the new skill to the README list**

Summarize:
- purpose
- input types
- output structure

**Step 2: Update the repo structure section**

Add the new top-level skill directory to the tree.

### Task 5: Validate the new skill docs

**Files:**
- Verify: `reading-vault-builder/SKILL.md`
- Verify: `reading-vault-builder/references/templates.md`
- Verify: `reading-vault-builder/references/quality-checklist.md`
- Verify: `README.md`

**Step 1: Run structural checks**

Run commands such as:

```bash
test -f reading-vault-builder/SKILL.md
test -f reading-vault-builder/references/templates.md
test -f reading-vault-builder/references/quality-checklist.md
rg -n "^---$|^name:|^description:" reading-vault-builder/SKILL.md
```

**Step 2: Manually review for scope drift**

Confirm:
- no codebase mode remains
- the workflow is optimized for book notes
- references are linked from `SKILL.md`
- README describes the new skill accurately
