---
id: standard
kind: extraction-preset
atoms: [failure-cluster, success-pattern, evaluator]
emit_targets: [claude-path, skill-constraint]
---

# standard — recommended starter

Three atoms covering the three behaviours that matter most: learn from failure, learn from success, filter noise.

## Atoms

- [`failure-cluster`](../atoms/failure-cluster.md) (`algo: keyword`, weight: 1.0) — produces `rule`-targeted instincts
- [`success-pattern`](../atoms/success-pattern.md) (`algo: semantic`, weight: 0.7) — produces `skill`-targeted instincts
- [`evaluator`](../atoms/evaluator.md) (weight: 1.2) — scores both above; only kept candidates write files

## Emit

- `claude-path` for `rule` instincts
- `skill-constraint` for `skill` instincts

## Why these three

Failure + success covers the productive surface. Evaluator stops the pool from filling with one-off observations. Anything beyond this is optional.
