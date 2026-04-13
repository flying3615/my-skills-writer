# Codebase Reference Vault Design

**Problem**

The user wants a new skill extracted from the code-oriented side of `tutor-setup`, but narrowed to code reading and reference building rather than study exercises or onboarding tasks. The output should combine a code map with a searchable reading reference, and the default language should be English.

**Approaches**

1. Build a lightweight architecture-overview skill only.
   This would be easy to maintain, but it would not provide enough depth for recurring code-reading work.

2. Build a reference-vault skill only, focused on readable notes and module summaries.
   This improves lookup quality, but it can under-emphasize structural maps, boundaries, and call flows in larger repositories.

3. Build a mixed code-map and reference-vault skill.
   Recommended. This matches the user request directly: a vault that explains the architecture, maps the major directories and boundaries, and provides readable notes for modules, flows, config, commands, and debugging.

**Recommended Design**

Use approach 3.

## Scope

The skill should:

- analyze a software project as a code-reading target
- generate a vault for architecture, modules, flows, configuration, commands, and debugging
- default to English
- use `CodebaseVault/` when no project name is provided
- use `<project_name>_vault/` when the user provides a project name

The skill should not try to exhaustively document every file. It should first sweep the full repository, then expand the core directories and most important execution paths.

## Output Model

The vault should include:

- `00-Overview/`
- `01-Architecture/`
- `02-Modules/`
- `03-Flows/`
- `04-Config-And-Commands/`
- `05-Debug-Reference/`

This gives the user both a map and a reference layer.

## Reading Strategy

The workflow should use a breadth-first pass before deep dives:

1. identify repository shape and likely entry points
2. identify core directories, ownership boundaries, and high-level dependencies
3. identify execution flows worth tracing
4. expand the modules and flows that matter most
5. write the vault after the map is stable

This keeps the skill from producing notes that are detailed but structurally wrong.

## Reference Files

Keep `SKILL.md` concise and push the note formats and review rules into:

- `codebase-reference-vault/references/templates.md`
- `codebase-reference-vault/references/quality-checklist.md`

## Verification

Validation should confirm:

- the skill defaults to English
- the output directory naming rule is explicit
- the structure supports both code maps and reference notes
- README is updated to list the new skill
