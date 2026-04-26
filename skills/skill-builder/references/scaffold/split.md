# preset: split

`split` = `orchestrator` parent + N × `child-skill` (each a `minimal` or `standard` combination).

```
parent:  frontmatter + trigger + workflow + redflag + output + requirements + orchestrator [+ references-dir]
child:   frontmatter + trigger + workflow + redflag + output + requirements [+ references-dir]
         × N
```

## Use when

Propose a split when any of these are true:

| Condition | How to check |
|---|---|
| 2+ sub-topics each capable of an independent trigger phrase | Can each phase be described in one sentence on its own? |
| Different user personas use only different phases | Imagine "I only want phase X" scenarios |

### When NOT to split

- Steps have strong sequential dependency (A → B → C is the only flow)
- Extracted phases don't make sense in isolation

> Size is not a trigger. A long SKILL.md is fine if every section is on the same trigger; a short SKILL.md should still split if it has two independent triggers.

## Directory layout

Choose based on whether sub-skills are user-facing or internal:

**Top-level** — sub-skills are independently triggerable:

```
skills/<name>/             ← orchestrator (calls sub-skills in order)
├── SKILL.md
└── references/

skills/<phase-a>/          ← independent skill, own trigger
└── SKILL.md

skills/<phase-b>/          ← independent skill, own trigger
└── SKILL.md
```

**Nested** — sub-skills are internal phases of the parent:

```
skills/<name>/
├── SKILL.md
├── references/
└── skills/
    ├── <phase-a>/
    │   └── SKILL.md
    └── <phase-b>/
        └── SKILL.md
```

See [`atoms/nested-sub-skill.md`](atoms/nested-sub-skill.md) for the nested pattern.

## How to scaffold

Run atomic-builder once for the parent and once per child:

**Top-level split:**

```
# Parent (orchestrator)
PICK: frontmatter + trigger + workflow + redflag + output + requirements + orchestrator
BUILD: skills/<name>/SKILL.md

# For each child phase
PICK: frontmatter + trigger + workflow + redflag + output + requirements [+ references-dir]
BUILD: skills/<phase-x>/SKILL.md
```

**Nested split:**

```
# Parent (orchestrator)
PICK: frontmatter + trigger + workflow + redflag + output + requirements + orchestrator
BUILD: skills/<name>/SKILL.md

# For each nested child phase
PICK: frontmatter + trigger + workflow + redflag + output + requirements
BUILD: skills/<name>/skills/<phase-x>/SKILL.md
```

Atom-level templates:

- `orchestrator` — [`atoms/orchestrator.md`](atoms/orchestrator.md)
- `child-skill` (top-level) — [`atoms/child-skill.md`](atoms/child-skill.md)
- `nested-sub-skill` — [`atoms/nested-sub-skill.md`](atoms/nested-sub-skill.md)
- Content atoms — see [`minimal`](minimal.md)

## Split procedure (when splitting an existing skill)

1. Create each phase as a new independent skill at `skills/<phase>/SKILL.md`
2. Replace the original SKILL.md's Workflow with `orchestrator` atom — "calls `<phase-a>` then `<phase-b>` in order"
3. Add orchestrator `-->` child edges to the dependency graph (see `dependency.md`)
4. Re-run evals on both the orchestrator and each sub-skill to confirm scores did not regress
