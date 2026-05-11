---
id: cursor-mdc
kind: harness-target
provider: cursor
reads: instinct + atom (rendering recipe)
writes: instincts/<slug>/variants/cursor-mdc.mdc
deploys_to: .cursor/rules/<slug>.mdc
default_method: symlink
---

# cursor-mdc — Cursor MDC rule

Generate a `.cursor/rules/<slug>.mdc` file with MDC frontmatter.

## Variant template

```mdc
---
globs: [<path_scope or "**/*">]
---

<rendered body — short, ≤ 50 lines>
```

## Constraints

- Keep under 50 lines (Cursor reads at rule-load time)
- Avoid tables > 5 rows
- Code examples allowed and useful

## DEPLOY behaviour

- Method: `symlink` (default)
- Path: `.cursor/rules/<slug>.mdc`

## Best paired with

- Rendering atoms: `invariant-guard`, `kata`, `anti-pattern-gallery`
- Concise rules — long story-arc renders should be trimmed before emitting cursor-mdc
