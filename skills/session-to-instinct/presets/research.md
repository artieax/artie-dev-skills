---
id: research
kind: extraction-preset
atoms: [failure-cluster, success-pattern, head-start, diff-outcome, incident-driven, evaluator, dream-assisted]
emit_targets: [claude-path, agents-md, gemini-md]
---

# research — every angle, no auto-publish

Throws every analytical lens at the session pool. Useful when *exploring* what's worth turning into instincts, before committing to a slimmer set.

## Atoms

- [`failure-cluster`](../atoms/failure-cluster.md)
- [`success-pattern`](../atoms/success-pattern.md)
- [`head-start`](../atoms/head-start.md) — generic rules that would have shortened the session
- [`diff-outcome`](../atoms/diff-outcome.md)
- [`incident-driven`](../atoms/incident-driven.md)
- [`evaluator`](../atoms/evaluator.md) — scores all of the above
- [`dream-assisted`](../atoms/dream-assisted.md) — runs after the others to consolidate

`human-curated` is intentionally NOT enabled — research mode runs unattended.

## Emit

- `claude-path` for primary use
- `agents-md` + `gemini-md` for cross-reading

## Use when

- Auditing a long backlog of session logs
- Designing a new team's `.instinct.yml` — see what each mode produces
- Comparing extraction methods on the same input

## Caution

Generates volume. Always run `evaluator` (already included) and review pool before promoting any instinct.
