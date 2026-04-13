# Codebase Reference Vault Templates

Use these templates as the default output format for `codebase-reference-vault`.

## 1. Project Overview

Suggested path: `<vault_root>/00-Overview/project-overview.md`

```md
# Project Overview

## Snapshot
- Project name:
- Primary language(s):
- Framework/runtime:
- Package/build system:
- Main entry points:

## What This System Does

## Repository Shape
- `path/`:
- `path/`:
- `path/`:

## Core Areas
- [[Architecture Overview]]
- [[Module Map]]
- [[Primary Request Flow]]
- [[Config And Commands]]
- [[Debug Reference]]

## Reading Order
1. 
2. 
3. 

## Open Questions
- 
```

## 2. Architecture Overview

Suggested path: `<vault_root>/01-Architecture/architecture-overview.md`

```md
# Architecture Overview

## High-Level Structure

## Main Layers
- interface layer:
- application/business layer:
- data/integration layer:

## Entry Points
- file:
- command:
- service:

## Boundaries
- internal boundary:
- external boundary:

## Key Dependencies
- dependency:
- dependency:

## Related Notes
- [[Project Overview]]
- [[Module Map]]
- [[Primary Request Flow]]
```

## 3. Module Note

Suggested path: `<vault_root>/02-Modules/module-<name>.md`

```md
# Module: Name

## Purpose

## Key Paths
- `path/to/module`
- `path/to/file`

## Main Interfaces
- symbol:
- symbol:

## Internal Responsibilities
- 

## Dependencies
- depends on:
- used by:

## Important Files
- `path/to/file`: why it matters
- `path/to/file`: why it matters

## Reading Notes
- 

## Related Notes
- [[Architecture Overview]]
- [[Primary Request Flow]]
- [[Config And Commands]]
```

## 4. Flow Note

Suggested path: `<vault_root>/03-Flows/flow-<name>.md`

```md
# Flow: Name

## Trigger

## Entry Point
- file:
- symbol:

## Step-by-Step Path
1. 
2. 
3. 

## State Changes / Side Effects
- 

## Key Modules
- [[Module: A]]
- [[Module: B]]

## Failure Points
- 

## Related Notes
- [[Architecture Overview]]
- [[Debug Reference]]
```

## 5. Config And Commands

Suggested path: `<vault_root>/04-Config-And-Commands/config-and-commands.md`

```md
# Config And Commands

## Important Config Files
- `path/to/config`:
- `path/to/config`:

## Important Environment Variables
- `ENV_NAME`:
- `ENV_NAME`:

## Common Commands
- install:
- dev:
- build:
- test:
- lint:

## Notes
- 

## Related Notes
- [[Project Overview]]
- [[Debug Reference]]
```

## 6. Debug Reference

Suggested path: `<vault_root>/05-Debug-Reference/debug-reference.md`

```md
# Debug Reference

## Good Starting Points
- file:
- command:
- log source:

## Common Failure Areas
- 

## Traces To Follow
- request trace:
- startup trace:
- background job trace:

## Useful Commands
- 

## Related Notes
- [[Architecture Overview]]
- [[Primary Request Flow]]
- [[Config And Commands]]
```
