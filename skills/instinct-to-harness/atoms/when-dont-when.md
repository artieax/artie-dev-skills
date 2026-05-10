---
id: when-dont-when
kind: rendering-atom
applies_to: instinct → variant
fits_polarity: any
---

# when-dont-when — use vs don't-use, two columns

Render an instinct that's about *choosing* between two tools, methods, or approaches.

## When this fits

- The instinct compares two options and tells you when to use which
- Both options are valid in their own context
- "Use X when …; use Y when …"

## Output shape

```markdown
# <title>

## Use <option A> when

- <signal 1>
- <signal 2>
- <signal 3>

## Use <option B> when

- <signal 1>
- <signal 2>
- <signal 3>

## Tie-breaker
<what to do when both seem to apply>
```

## Anti-pattern

Don't use for instincts that ban one option entirely — that's `invariant-guard`. when-dont-when implies *both* are sometimes correct.
