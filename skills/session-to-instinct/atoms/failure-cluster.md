---
id: failure-cluster
kind: extraction-method
reads: session-log
writes: instincts/<slug>.md
default_algo: keyword
default_polarity_bias: never
typical_promotion_target: rule
---

# failure-cluster — learn from failure

Cluster failure events in the session and turn each cluster into a "don't repeat this" instinct.

## What it looks for

- Error lines: stack traces, `error:`, `failed`, `exit 1`, non-zero exit codes
- Backtracking: `git reset`, undo commands, repeated edits to the same file
- Explicit corrections from the user: "no", "stop", "don't", "instead", "actually"
- Repeated tries on the same operation with parameter changes

## Output shape

Each cluster → one instinct with:
- `polarity: never` or `bad`
- `corrective:` filled (what to do next time)
- `promotion_targets: [rule]`

## Best paired with

- `--algo keyword` for fast surface scan over large session batches
- `--algo llm` when failures are implicit (user gave up, switched approach)

## When NOT to use

- Smooth sessions with no failures → produces nothing useful
- Sessions where the user is exploring (not failing) → spurious "never" atoms
