---
id: evaluator
kind: extraction-method
reads: candidate-instincts (from other modes)
writes: instincts/<slug>.md (with signals.confidence + signals.support_count populated)
default_algo: any
default_polarity_bias: any
typical_promotion_target: any
---

# evaluator — score before commit

Run the other extraction modes first to generate candidate instincts, then score each candidate by precision / coverage / annoyance and keep only the ones above the gate.

## What it does

1. Runs each enabled non-evaluator mode → produces candidate instincts (in-memory, not yet written)
2. For each candidate:
   - **precision**: how often the same observation actually re-occurs in the session pool
   - **coverage**: how many sessions / domains support the observation
   - **annoyance**: would enforcing this rule cause friction on unrelated tasks?
3. Drops candidates below `min_confidence` or `min_support_count` (from `.instinct.yml`)
4. Writes survivors to `instincts/<slug>.md` with `signals.confidence` + `signals.support_count` filled

## Output shape

Each survivor → one instinct with:
- `signals.confidence: <float 0–1>`
- `signals.support_count: <int>`
- `review_status: pending` (still needs human gate unless `auto_publish: true`)

## Best paired with

- Multi-mode runs — evaluator is most useful when ≥ 2 generative modes feed it
- `failure-cluster` + `success-pattern` + `evaluator` is the recommended starter set

## Why it matters

Without evaluator, instincts pile up at the same noise rate they're observed. Most one-off observations should NOT become rules. Evaluator is the noise filter.

## When NOT to use

- First-ever run with empty session pool → nothing to score against
- When you want every candidate kept for manual review (use `human-curated` instead)
