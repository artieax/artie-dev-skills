# preset: standard

`standard` = `minimal` + `references-dir` atom.

```
frontmatter + trigger + workflow + redflag + output + requirements + references-dir
```

## Use when

- The skill needs supplementary docs alongside SKILL.md
- Eval tracking via `eval-log.jsonl` is needed
- The Workflow section is long enough to delegate parts to `references/`

## Directory layout

```
skills/<name>/
├── SKILL.md
└── references/
    ├── <topic>.md
    └── eval-log.jsonl       # optional, for iteration tracking
```

## How to scaffold

Run atomic-builder with the `standard` pick set:

```
PICK: frontmatter + trigger + workflow + redflag + output + requirements + references-dir
BUILD: skills/<name>/SKILL.md + skills/<name>/references/
```

Atom-level templates:

- Content atoms — see [`minimal`](minimal.md)
- Structural atom — [`atoms/references-dir.md`](atoms/references-dir.md)

## Workflow → references delegation

Replace any Workflow step that exceeds ~10 lines with a delegation:

```markdown
### 2. <Step>

Full protocol → `references/<topic>.md`

<2–4 line summary so the step is actionable without opening the reference>
```

## When to upgrade

- Add `scripts-dir` atom (→ [`scripts`](scripts.md)) when shell or file operations grow > 3 chained commands
- Switch to [`split`](split.md) when two or more references could each have an independent trigger phrase, or when disjoint user personas use only different phases
