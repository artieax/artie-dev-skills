# atom: regression-diff

| Type | Cost | Depends on |
|---|---|---|
| comparator | low | `static-score` on both versions |

Compare `static-score` results between v(N) and v(N-1). Flags per-metric regressions ≥ 2pt as `safe_to_merge: false`.

## When to add

After every iteration that produces a new version. The cheapest possible regression guard.

## Inputs

- two SKILL.md versions, each with a `static-score` result

## Output

```json
{
  "version_from": "v1",
  "version_to": "v2",
  "delta": {
    "trigger_precision": +2,
    "workflow_coverage": 0,
    "output_clarity": -3,
    "red_flag_completeness": +1,
    "dep_accuracy": 0
  },
  "total_delta": 0,
  "regressions": ["output_clarity: -3"],
  "safe_to_merge": false
}
```

## Common mistakes

- Looking only at `total_delta`. A 0-point change can hide a +5 / -5 swap that hurts where it matters most.
- Skipping when `total_delta > 0` — a metric that regressed by ≥ 2pt is still a regression even if the total improved.
