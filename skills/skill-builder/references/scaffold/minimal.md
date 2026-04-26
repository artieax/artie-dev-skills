# preset: minimal

`minimal` = the six required content atoms only.

```
frontmatter + trigger + workflow + redflag + output + requirements
```

No `references/`, no `scripts/`, no children.

## Use when

- The skill has ≤ 3 workflow steps
- No supplementary docs are needed
- Eval tracking can wait until the skill grows

## Directory layout

```
skills/<name>/
└── SKILL.md
```

## How to scaffold

Run atomic-builder with the `minimal` pick set:

```
PICK: frontmatter + trigger + workflow + redflag + output + requirements
BUILD: skills/<name>/SKILL.md
```

Each atom has its own template — open the atom files for the exact section structure:

- [`atoms/frontmatter.md`](atoms/frontmatter.md)
- [`atoms/trigger.md`](atoms/trigger.md)
- [`atoms/workflow.md`](atoms/workflow.md)
- [`atoms/redflag.md`](atoms/redflag.md)
- [`atoms/output.md`](atoms/output.md)
- [`atoms/requirements.md`](atoms/requirements.md)

## Composed SKILL.md template

```markdown
---
name: <kebab-case-name>
description: '<one-line trigger description. Use when the user says "X" or "Y">'
author: '@artieax'
---

# <name>

<What the skill does in 1–2 sentences. Lead with the user's outcome.>

## When to use

- "<trigger phrase 1>"
- "<trigger phrase 2>"
- "<trigger phrase 3>"

**Do not trigger** when:

- <case where another skill is the right choice>
- <case that belongs to an adjacent skill>

## Workflow

### 1. <First step>

<Explanation>

### 2. <Next step>

<Explanation>

## Red flags

### Always

- <pick from references/red-flags.md#always-patterns>

### Never

- <pick from references/red-flags.md#never-patterns>

## Output

<Format of the deliverable — file, commit, report, or message — be specific.>

## Requirements

<!-- Used by Pipeline executor's acceptance-gate. RFC 2119 priorities; at least one MUST required. -->

- <requirement 1> `MUST`
- <requirement 2> `SHOULD`
- <requirement 3> `MAY`
```

## When to upgrade

Add the `references-dir` atom (→ [`standard`](standard.md)) when:

- The Workflow section exceeds ~40 lines
- You need an `eval-log.jsonl` for tracking iterations
- Protocol details would clutter the main SKILL.md
