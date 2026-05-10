---
id: claude-global
kind: harness-target
provider: claude
reads: instinct + atom (rendering recipe)
writes: instincts/<slug>/variants/claude-global.txt
deploys_to: CLAUDE.md (append one trigger line)
default_method: append
---

# claude-global — single trigger line in CLAUDE.md

Generate ONE line to append to CLAUDE.md that points at the path-scoped rule for details.

## Variant template

```
<domain> で <pattern> → `.claude/rules/<slug>.md` 参照
```

or in English:

```
On <domain> doing <pattern> → see `.claude/rules/<slug>.md`
```

## Constraints

- **One line only** (CLAUDE.md must stay scannable)
- No body text — defer to the path-scoped rule for details
- Use this ONLY when the rule needs global awareness (loaded for every Claude Code session)

## DEPLOY behaviour

- Method: `append` one line under a stable section heading
- Path: `CLAUDE.md` at project root
- Idempotent by slug match

## Best paired with

- Used together with `claude-path` — claude-global is the trigger, claude-path is the body
- Rendering atom: not really applicable; this is just a redirect pointer

## Anti-pattern

Don't deploy to claude-global without also deploying to claude-path — the trigger points at a file that must exist.
