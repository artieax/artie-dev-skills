---
id: gemini-md
kind: harness-target
provider: gemini
reads: instinct + atom (rendering recipe)
writes: instincts/<slug>/variants/gemini-md.md
deploys_to: GEMINI.md (insert into a section)
default_method: append
---

# gemini-md — Gemini CLI GEMINI.md

Generate a markdown block to insert into `GEMINI.md`.

## Variant template

Same shape as `agents-md` but Gemini tends to read short bullets better:

```markdown
- <directive form>: <one-line reason>
```

Code blocks are OK if they illustrate the corrective.

## DEPLOY behaviour

- Method: `append`
- Path: `GEMINI.md` at project root
- Idempotent: replaces existing block matching the slug

## Best paired with

- Rendering atoms: `invariant-guard`, `kata`
- Short, action-oriented instincts
