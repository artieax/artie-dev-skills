# evals — atom-first index

Eval pipelines are **picking atoms and combining them** — same model as scaffold. Each atom measures one thing; presets are named atom combinations; custom pipelines are free combinations.

The vocabulary intentionally tracks classical software-engineering practice — RFC 2119 priorities, ATDD acceptance gates, IV&V independence (IEEE 1012), requirements engineering open-questions / assumptions logs (IEEE 29148, PMBOK), runtime telemetry. See [`../lineage.md`](../lineage.md).

Start here:

1. **Pick atoms** from the catalog below
2. **Combine them** — match a preset or assemble freely
3. **Generate the pipeline** via [`atomic-builder.md`](atomic-builder.md)
4. **Run it** and append a row to `references/eval-log.jsonl` (the human-readable, committed ledger). The optimizer cache `data/evals.jsonl` is generated separately by `scripts/collect_evals.py` — see [Two eval files: ledger vs cache](#two-eval-files-ledger-vs-cache).

→ Pipeline mechanics: [`atomic-builder.md`](atomic-builder.md)

→ Situation → preset (extended table): [`preset-selection.md`](preset-selection.md) · HTML review UI: [`review-viewer.md`](review-viewer.md)

---

## Atom catalog

### Foundational atoms

| Atom | Type | Cost | What it produces |
|---|---|---|---|
| [`static-score`](atoms/static-score.md) | evaluator | low | 5-metric quality score (0–50pt) |
| [`independent-evaluator`](atoms/independent-evaluator.md) | runner | medium | skill execution output from an independent agent (IV&V) |

### Reporters (require `independent-evaluator`)

| Atom | Type | Cost | What it produces |
|---|---|---|---|
| [`open-questions-log`](atoms/open-questions-log.md) | reporter | low | list of instructions the evaluator could not determine |
| [`assumptions-log`](atoms/assumptions-log.md) | reporter | low | list of decisions the evaluator made without instruction |

### Validators / observers (require `independent-evaluator`)

| Atom | Type | Cost | What it produces |
|---|---|---|---|
| [`acceptance-gate`](atoms/acceptance-gate.md) | validator | low | pass/fail against `MUST` requirements (RFC 2119) — **skill-level** |
| [`assertion-grader`](atoms/assertion-grader.md) | validator | low | per-fixture assertion pass/fail with literal evidence — **fixture-level** |
| [`runtime-telemetry`](atoms/runtime-telemetry.md) | observer | low | tool_uses / duration_ms / total_tokens / retry_count |
| [`hold-out`](atoms/hold-out.md) | validator | medium | score on fixtures never used during tuning |

### Comparators / boundary tests

| Atom | Type | Cost | What it produces |
|---|---|---|---|
| [`regression-diff`](atoms/regression-diff.md) | comparator | low | per-metric delta between v(N) and v(N-1) |
| [`baseline-comparison`](atoms/baseline-comparison.md) | comparator | medium | with-skill vs without-skill: pass_rate / duration / tokens delta |
| [`adversarial`](atoms/adversarial.md) | tester | medium | false-positive / false-negative on out-of-scope inputs |
| [`collision-scan`](atoms/collision-scan.md) | scanner | low | trigger phrase overlap with adjacent skills |

### Controllers

| Atom | Type | Cost | What it produces |
|---|---|---|---|
| [`convergence-check`](atoms/convergence-check.md) | controller | low | stop condition: are criteria met for 2 consecutive runs? |

### Pre-runtime optimizers

Run these *before* the runtime pipeline. They modify the SKILL.md (or sibling artifacts) directly to lift baseline quality before any pipeline atom runs.

| Atom | Type | Cost | What it produces |
|---|---|---|---|
| [`description-optimization`](atoms/description-optimization.md) | optimizer | medium | best `description` field by accuracy on a 20-query trigger eval set |

### Discovery / drift

Open-loop scanners that pull signal in from outside the repo and propose additions. Out-of-band relative to the runtime pipeline; output is advisory (proposals only, never auto-applied). Trigger and source list are supplied by the caller's harness — the atom stays portable.

| Atom | Type | Cost | What it produces |
|---|---|---|---|
| [`practice-drift-scan`](atoms/practice-drift-scan.md) | proposer | high | proposals (new atoms / SKILL.md edits / scripts) drawn from caller-supplied external sources |

---

## Presets — named atom combinations

| Preset | Atoms | When to use |
|---|---|---|
| `quick` | `static-score` | First draft, any quick check |
| `executor` | `independent-evaluator` + `open-questions-log` + `assumptions-log` + `acceptance-gate` + `assertion-grader` | After any Workflow change |
| `measured` | `executor` + `runtime-telemetry` + `baseline-comparison` | Quantitative execution signals + with-skill vs baseline value proof |
| `diff` | `static-score` + `regression-diff` | After every iteration (cheap regression guard) |
| `boundary` | `adversarial` + `collision-scan` | When `Do not trigger` changes or before publishing |
| `full` | `static-score` + `independent-evaluator` + `open-questions-log` + `assumptions-log` + `acceptance-gate` + `assertion-grader` + `runtime-telemetry` + `hold-out` + `regression-diff` + `baseline-comparison` + `convergence-check` (strict) | Pre-merge final gate |
| `pre-runtime` | `description-optimization` | One-shot. Before publishing, after `## When to use` changes |

If none match, build a custom combination — that's what the catalog is for.

### Preset definitions (YAML)

```yaml
pipelines:
  quick:
    atoms: [static-score]
    convergence: standard

  executor:
    atoms: [independent-evaluator, open-questions-log, assumptions-log, acceptance-gate, assertion-grader]
    convergence: standard

  measured:
    extends: executor
    atoms: [+runtime-telemetry, +baseline-comparison]

  diff:
    atoms: [static-score, regression-diff]
    convergence: standard

  boundary:
    atoms: [adversarial, collision-scan]

  full:
    atoms:
      - static-score
      - independent-evaluator
      - open-questions-log
      - assumptions-log
      - acceptance-gate
      - assertion-grader
      - runtime-telemetry
      - hold-out
      - regression-diff
      - baseline-comparison
      - convergence-check
    convergence: strict

  pre-runtime:
    atoms: [description-optimization]
    note: not a runtime pipeline — modifies SKILL.md frontmatter, run separately
```

---

## Selection guide

```
New skill, first draft            → quick
After changing Workflow           → executor (+ diff if prev version exists)
Want quantitative signals         → measured
After every iteration             → diff
Do not trigger / publish          → boundary
Pre-merge final gate              → full
```

---

## Two eval files: ledger vs cache {#two-eval-files-ledger-vs-cache}

Eval signal lives in **two distinct files with different ownership**. They are not interchangeable; the previous version of these docs blurred them together and the result was a known SSOT drift.

| File | Role | Lifecycle | Git status |
|---|---|---|---|
| `references/eval-log.jsonl` | **Committed ledger** — one human-readable summary row per pipeline run, written by hand or by the pipeline itself when it appends a run summary | Append-only, kept forever in git history (rotation lives in [`../schedule.md#evals-rotation`](../schedule.md#evals-rotation) but only kicks in once it grows large) | **Committed** |
| `data/evals.jsonl` | **Optimizer cache** — generated by `scripts/collect_evals.py` from `projects/<name>/v<N>/eval.json` snapshots, paired with the SKILL.md text that was scored. Read by `optimize.py` / `tune_thresholds.py` as training input | Regenerable from `projects/` + git history; can be deleted and rebuilt at any time | **gitignored** (see `.gitignore`) |

Decision rule:

- **Want a row a teammate will read in a PR or 6 months from now?** Append to `references/eval-log.jsonl`.
- **Want training data for `optimize.py` / `tune_thresholds.py`?** Run `python scripts/collect_evals.py` — it rebuilds `data/evals.jsonl` from `projects/*/v*/eval.json` and git history.

`generate_review.py` reads `data/evals.jsonl` because the HTML viewer's whole point is rich per-version data (full SKILL.md snapshot + open questions + sandbox links). For a quick `git log`-friendly recap, read `references/eval-log.jsonl` directly.

### `references/eval-log.jsonl` format (committed ledger)

One entry per pipeline run, in `references/eval-log.jsonl` of the skill being evaluated.

```jsonl
{"pipeline":"quick","version":"v1","date":"2026-04-25","scores":{"trigger_precision":6,"workflow_coverage":7,"output_clarity":6,"red_flag_completeness":7,"dep_accuracy":7},"total":33,"top_improvement":"trigger_precision: add Do not trigger boundary","notes":"initial eval"}
{"pipeline":"diff","version":"v2","date":"2026-04-26","delta":{"trigger_precision":2,"output_clarity":1},"total_delta":3,"regressions":[],"safe_to_merge":true}
{"pipeline":"executor","version":"v2","date":"2026-04-26","open_questions":[],"all_must_passed":true,"convergence":"converged"}
```

### `data/evals.jsonl` format (optimizer cache)

Same record shape plus `skill_md` (the snapshot that was scored) and `change_notes` (the `v<N>/input.md` log). See `scripts/collect_evals.py` for the exact schema.

---

## Periodic improvement {#periodic}

```jsonl
{
  "name": "skill-monthly-eval",
  "schedule": "0 9 1 * *",
  "pipeline": "quick",
  "checks": [
    "total < 35 → propose executor pipeline iteration",
    "2+ independent triggers detected → propose split",
    "unregistered deps → propose dependency-graph update"
  ]
}
```

---

## Optimization scripts

The `scripts/` directory contains tools that learn from accumulated eval data. Prompts they use live in `prompts/*.md`; the LLM call layer lives in `scripts/agent.py`.

### collect_evals.py — accumulate eval records

```bash
# Form A — from the target skill's root
cd skills/<name>
python ../skill-builder/scripts/collect_evals.py        # scans projects/*/v*/eval.json → data/evals.jsonl

# Form B — from the repo root (canonical, no cwd ambiguity)
python skills/skill-builder/scripts/collect_evals.py --skill-root skills/<name>
```

Pairs each completed `eval.json` (non-null total) with two snapshots: the
`skill_md` that was actually scored (resolved from
`projects/<name>/v<N>/skill.md` first, then the git commit that introduced
the eval), and the `change_notes` (`v<N>/input.md` change log) that
describe what triggered the version. Idempotent. Run after every
iteration that produces a new `eval.json`. The script reads
`--skill-root` (default `.`); see
[`SKILL.md → Where to run the scripts`](../../SKILL.md#where-to-run-the-scripts).

### optimize.py — BootstrapFewShot prompt optimizer

```bash
# Form A — from the target skill's root
cd skills/<name>
python ../skill-builder/scripts/optimize.py                            # optimize scaffold prompt
python ../skill-builder/scripts/optimize.py --max-demos 3 --trials 10  # more search
python ../skill-builder/scripts/optimize.py --estimate-only            # call/dollar bound, no claude calls
python ../skill-builder/scripts/optimize.py --seed 42                  # reproducible run

python ../skill-builder/scripts/optimize.py --generate \
    --description "A skill that reviews PRs" \
    --requirements "Uses gh CLI, outputs structured comments"

# Form B — from the repo root
python skills/skill-builder/scripts/optimize.py --skill-root skills/<name> [--seed 42 | --estimate-only | ...]
```

Uses `claude -p` via `scripts/agent.py` — no API key needed. Prompts loaded from `prompts/scaffold-system.md`, `prompts/scaffold-user.md`, `prompts/score.md`. Per-call timeout (`AgentConfig.timeout_s`, default 180s) and a process-wide cap (`--max-calls` or `SKILL_BUILDER_MAX_CALLS`) prevent a single hang from stalling cron / CI.

**When to use:** after accumulating ≥ 8 eval records. Below that, the demo selection has high variance and easily over-fits to one or two atypical SKILL.md instances — `optimize.py` prints a warning and runs anyway, but treat the result as exploratory until enough data accumulates.

### tune_thresholds.py — Optuna convergence threshold tuner

```bash
# Form A — from the target skill's root
cd skills/<name>
uv run ../skill-builder/scripts/tune_thresholds.py               # 100 Optuna trials
uv run ../skill-builder/scripts/tune_thresholds.py --trials 300  # more trials = better results
uv run ../skill-builder/scripts/tune_thresholds.py --show-plots  # visualize param importances

# Form B — from the repo root
uv run skills/skill-builder/scripts/tune_thresholds.py --skill-root skills/<name>
```

Groups `data/evals.jsonl` by skill into version sequences, then maximises quality × efficiency over `(convergence_threshold, improvement_threshold, metric_weights)`. Outputs `data/tuned_thresholds.json`.

Requires ≥ 2 completed versions of the same skill.

### Recommended workflow

```
eval run → collect_evals.py → (repeat until ≥ 8 records)
                                     ↓
                            optimize.py  ←→  tune_thresholds.py
                                     ↓
                      data/optimized_prompt.json
                      data/tuned_thresholds.json
                                     ↓
                        update iteration.md thresholds
                        use optimized prompt in Phase 2
```
