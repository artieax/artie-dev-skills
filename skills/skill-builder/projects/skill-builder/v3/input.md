# v3 — input

## Trigger

Eval-driven improvements from the first multi-pipeline self-eval (v2 eval: 27/50).

## Improvement targets (from eval findings)

1. 🔴 Red flags: "Create a branch" → "Create a worktree" (contradicted Phase 3)
2. 🔴 Phase 4: replace old static-scoring description with pipeline selection guide
3. 🟠 Do not trigger: add agent-config-manager boundary + non-skill-code boundaries
4. 🟠 Phase 2: add pattern selection quick guide (no longer full delegation)
5. 🟠 Phase 5: fix literal `<other-skill>` placeholder in grep command
6. 🟡 Output: "BRANCH:" → "WORKTREE:", add phase-only output examples
7. 🟡 Phase 7: add cron target file path (`db/data/cron_jobs.jsonl`)
8. 🟡 Add `## Requirements` section with MUST tags for acceptance-gate

## Branch / worktree

feature/skill-creator (worktree: artie-dev-skills-skill-creator)
