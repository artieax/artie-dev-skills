# v3 — changes

## From v2 (27/50) targeting ≥ 38/50

### 1. Do not trigger — expanded (trigger_precision)
Added 2 new boundaries:
- "Managing skills in a private or global-skills repo (use agent-config-manager)"
- "The word 'skill' appears but the request is about a software module, not an agent skill"

### 2. Phase 2 — pattern selection quick guide (workflow_coverage)
Added inline pattern selection table (A/B/C/D with conditions) instead of pure delegation.
Users can now pick a pattern without opening scaffold.md first.

### 3. Phase 4 — pipeline selection guide (workflow_coverage)
Replaced old "pass SKILL.md to Claude → 5 metrics" description with a pipeline selection table.
Ties directly to the element catalog in references/evals.md.
Eval log path now specifies `references/eval-log.jsonl` of the skill being evaluated.

### 4. Phase 5 — grep placeholder fixed (workflow_coverage)
Replaced literal `<other-skill>` with actual skill names + 2-step instruction (ls skills/ first).

### 5. Phase 7 — cron file path added (workflow_coverage)
Added `db/data/cron_jobs.jsonl` as the target file for the cron entry.

### 6. Red flags — worktree-first (red_flag_completeness)
- "Create a branch" → "Create a worktree (git worktree add)"
- Added: "Use an independent AI session to evaluate — never self-evaluate (IV&V principle)"
- Added: "Clean up worktrees after merging: git worktree remove + git branch -d"
- Never section: added "Never git checkout -b in the main working directory"

### 7. Output section — worktree + phase-only formats (output_clarity)
- "🌿 BRANCH:" → "🌿 WORKTREE:" with both path and branch shown
- Added Phase-only output examples: Eval only / Split only / Deps only

### 8. Requirements section added (dep_accuracy)
New `## Requirements` section with MUST tags enables acceptance-gate in Pipeline executor:
- Never pushes without instruction MUST
- Always uses git worktree add MUST
- Runs Pipeline quick before declaring done MUST
- SKILL.md is in English
- AGENTS.md skill table updated
