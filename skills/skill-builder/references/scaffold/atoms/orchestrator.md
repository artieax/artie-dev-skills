# atom: orchestrator

A SKILL.md whose Workflow delegates to other top-level skills, run in a fixed order.

## When to include

- The skill is the entry point for a multi-phase pipeline
- Each phase is itself an independently triggerable skill
- The user can also invoke individual phases without the orchestrator

If the phases can't stand alone, you don't need an orchestrator — keep it as a single skill.

If the right phase depends on the user's intent rather than always running in order, use [`match-router`](match-router.md) instead of (or inside) this atom.

## Layout

Two valid patterns — choose based on whether sub-skills have standalone user value:

**Top-level** (sub-skills are user-triggerable on their own):

```
skills/<name>/                    ← orchestrator
├── SKILL.md
└── references/

skills/<phase-a>/                 ← independent skill, own trigger
└── SKILL.md

skills/<phase-b>/                 ← independent skill, own trigger
└── SKILL.md
```

**Nested** (sub-skills are internal phases, not worth polluting `skills/`):

```
skills/<name>/                    ← orchestrator
├── SKILL.md
├── references/
└── skills/
    ├── <phase-a>/
    │   └── SKILL.md
    └── <phase-b>/
        └── SKILL.md
```

See [`nested-sub-skill`](nested-sub-skill.md) for the nested atom and when to prefer it over top-level.

## SKILL.md skeleton

```markdown
---
name: <name>
description: 'Orchestrates <phase-a> → <phase-b> → <phase-c>. Use when the user says "full X flow".'
author: '@artieax'
---

# <name>

Runs the full <X> pipeline: <phase-a> → <phase-b> → <phase-c>.

## When to use

- "full <X> flow"
- "run everything for <X>"

**Do not trigger** when the user only needs one phase — call that sub-skill directly.

## Workflow

### 1. Run <phase-a>

→ `skills/<phase-a>/SKILL.md`

### 2. Run <phase-b>

→ `skills/<phase-b>/SKILL.md`

### 3. Run <phase-c>

→ `skills/<phase-c>/SKILL.md`

## Output

Combined output of all phases.

## Requirements

- Sub-skills must exist before the orchestrator is used `MUST`
```

## Dependency graph

Add orchestrator `-->` child edges to the dependency graph (see `dependency.md`):

```
<name> --> <phase-a>
<name> --> <phase-b>
<name> --> <phase-c>
```
