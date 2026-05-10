---
id: escalation-ladder
kind: rendering-atom
applies_to: instinct → variant
fits_polarity: any
---

# escalation-ladder — try X, then Y, then Z

Render an instinct as an ordered fallback chain.

## When this fits

- Multiple valid approaches, ordered by preference
- "Try the cheap fix first; if that fails, try the deeper fix; if that fails, escalate"
- Source mode often `success-pattern` (a sequence that worked)

## Output shape

```markdown
# <title>

## Ladder

1. **<first attempt>** — <when to use, when to give up>
2. **<second attempt>** — <when to use, when to give up>
3. **<final fallback>** — <last resort>

## Escalate to
<who or what to ping when the ladder is exhausted>
```

## Anti-pattern

Don't use for unordered alternatives — that's `decision-table`. Ladder implies "try in order".
