---
name: skill-builder
description: 'Build or improve agent SKILL.md files by scaffolding, iterating with worktrees, running evals, registering dependencies, and proposing splits; not for general code modules, ordinary docs, or plugin packaging.'
author: '@artieax'
---

# skill-builder

A meta-skill that covers the full lifecycle of an agent skill — from design and scaffolding through worktree-based iteration, eval pipeline scoring, skill splitting, dependency registration, and scheduled improvement. Skills aren't "done" when first written; this skill keeps them improving.

## When to use

- "Create a new skill"
- "Scaffold a skill for X"
- "Iterate on this skill with worktrees"
- "Evaluate / score this skill's quality"
- "This skill is too big — split it"
- "Register the dependencies for this skill"
- "Set up periodic skill improvement"

**Do not trigger** when:
- Editing documentation that is not a SKILL.md file (use Edit directly)
- Developing non-skill code — functions, components, scripts (use a purpose-specific skill)
- Managing Claude's global or private skill list (use `/config` or edit `~/.claude/settings.json` directly)
- The word "skill" appears but the request is about a software module, not an agent skill

## Workflow overview

```
CREATE ──→ SCAFFOLD ──→ ITERATE (worktree loop)
                             │
                             ▼
                        EVALS (pipeline)
                             │
                    pass ────┴──── fail
                     │              │
                   MERGE          REFINE
                     │
               AUTO-DEPS ──→ AUTO-SPLIT? ──→ SCHEDULE
```

---

## Phase map (read the linked reference for each phase)

| Phase | Topic | Reference |
|---|---|---|
| 1 — CREATE | Design questions, duplicate check, persistence tiers | [`references/design.md`](references/design.md) |
| 2 — SCAFFOLD | Atom catalog, presets, `atomic-builder`, execution modes | [`references/scaffold/index.md`](references/scaffold/index.md) · [`references/scaffold/atomic-builder.md`](references/scaffold/atomic-builder.md) · [`references/scaffold/execution-modes.md`](references/scaffold/execution-modes.md) · [`references/archetypes.md`](references/archetypes.md) |
| 3 — ITERATE | Worktrees, parallel runs, exit criteria | [`references/iteration.md`](references/iteration.md) |
| 4 — EVALS | Atom catalog, presets, YAML, eval log, periodic tuning | [`references/evals/index.md`](references/evals/index.md) · [`references/evals/preset-selection.md`](references/evals/preset-selection.md) · [`references/evals/review-viewer.md`](references/evals/review-viewer.md) · [`references/lineage.md`](references/lineage.md) |
| 5 — AUTO-DEPS | sklock vs Mermaid, scan, register | [`references/dependency.md`](references/dependency.md) |
| 6 — AUTO-SPLIT | Triggers, procedure | [`references/scaffold/split.md`](references/scaffold/split.md) |
| 7 — SCHEDULE | Monthly cron / periodic checks | [`references/schedule.md`](references/schedule.md) |

**Scaffold atom templates:** `references/scaffold/atoms/<atom>.md` · **Eval atom templates:** `references/evals/atoms/`

---

## Red flags

**Always:**
- Use `git worktree add` for iteration; never `git checkout -b` in main
- Run eval pipeline (`collect_evals.py` → `generate_review.py`) before merging
- Write SKILL.md in English regardless of the conversation language
- Check for existing skills that overlap before scaffolding a new one
- Register all hard skill dependencies before merging

**Never:**
- Push to remote without an explicit user instruction
- Skip the convergence check and declare "done" based on vibes alone
- Overwrite `data/evals.jsonl` — use `collect_evals.py` (default appends; pass `--force` to replace records by id, or `--rebuild` for an atomic full refresh)
- Embed shell-provided text into HTML without escaping (XSS vector). For numeric fields rendered into HTML, coerce-to-number-or-`null` on the producer side; never trust the browser-side escape alone.
- Reference a skill by name in SKILL.md unless it exists in this repo
- Use a folded (`description: >`) or block (`description: |`) scalar for `description:` in SKILL.md frontmatter — it must be a single-line scalar (bare, single-, or double-quoted) so `optimize_description.py` can substitute it back without corrupting the file.

Full pattern catalog: [`references/red-flags.md`](references/red-flags.md)

---

## Requirements

<!-- Used by Pipeline executor's acceptance-gate element.
     RFC 2119 priorities; at least one item must be MUST — success = all MUST items passed. -->

- Never pushes to remote without an explicit instruction `MUST`
- Always uses `git worktree add -b <new-branch>`, never `git checkout -b` in main `MUST`
- Runs at least the eval collection + HTML review pipeline before declaring a skill done `MUST` — the canonical invocation, runnable from anywhere, is `python skills/skill-builder/scripts/collect_evals.py --skill-root skills/<target-skill> && python skills/skill-builder/scripts/generate_review.py --skill-root skills/<target-skill>`. `--skill-root` is **a single skill's root** (the dir containing `SKILL.md`, `projects/`, and `data/`), never the parent `skills/` dir. The shorter form `python3 scripts/collect_evals.py && python3 scripts/generate_review.py` only works when `cwd` is `skills/<target-skill>` (`--skill-root` defaults to `.`).
- SKILL.md is written in English `SHOULD`
- Skill table in AGENTS.md is updated `SHOULD`

### Where to run the scripts

Both scripts default `--skill-root .`, so `cwd` matters. The two equivalent ways:

```bash
# Form A — run from the target skill's root (short form, used in most examples below)
cd skills/<target-skill>
python3 ../skill-builder/scripts/collect_evals.py
python3 ../skill-builder/scripts/generate_review.py

# Form B — run from the repo root, point at the target via --skill-root
python skills/skill-builder/scripts/collect_evals.py --skill-root skills/<target-skill>
python skills/skill-builder/scripts/generate_review.py --skill-root skills/<target-skill>
```

Form B is the canonical, copy-paste-from-anywhere form and is what the `Requirements` block above mandates. Form A is fine in interactive sessions; the historic footgun was running Form A from the repo root, which used to silently scan the repo's empty `projects/` and write a misleading `data/evals.jsonl` at the repo root. `collect_evals.py` now refuses to run when `--skill-root` has no `SKILL.md` (e.g. the parent `skills/` dir or the repo root) and exits with a clear error; pass `--allow-missing-skill-md` only when you deliberately want to scan a heterogeneous tree that has no `SKILL.md`.

---

## Output

Report shape and phase-only variants → [`references/output-templates.md`](references/output-templates.md)
