## Skills in `artie-dev-skills`

| Skill | Purpose |
|-------|---------|
| `pluginize` | Turn a skills repo into a multi-platform plugin |
| `bommit` | Commit the current diff with a clean conventional message |
| `skill-builder` | Create, iterate, evaluate, and improve skills — scaffold, worktree iteration, metrics/evals, auto sub-skill split, auto dependency registration, periodic improvement |
| `session-to-instinct` | Read AI coding session logs and produce instincts using a catalog of pluggable extraction-method atoms; presets bundle atoms into named recipes (minimal / standard / safe / broadcast / research) |
| `instinct-to-harness` | Render instincts into AI harness files (claude-path, cursor-mdc, agents-md, skill-constraint, system-prompt) via a rendering-atom × harness-target catalog; BUILD writes inside the skill, DEPLOY places variants at external project paths |

See `skills/*` for details.

## Red Flags

**Always**
- Bump `version` in `plugin.json` when updating this file (`AGENTS.md`)
- Create a worktree under `.worktrees/*` before starting any feature or fix work — no direct commits to `main`
- Write all temporary files under `tmp/*` (gitignored)

**Never**
