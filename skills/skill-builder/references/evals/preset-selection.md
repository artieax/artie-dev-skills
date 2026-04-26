# Preset selection — when to run which pipeline

Presets are named atom combinations. Full catalog and YAML definitions → [`index.md`](index.md).

If none of the rows below match, assemble a custom pipeline from [`atoms/`](atoms/).

---

## Situation → preset

| Situation | Preset (atom combination) |
|---|---|
| First draft or quick check | `quick` — `static-score` |
| After any Workflow change | `executor` — `independent-evaluator` + `open-questions-log` + `assumptions-log` + `acceptance-gate` + `assertion-grader` |
| Want quantitative signals + value proof | `measured` — `executor` + `runtime-telemetry` + `baseline-comparison` |
| After every iteration | `diff` — `static-score` + `regression-diff` |
| `Do not trigger` changed or before publishing | `boundary` — `adversarial` + `collision-scan` |
| Pre-merge final gate | `full` — all atoms, strict convergence |
| Tune `description` for trigger precision (one-shot) | `pre-runtime` — `description-optimization` (run separately) |

---

## Two-tier validation in `executor`

- **`acceptance-gate`** — validates skill-level RFC 2119 `MUST` items in `## Requirements`.
- **`assertion-grader`** — validates fixture-level output properties.

Run both inside `executor` for skill-level plus fixture-level coverage.

---

## Baseline and description tuning

- **`baseline-comparison`** — shows the skill beats the no-skill baseline (mean ± stddev across ≥ 3 runs per side).
- **`pre-runtime`** — one-shot: tunes the `SKILL.md` frontmatter `description` against a 20-query eval set and writes the winner back. Run before `boundary` and before publishing. Implementation → `scripts/optimize_description.py`.
