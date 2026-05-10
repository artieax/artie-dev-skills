---
id: claude-path
kind: harness-target
provider: claude
reads: instinct + atom (rendering recipe)
writes: instincts/<slug>/variants/claude-path.md
deploys_to: .claude/rules/<slug>.md
default_method: symlink
---

# claude-path — Claude Code path-scoped rule

Generate a `.claude/rules/<slug>.md` file. Path-scoped via YAML frontmatter `paths:`.

## Variant template

```markdown
---
paths: [<path_scope or omitted for global>]
---

<rendered body using the chosen rendering atom>

## 根拠 (session <session_id> / <today>)
<one-line origin reference>
```

## DEPLOY behaviour

- Method: `symlink` (default) — edits to source flow through immediately
- Path: `.claude/rules/<slug>.md`
- `--force` overwrites; otherwise refuses if file exists

## Best paired with

- Rendering atoms: `invariant-guard`, `decision-table`, `symptom-cause-fix`, `story-arc`
- Long-form, code-heavy instincts (claude-path supports full markdown)
