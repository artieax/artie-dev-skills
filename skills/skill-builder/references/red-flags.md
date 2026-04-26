# red-flags — Always / Never pattern catalog

Pick patterns from the tables below and paste them into a new skill's `## Red flags` section.
Each pattern is self-contained — combine as needed.

---

## Always patterns

### General safety

| Pattern | Text to use |
|---|---|
| Branch before working | Always create a worktree / branch before making any change — never commit directly to main |
| Confirm before destructive ops | Confirm with the user before deleting, overwriting, or resetting anything |
| Stage by name | Stage files explicitly by path — never `git add -A` or `git add .` |
| Secret guard | Stop and flag any file that looks like a secret (`.env`, `*.pem`, `*_rsa`, `credentials.*`) before staging |
| One concept per commit | Split unrelated changes into separate commits; never mix concerns in one commit |
| No push without instruction | Never push to a remote without an explicit instruction to do so |
| No `--no-verify` | Never skip pre-commit hooks — hook failures are signals, not obstacles |

### Skill authoring

| Pattern | Text to use |
|---|---|
| Answer design questions first | Answer the three design questions (trigger / output / boundary) before writing SKILL.md |
| Eval before merge | Run evals and confirm scores meet the exit criteria before merging |
| Update dependency graph | Update `dependency-graph.md` whenever a dependency is added, changed, or removed |
| Update skill table | Update the AGENTS.md skill table whenever a skill is added or renamed |
| Propose split at threshold | Propose a skill split when 2+ independent triggers or 2+ disjoint personas appear |

### Workflow discipline

| Pattern | Text to use |
|---|---|
| Pre-check state | Check current state (status, log, worktree list) before starting any operation |
| One focus per iteration | Change only one focus area per iteration — do not mix workflow and metrics improvements |
| Read before edit | Read a file before editing it — do not assume current content from memory |
| Report result | Report the outcome (short SHA, file path, score) after completing each step |

---

## Never patterns

### Git

| Pattern | Text to use |
|---|---|
| No force push to main | Never force-push to main or any shared branch |
| No amend published commits | Never `--amend` a commit that has already been pushed |
| No branch switch in main dir | Never use `git checkout -b` in the main working directory — use `git worktree add` |
| No self-kill | Never run `taskkill //IM node.exe` or process-wide kills that could kill the current process |

### Skill content

| Pattern | Text to use |
|---|---|
| No vague output | Never write "creates a file" — always specify the exact path and format |
| No invented references | Never invent ticket numbers, issue links, or co-author trailers unless they exist |
| No marketing language | Never use "improve" or "enhance" in commit messages without saying what specifically changed |
| No premature databases | Never use a database for data that fits in markdown or JSONL |
| No nested skills | Never create a `sub-skills/` directory — split into independent top-level `skills/<name>/` |

### Safety

| Pattern | Text to use |
|---|---|
| No secret commits | Never commit files that contain credentials, even if the user asks |
| No blind overwrite | Never overwrite a previous version's output — always increment or confirm first |
| No trigger without check | Never trigger an adjacent skill on the user's behalf without asking |

---

## Default stack for skill-builder

When the agent is executing the **skill-builder** meta-skill, apply this subset in full (they are also valid picks from the tables above).

### Always

- Answer the three design questions before writing any `SKILL.md`
- Create a **worktree** (`git worktree add`) before starting work — never commit to main directly
- Run at least the `quick` pipeline before declaring a skill ready
- Use an **independent** AI session (no prior context about the skill) to evaluate — never self-evaluate (IV&V principle)
- Update the dependency graph before opening a PR
- Update the skill table in `AGENTS.md`
- Clean up worktrees after merging: `git worktree remove <path> && git branch -d <branch>`

### Never

- Never `git push` without an explicit instruction to do so
- Never `git checkout -b` in the main working directory — use `git worktree add`
- Never start writing `SKILL.md` before answering the three design questions
- Never declare a skill "done" without running evals
- Never skip hooks with `--no-verify`

---

## Composing Red flags for a new skill

Pick 3–6 patterns total (mix Always and Never). Example composition for a file-writing skill:

```markdown
## Red flags

### Always

- Stage files explicitly by path — never `git add -A` or `git add .`
- Stop and flag any file that looks like a secret before staging
- Report the output file path and line count after writing

### Never

- Never overwrite an existing file without confirming with the user first
- Never write a file without reading the current version first
- Never push without an explicit instruction to do so
```
