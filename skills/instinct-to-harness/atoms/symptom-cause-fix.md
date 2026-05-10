---
id: symptom-cause-fix
kind: rendering-atom
applies_to: instinct → variant
fits_polarity: never, bad
---

# symptom-cause-fix — diagnostic flow

Render an instinct as a runbook: what the user will see, what's actually wrong, how to fix.

## When this fits

- Error / failure pattern with a known root cause
- `enforcement_mode: script` (fix can be automated)
- Source mode is `failure-cluster` and the error has a recognisable signature

## Output shape

```markdown
# <title>

## Symptom
<exact error message or observable behaviour>

## Cause
<root cause — one paragraph>

## Fix
```bash
<commands or steps>
```

## Verification
<how to confirm the fix worked>
```

## Anti-pattern

Don't use this for general guidance — symptom-cause-fix only applies when there's a real error to recognise.
