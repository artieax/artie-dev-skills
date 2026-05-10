---
id: safe
kind: extraction-preset
atoms: [failure-cluster, incident-driven, human-curated]
emit_targets: [claude-path]
---

# safe — high-trust environments

Conservative: only failures and incidents, never auto-published, every candidate goes through human review.

## Atoms

- [`failure-cluster`](../atoms/failure-cluster.md) (`algo: keyword`)
- [`incident-driven`](../atoms/incident-driven.md) (`algo: llm`) — security/destructive events
- [`human-curated`](../atoms/human-curated.md) — wraps the above; pauses for accept/reject

## Emit

- `claude-path` only — no broadcast to other AIs until reviewed
- `auto_publish: false`, `require_review: true`

## Use when

- Initial rollout in a regulated team
- Codebase touches secrets, infra, finance, health
- Cultural calibration phase — what counts as a rule must be agreed before it becomes one
