# v4 — input

## Trigger

Snapshot bump: the active `SKILL.md` was renamed from `skill-creator` to
`skill-builder` and grew a full lifecycle script suite
(`collect_evals.py`, `generate_review.py`, `optimize.py`,
`optimize_description.py`, `smoke_test.py`) plus an HTML eval viewer. The
v3 snapshot under `projects/skill-builder/v3/skill.md` is now stale —
`current.md` was still pointing at v3, which meant `collect_evals.py`
would feed the optimizer an old `name: skill-creator` SKILL.md as the
canonical training row.

This version pins `current.md` to v4 so the optimizer's `skill_md`
snapshot matches the on-disk `SKILL.md` again.

## Improvement targets (vs. v3 snapshot, not vs. v3 eval scores)

1. 🔴 SSOT: `projects/skill-builder/v4/skill.md` mirrors the live
   `skills/skill-builder/SKILL.md` (rename + lifecycle scripts + script
   invocation guidance landed since v3).
2. 🟠 `current.md` updated from `v3` to `v4` so the optimizer's training
   data uses the renamed, lifecycle-aware SKILL.md.
3. 🟡 No fresh eval scores yet — `eval.json` carries `total: null` so
   `collect_evals.py` keeps the snapshot available (for git-history
   fallback and future reruns) without polluting `data/evals.jsonl` with
   fabricated numbers.

## Branch / worktree

main (PR review consolidation; v4 snapshot bump committed alongside
script + doc fixes from PR review).
