# Reading Vault Builder Design

**Problem**

The user wants a reusable skill for turning books into an Obsidian-friendly reading notes library. The reference skill, `tutor-setup`, contains a useful document workflow, but it also includes codebase onboarding behavior and mode detection that are outside the desired scope. The new skill should be single-purpose: book reading comprehension and note organization.

**Approaches**

1. Keep the original dual-mode structure and only downplay codebase mode.
   This preserves upstream complexity and leaves room for the assistant to drift into project analysis when the task is actually about books.

2. Create a single-mode reading vault skill focused on book sources and note libraries.
   Recommended. This matches the user request directly and keeps the instructions narrow: discover book sources, map chapters, produce chapter notes, then add cross-chapter indexes.

3. Build an interactive tutoring skill first and let note generation be secondary.
   This would be useful for seminar-style discussion, but it would make the default output too conversational for a notes library workflow.

**Recommended Design**

Use approach 2.

## Scope

The skill should support:

- primary inputs: `PDF`, `epub`
- secondary inputs: `txt`, `md`, `url`
- default output language: Chinese
- preservation of original terminology and key quotations
- default note style: chapter-led notes plus cross-chapter theme pages

The skill should explicitly avoid:

- codebase/project mode detection
- software onboarding workflows
- heavy exam-style question banks
- pretending unsupported quotes or page numbers are exact

## Output Model

The vault should be created under `ReadingVault/` and prioritize mixed navigation:

- `00-Overview/` for book overview, reading roadmap, and index pages
- `01-Chapters/` for chapter-by-chapter notes
- `02-Themes/` for themes or motifs that connect multiple chapters
- `03-Concepts/` for recurring concepts, people, places, or frameworks
- `04-Quotes/` for traceable quote collections
- `05-Checks/` for lightweight review prompts when the book is long enough to benefit from separate review files

This keeps the original book structure visible while allowing theme-driven recall later in Obsidian.

## Reading Workflow

The skill should use a structure-first workflow:

1. discover and confirm source files
2. extract text from primary formats before analysis
3. verify title, author, table of contents, and chapter boundaries
4. build a source map of chapters to page ranges or anchors
5. generate chapter notes before generating theme and concept indexes
6. add lightweight comprehension checks only after the note structure is stable

This prevents the assistant from writing polished notes before it actually knows the book structure.

## Content Adaptation

The workflow should adapt to the type of book:

- nonfiction: emphasize thesis, argument flow, frameworks, evidence, and definitions
- fiction: emphasize plot movement, characters, motifs, scenes, and turning points
- biography/history: emphasize timeline, actors, causality, and interpretation

The output format should remain stable even when the analysis focus shifts.

## Traceability Rules

The skill should require every major note to be traceable back to a source chapter and page range or section anchor when available. If the source lacks stable page numbers, the assistant should say so clearly and use section anchors instead.

The skill should also distinguish:

- direct source claims
- assistant synthesis
- supplemental background added to clarify the source

## References

To keep `SKILL.md` lean, the detailed note templates and review checklist should live in:

- `reading-vault-builder/references/templates.md`
- `reading-vault-builder/references/quality-checklist.md`

## Verification

Validation should focus on:

- clear frontmatter and triggering description
- stable folder structure
- no codebase workflow leakage
- explicit traceability and anti-hallucination rules
- README updated to list the new skill
