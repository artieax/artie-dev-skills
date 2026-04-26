---
name: skill-creator
description: 'Create, iterate, evaluate, and improve agent skills — end-to-end. Covers scaffolding, worktree-based iteration, quality metrics, prompt evals, auto sub-skill splitting, auto dependency registration, and periodic improvement scheduling. Use when building a new skill or improving an existing one in any skills repo.'
author: '@artieax'
---

# skill-creator

A meta-skill that covers the full lifecycle of an agent skill — from design and scaffolding through worktree-based iteration, eval scoring, sub-skill splitting, dependency registration, and scheduled improvement. Skills aren't "done" when first written; this skill keeps them improving.

## When to use

- "Create a new skill"
- "Scaffold a skill for X"
- "Iterate on this skill with worktrees"
- "Evaluate / score this skill's quality"
- "This skill is too big — split it"
- "Register the dependencies for this skill"
- "Set up periodic skill improvement"

**Do not trigger** when:
- Editing documentation unrelated to a skill (use Edit directly)
- Developing non-skill code (use a purpose-specific skill)

## Workflow overview

```
CREATE ──→ SCAFFOLD ──→ ITERATE (worktree loop)
                             │
                             ▼
                        EVALS (score)
                             │
                    pass ────┴──── fail
                     │              │
                   MERGE          REFINE
                     │
               AUTO-DEPS ──→ AUTO-SPLIT? ──→ SCHEDULE
```

---

## Phase 1 — CREATE: skill design

### 1.1 Pre-check

```bash
ls skills/
```

Duplicate check: confirm no existing skill has the same trigger. If one does, decide whether extending it is enough.

### 1.2 The three design questions

1. **What is the trigger phrase?** — Write 1–3 natural-language phrases the user would say.
2. **What is the output?** — File / commit / report / message — be concrete.
3. **Where is the boundary with adjacent skills?** — One sentence separating this skill's scope from its neighbors.

If you can't answer all three, it's too early to create a skill.

### 1.3 Persistence tier decision

| Data character | Tier | Location |
|---|---|---|
| Config, reports, human-readable docs | A (markdown) | `references/` |
| Logs, append-heavy structured data | B (JSONL) | `references/*.jsonl` |

Default to Tier A.

---

## Phase 2 — SCAFFOLD: file generation

Full templates → `references/scaffold.md`

### Minimum layout

```
skills/<name>/
└── SKILL.md
```

### Recommended layout (medium skill)

```
skills/<name>/
├── SKILL.md
└── references/
    ├── <topic-a>.md
    └── <topic-b>.md
```

### Large skill (sub-skill candidate)

```
skills/<name>/
├── SKILL.md
├── references/
└── sub-skills/
    ├── <part-a>/SKILL.md
    └── <part-b>/SKILL.md
```

### Required SKILL.md sections

```markdown
---
name: <kebab-case>
description: '<trigger description — 1 sentence>'
author: '@artieax'
---

# <name>

<What the skill does in 1–2 sentences. Lead with the user's outcome.>

## When to use
- "<trigger phrase>"

**Do not trigger** when:
- <case where another skill is the right choice>

## Workflow
### 1. ...

## Red flags
### Always
- ...

### Never
- ...

## Output
<Format of the deliverable — file path, commit, report, message.>
```

---

## Phase 3 — ITERATE: worktree loop

Full protocol → `references/iteration.md`

### Branch naming

| Type | Pattern |
|---|---|
| New skill | `feature/<skill-name>` |
| Improvement iteration | `iter/<skill-name>-v<N>` |
| Refactor | `refactor/<skill-name>` |

### Parallel worktree improvement

When testing multiple improvement ideas simultaneously:

```bash
# Worktree A: workflow improvement
git worktree add ../skill-creator-iter-a iter/skill-creator-v2-workflow

# Worktree B: metrics strengthening
git worktree add ../skill-creator-iter-b iter/skill-creator-v2-metrics

# Run evals in both → compare scores → cherry-pick the winner
```

### Iteration exit criteria

- All metrics ≥ **7 / 10**, **or**
- ≥ **+15%** improvement over the previous version

Neither met → run another iteration.

---

## Phase 4 — EVALS: quality scoring

Full framework → `references/evals.md`

### Metrics (0–10 each)

| Metric | Definition |
|---|---|
| **trigger_precision** | How clear and unambiguous the trigger phrases are |
| **workflow_coverage** | Whether the Workflow covers all stated use cases |
| **output_clarity** | How concretely the Output section defines format, location, and volume |
| **red_flag_completeness** | Whether Red flags capture the important edge cases and side effects |
| **dep_accuracy** | Whether dependent skills are correctly declared |

Scoring method: pass the SKILL.md to Claude and ask for a 0–10 score with reasoning per metric.

### Eval log

```
references/eval-log.jsonl
```

```jsonl
{"version":"v1","date":"2026-04-25","scores":{"trigger_precision":8,"workflow_coverage":7,"output_clarity":8,"red_flag_completeness":7,"dep_accuracy":9},"total":39,"top_improvement":"workflow_coverage: Do not trigger cases are not reflected in Workflow","notes":"initial eval"}
```

---

## Phase 5 — AUTO-DEPS: dependency registration

Full protocol → `references/dependency.md`

### Auto-detection logic

Scan the SKILL.md for references to other skill names:

```bash
# Get list of existing skills
ls skills/

# Check for references inside the new SKILL.md
grep -E "(bommit|pluginize|<other-skill>)" skills/<name>/SKILL.md
```

Detected references are proposed for registration in `dependency-graph.md`:

```
Detected new dependency edges:
  skill-creator -.-> bommit    (SKILL.md line 82 references bommit)

Add to dependency-graph.md? [Y/n]
```

### Dependency types

- `-->` hard dependency: called at runtime (breaks without it)
- `-.->` soft reference: recommended but not required

---

## Phase 6 — AUTO-SPLIT: sub-skill decomposition

Full criteria → `references/scaffold.md#sub-skill-split`

### Split triggers

Propose a split when any of these are true:

1. SKILL.md exceeds **200 lines** and has **3+ workflow phases**
2. There are **2+ sub-topics** each capable of having an independent trigger phrase
3. Different user personas use only different phases

### Split procedure

1. Extract each phase into `sub-skills/<phase>/SKILL.md`
2. Rewrite the parent `SKILL.md` as an orchestrator (what calls what and in which order)
3. Add parent → child edges to the dependency graph
4. Re-run evals to confirm scores did not regress

---

## Phase 7 — SCHEDULE: periodic improvement

Full setup → `references/evals.md#periodic`

### Monthly skill review

```jsonl
{
  "name": "skill-monthly-review",
  "schedule": "0 9 1 * *",
  "checks": [
    "eval total < 35 → propose improvement iteration",
    "SKILL.md > 200 lines → propose split",
    "unregistered dependencies detected → propose dependency-graph update"
  ]
}
```

---

## Red flags

### Always

- Answer the three design questions before writing any SKILL.md
- Create a branch before starting work — never commit to main directly
- Run evals before merging
- Update the dependency graph before opening a PR
- Update the skill table in AGENTS.md

### Never

- Never `git push` without an explicit instruction to do so
- Never start writing SKILL.md before answering the three design questions
- Never declare a skill "done" without running evals
- Never leave a 200+ line SKILL.md without proposing a split
- Never skip hooks with `--no-verify`

---

## Output

```
📋 DESIGN
  ✅ Trigger: "create a new skill" / "scaffold a skill for X"
  ✅ Output: SKILL.md + references/*.md
  ✅ Boundary: bommit handles commits only; skill-creator handles design → improvement

🌿 BRANCH: feature/<skill-name> (artie-dev-skills)

📦 SCAFFOLD: skills/<name>/ created
  └── SKILL.md
  └── references/ (N files)

📊 EVAL v1
  trigger_precision:    8/10
  workflow_coverage:    7/10
  output_clarity:       8/10
  red_flag_completeness:7/10
  dep_accuracy:         9/10
  total: 39/50

🔗 DEPS: skill-creator -.-> bommit added to dependency-graph.md

🚫 PUSH: waiting — will not push until explicitly told to
```
