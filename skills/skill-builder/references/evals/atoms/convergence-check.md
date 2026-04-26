# atom: convergence-check

| Type | Cost | Depends on |
|---|---|---|
| controller | low | at least `static-score` (standard) or `open-questions-log` + `hold-out` (strict) |

Decide whether iteration should stop. Runs after each iteration; returns a stop / continue decision.

## When to add

Always include in pipelines that drive a multi-iteration loop. Skip for one-shot evals (e.g. `quick`, `diff`).

## Modes

### Standard (fast, no executor)

```json
{
  "mode": "standard",
  "conditions": {
    "all_metrics_gte_7": true,
    "improvement_gte_15pct": false
  },
  "converged": true
}
```

Stop when **either** condition is true.

### Strict (requires `open-questions-log` + `hold-out`, 2 consecutive passes)

```json
{
  "mode": "strict",
  "conditions": {
    "open_questions_empty": true,
    "score_delta_lte_3": true,
    "holdout_drop_lt_15": true
  },
  "consecutive_passes": 2,
  "converged": true
}
```

Stop when all three conditions hold for **two iterations in a row**.

## Common mistakes

- Calling `converged: true` after a single strict pass. Strict mode requires two consecutive passes by definition.
- Using standard mode after a Workflow change. Standard never sees execution failures — pair with `executor` pipeline elements first.
