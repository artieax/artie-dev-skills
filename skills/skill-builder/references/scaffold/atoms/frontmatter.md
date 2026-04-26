# atom: frontmatter

YAML header at the top of every `SKILL.md`. Drives skill discovery — the `description` field is what the harness searches.

## Always include

Every SKILL.md needs this atom. Without it the file is not a skill.

## Template

```markdown
---
name: <kebab-case-name>
description: '<one sentence starting with a verb. Include 1–2 trigger phrases the user would actually say.>'
author: '@artieax'
---
```

## Field rules

| Field | Rule |
|---|---|
| `name` | `kebab-case`, no leading verb (`bommit`, `skill-builder`, not `do-bommit`) |
| `description` | One sentence, starts with a verb, ≤ 200 chars. Include trigger phrasing. |
| `author` | Org or user handle. `@artieax` for this repo. |

## Common mistakes

- `description` written as a noun phrase ("A skill for X") instead of starting with a verb
- `name` containing `_` or `CamelCase` — must be `kebab-case`
- Missing `description` → skill never matches user requests

## Optimization

The `description` field is the single biggest lever on trigger precision. After
the SKILL.md draft is otherwise stable, run `description-optimization` to tune
it against a 20-query eval set:

```bash
# From the target skill root (the shared tool lives in skill-builder)
cd skills/<name>/
python ../skill-builder/scripts/optimize_description.py --skill-root . --variants 8
python ../skill-builder/scripts/optimize_description.py --skill-root . --apply  # write the best variant back

# Or from the repo root
python skills/skill-builder/scripts/optimize_description.py --skill-root skills/<name> --apply
```

See [`../../evals/atoms/description-optimization.md`](../../evals/atoms/description-optimization.md).
