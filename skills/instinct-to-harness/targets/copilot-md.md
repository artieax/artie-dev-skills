---
id: copilot-md
kind: harness-target
provider: copilot
reads: instinct + atom (rendering recipe)
writes: instincts/<slug>/variants/copilot-md.md
deploys_to: .github/copilot-instructions.md (insert)
default_method: append
---

# copilot-md — GitHub Copilot instructions

Generate a block for `.github/copilot-instructions.md`. Copilot is completion-focused, so render lead with code patterns.

## Variant template

```markdown
### <title>

<one line of context>

```<lang>
// NG
<bad pattern>
```

```<lang>
// OK
<good pattern>
```
```

## Constraints

- ≤ 20 lines total per rule
- Code-first; explanation second
- Keep prose minimal (Copilot weighs code more)

## DEPLOY behaviour

- Method: `append` to `.github/copilot-instructions.md`
- Idempotent by section header

## Best paired with

- Rendering atom: `anti-pattern-gallery` (NG/OK is exactly Copilot's wheelhouse)
- Instincts about *coding style* — less useful for behavioural / process instincts
