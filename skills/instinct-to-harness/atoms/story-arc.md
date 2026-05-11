---
id: story-arc
kind: rendering-atom
applies_to: instinct → variant
fits_polarity: any
---

# story-arc — narrative WHY

Render an instinct as a short narrative: situation → what we tried → what we learned → the rule.

## When this fits

- The lesson only makes sense with the backstory
- Source mode `incident-driven` — the why must be remembered or the rule decays
- Cultural / team-specific rules where someone new will ask "why?"

## Output shape

```markdown
# <title>

## What happened
<concrete situation — date, what was being done>

## What we tried
<approach taken; why it seemed reasonable>

## What broke
<the consequence>

## What we learned
<the actual instinct — one sentence>

## The rule
<directive form of the instinct>
```

## Anti-pattern

Don't use for stable, well-understood patterns — `kata` or `invariant-guard` is shorter and works.
