# Codebase Reference Vault Quality Checklist

Review this before delivery.

## 1. Coverage

- [ ] The vault root follows the naming rule: `CodebaseVault/` or `<project_name>_vault/`
- [ ] The repository was surveyed broadly before deep dives
- [ ] The most important directories and entry points are covered
- [ ] Generated, vendor, or build output paths were not treated as core source without reason

## 2. Code Map Quality

- [ ] The vault explains the top-level repository shape
- [ ] Architecture notes identify major layers or boundaries
- [ ] Core modules and dependencies are mapped clearly
- [ ] Important flows are traced from entry point to side effects
- [ ] A dedicated `Module Map` page exists
- [ ] A dedicated `Flow Index` page exists
- [ ] A dedicated `Architecture Graph` page exists with a Mermaid graph

## 3. Reference Quality

- [ ] Module notes explain purpose, key paths, and interfaces
- [ ] Flow notes name the actual files, modules, or commands involved
- [ ] Config and command notes are practical and specific
- [ ] Debug notes include real entry points for investigation
- [ ] Core module pages are not collapsed into overly broad summaries

## 4. Navigation

- [ ] Overview pages link to architecture, modules, flows, config, and debug notes
- [ ] Module notes link to related flows or architecture notes
- [ ] Flow notes link back to modules and debug references
- [ ] The vault is easy to browse without re-reading the whole repository
- [ ] The graph is hub-based rather than a flat pile of disconnected notes
- [ ] Core module and flow pages have enough wikilinks to appear connected in Obsidian Graph View

## 5. Language And Terminology

- [ ] Default output is English
- [ ] Terms from the repository are reused consistently
- [ ] Page titles are short, clear, and stable
- [ ] Notes describe the codebase directly instead of drifting into generic explanations
