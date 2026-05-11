---
id: agents-md
kind: harness-target
provider: codex
reads: instinct + atom (rendering recipe)
writes: instincts/<slug>/variants/agents-md.md
deploys_to: AGENTS.md (insert into a section)
default_method: append
---

# agents-md — Codex / OpenAI AGENTS.md

Generate a markdown block to insert into `AGENTS.md` under a `## Rules` or `## Constraints` section.

## Variant template

```markdown
- **Do not** <action> — <one-line reason>
```

or for `polarity: good`:

```markdown
- **Prefer** <action> — <one-line reason>
```

## Constraints

- ≤ 30 words per bullet
- One bullet per instinct
- No code blocks (token budget)

## DEPLOY behaviour

- Method: `append` — section markers identify the insert point
- Path: `AGENTS.md` at project root
- Re-run is idempotent: existing block is replaced if slug matches

## Best paired with

- Rendering atom: `invariant-guard` (renders to a single bullet cleanly)
- Instincts where the rule itself is short — long ones lose information here
