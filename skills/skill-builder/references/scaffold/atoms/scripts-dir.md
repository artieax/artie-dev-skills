# atom: scripts-dir

Adds a `scripts/` directory for encapsulated shell or file operations called from the Workflow.

## When to include

- The operation is more than 3 shell commands chained together
- The logic needs to be reusable across multiple workflow steps
- Output parsing or error handling would clutter the SKILL.md prose

If a workflow step is a single command, inline it — don't add a script.

## Layout

```
skills/<name>/
├── SKILL.md
├── references/                 # often paired with references-dir atom
└── scripts/
    ├── <action>.mjs            # Node ES module
    └── <action>.sh             # pure shell
```

## File conventions

- `.mjs` (ES module) for Node scripts; `.sh` for pure shell
- One script per atomic action — `collect.mjs`, `validate.mjs`, not `everything.mjs`
- Scripts are called from SKILL.md Workflow steps, never standalone

## Script header

Every script starts with a usage comment:

```js
// Usage: node scripts/<action>.mjs --input <path> [--dry-run]
// Output: writes to <path>
```

```sh
#!/usr/bin/env bash
# Usage: scripts/<action>.sh <arg>
# Output: <description>
set -euo pipefail
```

## SKILL.md integration

```markdown
### 2. Collect data

```bash
node scripts/collect.mjs --input <path> --output references/collected.jsonl
```

Expected output: `references/collected.jsonl` with N records.
```
