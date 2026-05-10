---
id: minimal
kind: extraction-preset
atoms: [failure-cluster]
emit_targets: [claude-path]
---

# minimal — start tiny

Just `failure-cluster` with the `keyword` algo. One mode, one fast scan. Useful as a smoke test before committing to a larger config.

## Atoms

- [`failure-cluster`](../atoms/failure-cluster.md) (`algo: keyword`, weight: 1.0)

## Emit

- `claude-path` only
