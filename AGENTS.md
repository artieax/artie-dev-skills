## Skills in `artie-dev-skills`

| Skill | Purpose |
|-------|---------|
| `pluginize` | Turn a skills repo into a multi-platform plugin |
| `bommit` | Commit the current diff with a clean conventional message |
| `skill-builder` | Create, iterate, evaluate, and improve skills — scaffold, worktree iteration, metrics/evals, auto sub-skill split, auto dependency registration, periodic improvement |

See `skills/*` for details.

## Red Flags

**Always**
- Bump `version` in `plugin.json` when updating this file (`AGENTS.md`)
- Create a worktree under `.worktrees/*` before starting any feature or fix work — no direct commits to `main`

**Never**
