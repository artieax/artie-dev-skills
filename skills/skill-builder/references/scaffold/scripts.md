# preset: scripts

`scripts` = `standard` + `scripts-dir` atom.

```
frontmatter + trigger + workflow + redflag + output + requirements + references-dir + scripts-dir
```

## Use when

- A workflow operation is more than 3 shell commands chained together
- The same logic is reused across multiple workflow steps
- Output parsing or error handling would clutter SKILL.md prose

If a workflow step is one command, inline it — don't reach for `scripts/`.

## Directory layout

```
skills/<name>/
├── SKILL.md
├── references/
└── scripts/
    └── <action>.mjs
```

## How to scaffold

Run atomic-builder with the `scripts` pick set:

```
PICK: frontmatter + trigger + workflow + redflag + output + requirements
      + references-dir + scripts-dir
BUILD: skills/<name>/SKILL.md + skills/<name>/references/ + skills/<name>/scripts/
```

Atom-level templates:

- Content atoms — see [`minimal`](minimal.md)
- `references-dir` — [`atoms/references-dir.md`](atoms/references-dir.md)
- `scripts-dir` — [`atoms/scripts-dir.md`](atoms/scripts-dir.md)

## SKILL.md workflow integration

```markdown
### 2. Collect data

```bash
node scripts/collect.mjs --input <path> --output references/collected.jsonl
```

Expected output: `references/collected.jsonl` with N records.
```

## Conventions

- `.mjs` (ES module) for Node scripts; `.sh` for pure shell
- One script per atomic action — `collect.mjs`, `validate.mjs`, not `everything.mjs`
- Scripts are called from SKILL.md Workflow steps, never standalone
- Each script starts with a usage comment (see [`atoms/scripts-dir.md`](atoms/scripts-dir.md))
