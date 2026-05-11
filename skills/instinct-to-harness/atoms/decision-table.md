---
id: decision-table
kind: rendering-atom
applies_to: instinct → variant
fits_polarity: any
---

# decision-table — situation × action grid

Render an instinct as a markdown table mapping situations to the correct action.

## When this fits

- The corrective has 3+ branches
- Same domain, multiple contexts, each with a different right answer
- "If X, do Y; if Z, do W" pattern

## Output shape

```markdown
# <title>

## Decision

| Situation | Correct action | Reason |
|---|---|---|
| <case A> | <action A> | <why A> |
| <case B> | <action B> | <why B> |
| <case C> | <action C> | <why C> |

## Default
When the situation doesn't match any row above: <fallback action>.
```

## Anti-pattern

Don't use this for binary "do/don't" rules — that's `invariant-guard` territory.
