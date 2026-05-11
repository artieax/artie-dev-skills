---
id: invariant-guard
kind: rendering-atom
applies_to: instinct → variant
fits_polarity: never, bad
---

# invariant-guard — hard constraint block

Render an instinct as a non-negotiable rule with explicit DO / DON'T sections.

## When this fits

- `polarity: never` or `bad` with a single clear prohibition
- `enforcement_mode: rule` or `hook`
- The corrective is a one-liner, not a flowchart

## Output shape

```markdown
# <title>

## Invariant
<one-sentence rule>

## Why
<one-paragraph reason>

## DO
- <safe action 1>
- <safe action 2>

## DON'T
- <prohibited action> — <why>
```

## Anti-pattern

Don't use this for instincts where the right action depends on context — those need `decision-table` or `when-dont-when` instead.
