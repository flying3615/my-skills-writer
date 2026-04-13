---
name: codebase-reference-vault
description: Use when reading an unfamiliar software project, mapping a codebase, documenting architecture and modules, tracing request or data flows, or building a searchable code-reading vault from a repository.
---

# Codebase Reference Vault

Turn a software project into an English code-reading vault. The goal is to build a map and a reference library at the same time: architecture, module boundaries, core flows, configuration, commands, and debugging notes.

Default rules:

- default output language: English
- default output directory: `CodebaseVault/`
- if the user provides a project name: `<project_name>_vault/`
- start with a repository-wide sweep, then expand the core directories and most important flows

Use [references/templates.md](references/templates.md) for output formats and [references/quality-checklist.md](references/quality-checklist.md) before delivery.

## Output Directory

Choose the vault root like this:

- no project name provided: `CodebaseVault/`
- project name provided: `<project_name>_vault/`

Create this structure:

```text
<vault_root>/
  00-Overview/
  01-Architecture/
  02-Modules/
  03-Flows/
  04-Config-And-Commands/
  05-Debug-Reference/
```

## Workflow

### 1. Survey the Repository

Start broad.

- identify top-level directories
- identify likely entry points
- identify framework, runtime, and build system
- identify primary configs, env files, and command entry points
- identify generated, vendor, or build output directories and avoid treating them as first-class source

Do not expand every file. First build a reliable map of the repository shape.

### 2. Build the Code Map

Create a structural map before writing long notes.

Capture:

- major directories and their roles
- system boundaries
- internal dependencies
- external service boundaries
- execution entry points
- central abstractions, shared libraries, and cross-cutting layers

The code map should answer:

- where requests or jobs enter
- where core business logic lives
- where persistence, API, worker, UI, or integration layers sit
- which modules are central versus peripheral

### 3. Expand Core Modules

After the map is stable, document the important modules and directories.

For each core module, capture:

- purpose
- key files
- exported symbols or main interfaces
- internal responsibilities
- dependencies
- upstream and downstream relationships

Prefer module-level notes over file-by-file notes unless a specific file is unusually important.

### 4. Trace Important Flows

Document the flows that matter most for reading the system:

- request flow
- data flow
- background job flow
- startup flow
- auth flow
- sync or ingestion flow

Trace from entry point to side effects. Name the files, modules, and boundaries involved.

### 5. Capture Config, Commands, and Debug Paths

Create practical reference notes for:

- major config files
- important environment variables
- startup, test, build, and local-dev commands
- common logs, breakpoints, stack traces, and debugging entry points

This should make the vault useful during real code reading, not just as a static summary.

## Depth Policy

Use a breadth-first scan, then expand the core areas.

- cover the whole repository shape first
- expand the most central directories next
- only drill to file-level detail where it changes understanding

When the repo is large, prefer a strong map with selective deep dives over shallow notes for every folder.

## Linking Rules

Use internal links so the vault is navigable:

1. `00-Overview/` links to architecture, modules, flows, config, and debug sections
2. architecture notes link to module pages
3. module notes link to related flows and configs
4. flow notes link back to the modules and entry points they use
5. debug pages link to the modules or flows they help diagnose

## Naming and Language

- write in English by default
- keep page titles short and explicit
- prefer stable technical names from the codebase over paraphrased labels
- when the repository already uses a specific term, reuse it consistently
