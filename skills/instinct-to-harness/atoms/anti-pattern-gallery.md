---
id: anti-pattern-gallery
kind: rendering-atom
applies_to: instinct → variant
fits_polarity: never, bad
---

# anti-pattern-gallery — NG / OK side by side

Render an instinct as a before/after code comparison.

## When this fits

- The instinct is best understood by *seeing* the wrong way next to the right way
- The corrective contains a code block
- The lesson is structural (style, idiom) rather than behavioural

## Output shape

```markdown
# <title>

## NG — what not to write

```<lang>
<bad example>
```

## OK — what to write instead

```<lang>
<good example>
```

## Difference
<one paragraph on what changed and why it matters>
```

## Anti-pattern

Don't use for non-code instincts — gallery format requires both sides to be code.
