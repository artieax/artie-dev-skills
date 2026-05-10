---
id: success-pattern
kind: extraction-method
reads: session-log
writes: instincts/<slug>.md
default_algo: semantic
default_polarity_bias: good
typical_promotion_target: skill
---

# success-pattern — learn from success

Find sessions or sub-flows that ended cleanly with zero correction and extract the *order* the user / agent followed.

## What it looks for

- Sequences with no retries, no `revert`, no error lines
- User confirmation phrases: "perfect", "exactly", "ship it", "done"
- Smooth tool-call chains where each step passes on the first try
- PR / commit landing without rework

## Output shape

Each pattern → one instinct with:
- `polarity: good`
- Body documents the *ordered steps* that worked
- `promotion_targets: [skill]` — these become how-to skills, not constraints
- `target_skill` — **must be resolved during EXTRACT**; see resolution rules below

### `target_skill` resolution (during EXTRACT)

Order:

1. Session metadata names the skill explicitly (e.g. running inside `.agent/skill/<name>/`)
2. `path_scope` of the observation matches a known `<repo>/.agent/skill/*/` path
3. Heuristic match against tool calls / commands the success ran (e.g. `npm run skill:lock` → `sklock`)
4. None of the above resolves → drop `skill` from `promotion_targets`, fall back to `[doc]`, and emit a deferral note in `reviews/<slug>.md`

The atom MUST NOT emit a `[skill]` instinct with `target_skill: null` — that produces a build that can never be deployed (`skill-constraint` DEPLOY needs `<target-skill>`). Step 4 is the explicit escape hatch.

## Best paired with

- `--algo semantic` to cluster the steps by topic
- `--algo llm` to capture the implicit "why this order"

## When NOT to use

- Failure-heavy sessions → noise (every brief success looks like a pattern)
- One-shot trivial tasks → no real "pattern" to extract
