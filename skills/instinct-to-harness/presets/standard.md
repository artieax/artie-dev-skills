---
id: standard
kind: emit-preset
targets: [claude-path, skill-constraint]
default_atom_per_target:
  claude-path: auto         # use instinct.best_preset
  skill-constraint: auto    # polarity-aware: never/bad → invariant-guard, good → kata
---

# standard — claude-path + skill-constraint

Mirror of `session-to-instinct/presets/standard.md` on the emit side.

## Targets

- [`claude-path`](../targets/claude-path.md) — primary harness (path-scoped rule)
- [`skill-constraint`](../targets/skill-constraint.md) — append into the affected skill's section (Do Not for `never`/`bad`, Prefer/Recipes for `good`)

## Rendering

Both targets default to `auto`. `auto` for `skill-constraint` resolves polarity-aware:

| `polarity` | rendering atom |
|---|---|
| `never` / `bad` | `invariant-guard` |
| `good` | `kata` (or `decision-table` if the body has 3+ branches) |

This avoids rendering a positive `success-pattern` instinct as a negative constraint.
