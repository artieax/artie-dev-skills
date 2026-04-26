# atom: hold-out

| Type | Cost | Depends on |
|---|---|---|
| validator | medium | `independent-evaluator` (run on hold-out fixtures) |

Run `independent-evaluator` + `open-questions-log` + `acceptance-gate` against fixtures that were **never used during tuning**. Detects overfitting to training fixtures.

## When to add

Once before publishing or merging. Required by `convergence-check` strict mode.

## Setup

Fix the split before tuning starts and never change it:

```
fixtures/
  train/        ← used during iteration
  hold-out/     ← only touched for final validation
```

## Output

```json
{
  "holdout_total": 38,
  "train_total": 44,
  "drop": 6,
  "overfit_detected": false
}
```

`overfit_detected: true` when `drop >= 15`.

## Common mistakes

- Adding to hold-out fixtures during iteration → the set stops being held-out. If you must add fixtures, they go in `train/`.
- Running hold-out only once at the very end. Run it any time before declaring a major version converged.
