---
name: codebase-reference-vault
description: Use when reading an unfamiliar software project, mapping a codebase, documenting architecture and modules, tracing request or data flows, or building a searchable code-reading vault from a repository.
---

# Codebase Reference Vault

Turn a software project into an English code-reading vault. The goal is to build a map and a reference library at the same time: architecture, module boundaries, core flows, configuration, commands, and debugging notes.

This vault should be optimized for **Obsidian Graph View**. Do not just write isolated summaries. Create dense, intentional links between overview pages, module pages, flow pages, config pages, and debug pages so the graph becomes a readable code map.

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

Required hub pages:

- `00-Overview/project-overview.md`
- `00-Overview/module-map.md`
- `00-Overview/flow-index.md`
- `01-Architecture/architecture-overview.md`
- `01-Architecture/architecture-graph.md`

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

Write the map as both:

- linked vault pages for Obsidian Graph View
- a `Mermaid` graph page that shows major modules and boundaries

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

Every core module should become its own node in the vault. Avoid collapsing many unrelated modules into one page if that makes the graph unreadable.

### 4. Trace Important Flows

Document the flows that matter most for reading the system:

- request flow
- data flow
- background job flow
- startup flow
- auth flow
- sync or ingestion flow

Trace from entry point to side effects. Name the files, modules, and boundaries involved.

Every important flow should become its own page and link to every module page it crosses.

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

1. `project-overview.md` links to the module map, flow index, architecture overview, config notes, and debug notes
2. `module-map.md` links to every core module page
3. `flow-index.md` links to every important flow page
4. architecture notes link to module pages and to `architecture-graph.md`
5. every module page links to upstream modules, downstream modules, related flows, and relevant config/debug pages
6. every flow page links back to the modules and entry points it uses
7. debug pages link to the modules or flows they help diagnose

Do not leave pages as isolated leaves unless they are intentionally peripheral.

## Graph Policy

The Obsidian graph should be useful without manual cleanup.

To achieve that:

- keep one note per core module
- keep one note per important flow
- create central hub pages instead of relying on a single overview note
- use repeated links between related notes when the relationship matters
- prefer stable note titles that match technical concepts from the codebase

Also create one `Mermaid` graph page in `01-Architecture/architecture-graph.md` to visualize the high-level structure directly inside the vault.

## Naming and Language

- write in English by default
- keep page titles short and explicit
- prefer stable technical names from the codebase over paraphrased labels
- when the repository already uses a specific term, reuse it consistently
