# Codebase Reference Vault Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Add a new `codebase-reference-vault` skill that turns a software project into an English code-reading vault with architecture notes, code maps, module notes, flow traces, config references, and debug notes.

**Architecture:** `SKILL.md` defines the high-level workflow and naming rules. `references/templates.md` provides output templates for the vault pages, and `references/quality-checklist.md` provides the final review contract. `README.md` is updated so the new skill is discoverable.

**Tech Stack:** Markdown skill docs, repository README, local structural validation

---

### Task 1: Write design and implementation docs

**Files:**
- Create: `docs/plans/2026-04-13-codebase-reference-vault-design.md`
- Create: `docs/plans/2026-04-13-codebase-reference-vault.md`

**Step 1: Record the approved design**

Document:
- mixed code-map and reference-vault workflow
- default English output
- `CodebaseVault/` or `<project_name>_vault/` naming
- breadth-first scan followed by focused expansion

**Step 2: Record the implementation plan**

Document the file structure, templates, checklist, and validation steps.

### Task 2: Create the skill

**Files:**
- Create: `codebase-reference-vault/SKILL.md`

**Step 1: Write frontmatter**

Add:
- `name: codebase-reference-vault`
- a trigger-focused description beginning with `Use when...`

**Step 2: Write the workflow**

Cover:
- output directory naming
- repository survey
- code map generation
- architecture and module notes
- flow tracing
- config, commands, and debug references

### Task 3: Add supporting references

**Files:**
- Create: `codebase-reference-vault/references/templates.md`
- Create: `codebase-reference-vault/references/quality-checklist.md`

**Step 1: Add vault templates**

Provide templates for:
- project overview
- architecture note
- module note
- flow note
- config and commands note
- debug reference

**Step 2: Add quality checklist**

Provide checks for:
- repository coverage
- structural accuracy
- traceability to code paths
- link completeness
- English output

### Task 4: Update README

**Files:**
- Modify: `README.md`

**Step 1: Add the new skill entry**

Summarize:
- purpose
- output style
- default vault naming

**Step 2: Update the structure section**

Add the new skill directory to the repository tree.

### Task 5: Validate structure and content

**Files:**
- Verify: `codebase-reference-vault/SKILL.md`
- Verify: `codebase-reference-vault/references/templates.md`
- Verify: `codebase-reference-vault/references/quality-checklist.md`
- Verify: `README.md`

**Step 1: Run structural checks**

Run commands such as:

```bash
test -f codebase-reference-vault/SKILL.md
test -f codebase-reference-vault/references/templates.md
test -f codebase-reference-vault/references/quality-checklist.md
rg -n "^---$|^name:|^description:" codebase-reference-vault/SKILL.md
```

**Step 2: Review for scope alignment**

Confirm:
- English defaults are explicit
- the skill emphasizes both code maps and readable reference notes
- the output directory rule is clear
