---
id: incident-driven
kind: extraction-method
reads: session-log
writes: instincts/<slug>.md
default_algo: llm
default_polarity_bias: never
typical_promotion_target: security-rule
---

# incident-driven — learn from danger

Extract instincts only from high-severity events (or near-misses): secrets exposure, destructive commands, production-adjacent operations, data-loss potential.

## What it looks for

- Secret / credential references: `AWS_SECRET`, `BEGIN PRIVATE KEY`, `Bearer`, `password:`
- Destructive commands: `rm -rf`, `git reset --hard`, `DROP TABLE`, `--no-verify`, force-push
- Permission escalations and bypasses
- Near-misses: command was about to run but cancelled
- Production-shaped operations on dev / unclear contexts

## Output shape

- `polarity: never` (default — these are always prohibitions)
- `enforcement_mode: hook` or `script` preferred (auto-block beats text rule)
- `promotion_targets: [rule, security-rule]`
- High-severity flag in `tags`

## Best paired with

- `--algo llm` (severity judgement requires context)

## When NOT to use

- Routine sessions with no risk events → false positives waste reviewer time
- Skip if you already have a hook layer enforcing these — incidents shouldn't reach session logs
