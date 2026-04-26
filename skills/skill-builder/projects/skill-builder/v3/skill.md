---
name: skill-creator
description: 'Create, iterate, evaluate, and improve agent skills — end-to-end. Covers scaffolding, worktree-based iteration, eval pipelines, auto skill splitting, auto dependency registration, and periodic improvement scheduling. Use when building a new skill or improving an existing one in any skills repo.'
author: '@artieax'
---

# skill-creator

A meta-skill that covers the full lifecycle of an agent skill — from design and scaffolding through worktree-based iteration, eval pipeline scoring, skill splitting, dependency registration, and scheduled improvement. Skills aren't "done" when first written; this skill keeps them improving.

## When to use

- "Create a new skill"
- "Scaffold a skill for X"
- "Iterate on this skill with worktrees"
- "Evaluate / score this skill's quality"
- "This skill is too big — split it"
- "Register the dependencies for this skill"
- "Set up periodic skill improvement"

**Do not trigger** when:
- Editing documentation that is not a SKILL.md file (use Edit directly)
- Developing non-skill code — functions, components, scripts (use a purpose-specific skill)
- Managing skills in a private or global-skills repo (use agent-config-manager instead)
- The word "skill" appears but the request is about a software module, not an agent skill

## Workflow overview

```
CREATE ──→ SCAFFOLD ──→ ITERATE (worktree loop)
                             │
                             ▼
                        EVALS (pipeline)
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

## Phase 2 — SCAFFOLD: atom-first composition

Scaffolding a skill is **picking atoms and combining them**. Every preset is a named combination of atoms. The pipeline is `atomic-builder` (EXTRACT → PICK → BUILD).

Atom catalog → `references/scaffold/index.md` · Pipeline → `references/scaffold/atomic-builder.md` · Archetype combinations → `references/archetypes.md`

### Step 1 — pick atoms

Every skill needs the **six required content atoms**:

```
frontmatter + trigger + workflow + redflag + output + requirements
```

Then add **structural atoms** based on the skill's needs:

| Atom | Add when |
|---|---|
| `references-dir` | Workflow > 40 lines, or eval tracking needed |
| `scripts-dir` | > 3 chained shell commands, or reusable script logic |
| `prompts-dir` | Scripts make 2+ LLM calls, or prompts large enough to obscure call-site code |
| `orchestrator` + N × `child-skill` | Multi-phase pipeline with independent triggers |
| `versioned-projects` | Outputs evolve over time, rollback needed |
| `sandbox-dir` | Want to validate the skill before merging |

Atom templates → `references/scaffold/atoms/<atom>.md`.

### Step 2 — name the combination (optional)

If the pick set matches a preset, use the preset name as a shortcut:

| Preset | Combination |
|---|---|
| `minimal` | six required atoms only |
| `standard` | + `references-dir` |
| `scripts` | + `references-dir + scripts-dir` |
| `split` | + `orchestrator` + N × `child-skill` |

Otherwise, build a custom combination — that's what the catalog is for.

### Step 3 — run atomic-builder

`atomic-builder` produces the draft from the pick set. Two modes:

| Mode | Source | When |
|---|---|---|
| **catalog** | `references/scaffold/atoms/*.md` | default — works without exemplars |
| **exemplar** | atoms extracted from existing high-scoring skills | repo has ≥ 2 skills scoring ≥ 35/50, or user says "based on existing skills" / "参考にして作って" |

Pipeline:

```
1. EXTRACT — catalog atoms (default), or extract from exemplars:
     atomic-builder: EXTRACT skills/<exemplar-a>/SKILL.md
2. PICK    — required + structural atoms (or preset name as shortcut)
3. BUILD   — atomic-builder: BUILD target=SKILL.md for "<new-skill-name>"
```

The BUILD output is a first draft. Fill in skill-specific details, then run `quick` eval before treating it as done.

### Optimized scaffold prompt (optional)

If `data/optimized_prompt.json` exists, BUILD can use few-shot examples selected from high-scoring past skills:

```bash
python scripts/optimize.py --generate \
    --description "What this skill does" \
    --requirements "Key constraints"
```

Uses `claude -p` via `scripts/agent.py` — no API key needed. Prompts live in `prompts/*.md` (loaded by `scripts/prompts.py`); the LLM call layer (JSON parsing, repair retry, multi-turn chains) lives in `scripts/agent.py`. If `optimized_prompt.json` doesn't exist, BUILD falls back to catalog atoms. Run `collect_evals.py` + `optimize.py` after ≥ 3 evals to generate it.

---

## Phase 3 — ITERATE: worktree loop

Full protocol → `references/iteration.md`

### Worktree naming

Always use `git worktree add` — never `git checkout -b` in the main working directory.

| Type | Branch | Worktree path |
|---|---|---|
| New skill | `feature/<skill-name>` | `../<repo>-<skill-name>` |
| Improvement iteration | `iter/<skill-name>-v<N>` | `../<repo>-iter` |
| Refactor | `refactor/<skill-name>` | `../<repo>-refactor` |

```bash
# Always from main
git checkout main && git pull origin main
git worktree add ../<repo>-<name> -b feature/<name>
cd ../<repo>-<name>  # all work happens here
```

### Parallel worktree improvement

When testing multiple improvement ideas simultaneously:

```bash
git worktree add ../skill-creator-iter-a iter/skill-creator-v2-workflow
git worktree add ../skill-creator-iter-b iter/skill-creator-v2-metrics
# Run evals in both → compare scores → cherry-pick the winner
```

### Iteration exit criteria

- All metrics ≥ **7 / 10**, **or**
- ≥ **+15%** improvement over the previous version

Neither met → run another iteration.

---

## Phase 4 — EVALS: atom-first pipeline composition

Eval pipelines use the same atomic-builder model as scaffolding. Pick atoms, combine them.

Atom catalog → `references/evals/index.md` · Pipeline mechanism → `references/evals/atomic-builder.md` · One file per atom → `references/evals/atoms/`

### Which preset to run

| Situation | Preset (atom combination) |
|---|---|
| First draft or quick check | `quick` — `static-score` |
| After any Workflow change | `executor` — `independent-evaluator + open-questions-log + assumptions-log + acceptance-gate` |
| Want quantitative signals | `measured` — `executor + runtime-telemetry` |
| After every iteration | `diff` — `static-score + regression-diff` |
| `Do not trigger` changed or before publishing | `boundary` — `adversarial + collision-scan` |
| Pre-merge final gate | `full` — all atoms, strict convergence |

If none match, build a custom combination — that's what the catalog is for.

### Eval log

Append one entry per run to `references/eval-log.jsonl` in the skill being evaluated:

```jsonl
{"pipeline":"quick","version":"v1","date":"2026-04-25","scores":{"trigger_precision":6,"workflow_coverage":7,"output_clarity":6,"red_flag_completeness":7,"dep_accuracy":7},"total":33,"top_improvement":"trigger_precision: add Do not trigger boundary against agent-config-manager","notes":"initial eval"}
```

---

## Phase 5 — AUTO-DEPS: dependency registration

Full protocol → `references/dependency.md`

### Which path to take

```bash
npx sklock --version 2>/dev/null && echo "Path A: sklock" || echo "Path B: mermaid fallback"
```

**Path A (sklock available):** create/update `skill.yml` in the new skill's directory, then run `npx sklock validate && npx sklock lock`.

**Path B (no sklock):** grep-scan SKILL.md for skill name references, propose edges, update `artie-skill-manager/references/dependency-graph.md` Mermaid block.

### Auto-detection logic (both paths)

Scan the new SKILL.md for references to other skill names in the repo:

```bash
# Step 1: get all existing skill names
ls skills/

# Step 2: check for references inside the new SKILL.md
grep -E "(bommit|pluginize|skill-creator|atomic-builder)" skills/<name>/SKILL.md
# Replace the grep pattern with the actual skill names found in step 1
```

Detected references are proposed for registration:

```
Detected new dependency edges:
  new-skill -.-> bommit    (SKILL.md line 45 references bommit)

Register? [Y/n]
→ Path A: add to skill.yml requires[] + sklock lock
→ Path B: add to dependency-graph.md Mermaid block
```

### Dependency types

- `-->` hard dependency: called at runtime (breaks without it)
- `-.->` soft reference: recommended but not required (Path B only — not expressible in skill.yml)

---

## Phase 6 — AUTO-SPLIT: skill decomposition

Full criteria → `references/scaffold/split.md`

### Split triggers

Propose a split when either is true:

1. **2+ sub-topics** each capable of having an independent trigger phrase
2. Different user personas use only different phases

Size is not a trigger. A long SKILL.md is fine if every section answers the same trigger.

### Split procedure

1. Create each phase as a new independent skill at `skills/<phase>/SKILL.md`
2. Rewrite the original SKILL.md as an orchestrator (what calls what and in which order)
3. Add orchestrator → child edges to the dependency graph
4. Re-run evals to confirm scores did not regress

---

## Phase 7 — SCHEDULE: periodic improvement

Full setup → `references/evals/index.md#periodic`

### Monthly skill review

Append the following to `db/data/cron_jobs.jsonl` (or the cron config file for your project):

```jsonl
{"name":"skill-monthly-review","schedule":"0 9 1 * *","checks":["eval total < 35 → propose executor pipeline iteration","2+ independent triggers detected → propose split","unregistered dependencies detected → propose dependency-graph update"]}
```

---

## Red flags

### Always

- Answer the three design questions before writing any SKILL.md
- Create a **worktree** (`git worktree add`) before starting work — never commit to main directly
- Run at least the `quick` pipeline before declaring a skill ready
- Use a **fresh** AI instance (no prior context about the skill) to evaluate — never self-evaluate
- Update the dependency graph before opening a PR
- Update the skill table in AGENTS.md
- Clean up worktrees after merging: `git worktree remove <path> && git branch -d <branch>`

### Never

- Never `git push` without an explicit instruction to do so
- Never `git checkout -b` in the main working directory — use `git worktree add`
- Never start writing SKILL.md before answering the three design questions
- Never declare a skill "done" without running evals
- Never skip hooks with `--no-verify`

---

## Requirements

<!-- Used by Pipeline executor's acceptance-gate element.
     At least one item must be MUST — success = all critical items passed. -->

- Never pushes to remote without an explicit instruction `MUST`
- Always uses `git worktree add`, never `git checkout -b` in main `MUST`
- Runs at least Pipeline quick before declaring a skill done `MUST`
- SKILL.md is written in English
- Skill table in AGENTS.md is updated

---

## Output

### Full flow

```
📋 DESIGN
  ✅ Trigger: "create a new skill" / "scaffold a skill for X"
  ✅ Output: SKILL.md + references/*.md
  ✅ Boundary: bommit handles commits only; skill-creator handles design → improvement

🌿 WORKTREE: ../artie-dev-skills-<name>  [branch: feature/<name>]

📦 SCAFFOLD: skills/<name>/ created
  └── SKILL.md
  └── references/ (N files)

📊 EVAL — pipeline: quick
  trigger_precision:     6/10
  workflow_coverage:     7/10
  output_clarity:        6/10
  red_flag_completeness: 7/10
  dep_accuracy:          7/10
  total: 33/50
  top_improvement: "..."
  → saved to skills/<name>/references/eval-log.jsonl

🔗 DEPS: new-skill -.-> bommit added to dependency-graph.md

🚫 PUSH: waiting — will not push until explicitly told to
```

### Phase-only invocations

**Eval only:**
```
📊 EVAL — pipeline: <name>
  [scores or executor report]
  → saved to references/eval-log.jsonl
```

**Split only:**
```
✂️ SPLIT PROPOSAL
  Current: skills/<name>/  (N lines)
  Proposed: skills/<name>-a/ + skills/<name>-b/
  Confirm split? [Y/n]
```

**Deps only:**
```
🔗 DEPS SCAN
  Detected: new-skill -.-> bommit  (line 45)
  Add to dependency-graph.md? [Y/n]
```
