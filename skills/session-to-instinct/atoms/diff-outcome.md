---
id: diff-outcome
kind: extraction-method
reads: session-log + diff-stats
writes: instincts/<slug>.md
default_algo: diff
default_polarity_bias: any
typical_promotion_target: doc
---

# diff-outcome — learn from edit shapes

Read only the *statistics* of edits (file counts, revert rate, rewrite count) to learn what kinds of changes lead to clean outcomes vs. churn.

## What it looks for

- Number of files touched per change
- Number of directories spanned
- Revert / re-edit rate per slug
- Test re-run frequency
- Time between first edit and final commit

## Output shape

Each cluster → one instinct with:
- `polarity: any` (depends on outcome, not intent)
- Body explains the *shape* of edit that worked or didn't
- `promotion_targets: [doc]` — these become guidelines, not hard rules

## Best paired with

- `--algo diff` (mandatory — this method needs diff parsing)

## Privacy note

This method is **content-blind by design**: it looks at sizes and patterns of changes, never the source code itself. Useful when collecting from sessions where code privacy matters.

## When NOT to use

- Sessions with no diffs (pure planning / discussion) → no signal
- One-off small changes → too little data for a pattern
