# v1 — changes

Initial version. No previous version to diff against.

## Files created

- `SKILL.md` — 7-phase lifecycle (CREATE / SCAFFOLD / ITERATE / EVALS / AUTO-DEPS / AUTO-SPLIT / SCHEDULE)
- `references/scaffold.md` — Pattern A–D table + SKILL.md template + naming conventions + archetype overview
- `references/evals.md` — 5-metric scoring framework (50pt) + eval-log.jsonl format + periodic schedule
- `references/iteration.md` — worktree loop protocol (single + parallel) + exit criteria + cleanup
- `references/dependency.md` — auto-detection + dependency-graph.md update procedure
- `references/archetypes.md` — Archetype E/F/G layouts + self-referential skill improvement pattern
- `references/red-flags.md` — Always/Never pattern catalog (6 categories)
- `projects/skill-creator/` — this project tracking directory

## Key decisions

- Worktree-first: `git worktree add` as the standard; `git checkout -b` prohibited in main dir
- Flat skills/: split phases become independent top-level skills, never nested directories
- Archetype E applied to self: improvement iterations tracked as versioned project runs
