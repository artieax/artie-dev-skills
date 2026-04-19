---
name: bommit
description: 'Commit the current diff with a clean conventional message — the bot picks the prefix, writes the subject, and runs `git commit`. Use when the user says "bommit", "commit this", or "just commit" without dictating the message. bommit = bot + commit.'
author: @artieax
---

# bommit

**bommit = bot + commit.** The agent looks at the diff, writes a clear message following a chosen convention, and runs `git commit`. The user doesn't write the message — the bot does.

This skill is about *message authorship and commit execution*. It is not a general git workflow skill. It does not push, branch, rebase, or resolve conflicts unless the user asks separately.

## When to use

- "bommit" / "bommit this"
- "just commit"
- "commit it for me"
- "write a commit message and commit"
- "wrap this up with a commit"

**Do not trigger** when:

- The user has written their own message — just run `git commit -m "..."` with their text.
- The user wants to review staged vs unstaged changes — that's a status question, not a commit.
- There is nothing to commit (`git status` clean) — say so and stop.

## Workflow

### 1. On first use in a session: confirm the convention

Before the first commit, show the user the prefix table (below) and ask:

> "I'll commit using the Conventional Commits style — prefix + short imperative subject, e.g. `feat: add retry to upload queue`. OK to proceed with this convention, or do you want a different one (e.g. gitmoji, plain sentences, Japanese subject, ticket-prefixed)?"

Capture the answer. For the rest of the session, use that convention for every bommit call without re-asking. If the user says "use Japanese subjects" or "prefix with ARTIE-123", honor that.

Skip this step if the repo's recent `git log` already shows a clear, consistent convention — adopt it silently and tell the user which one you matched ("matching your existing `type(scope): subject` style"). Only ask if the log is mixed or empty.

### 2. Inspect the working tree

Run in parallel:

- `git status --short` — see what's changed, what's staged, what's untracked.
- `git diff --staged` — if anything is staged, that's the commit scope.
- `git diff` — unstaged changes.
- `git log -n 5 --oneline` — to match existing convention and tone.

Decide what goes in the commit:

- **Something is staged** → commit only the staged changes. Do not auto-stage more.
- **Nothing is staged, tracked files have changes** → stage the relevant tracked files by name (not `git add -A`, not `git add .`). Skip `.env`, credentials, large binaries, editor/OS droppings.
- **Only untracked files** → ask which ones to include before staging. Never blindly add all untracked files.
- **Mixed** → commit staged as-is; ask whether to fold in unstaged hunks.

### 3. Pick a prefix

Use this table. Pick the single prefix that best describes the dominant change. If a commit genuinely spans two categories, prefer the more user-visible one (`feat` > `refactor`, `fix` > `chore`).

| Prefix | Use for | Examples |
|--------|---------|----------|
| `feat` | New user-facing capability | new endpoint, new flag, new UI element |
| `fix` | Bug fix | crash, wrong output, regression repair |
| `docs` | Documentation only | README, comments, SKILL.md, guides |
| `style` | Formatting / whitespace / lint — no logic change | prettier run, import sort |
| `refactor` | Code restructure with no behavior change | rename, extract function, reorganize |
| `perf` | Performance improvement | caching, query optimization |
| `test` | Tests added or fixed | new unit tests, flaky test repair |
| `chore` | Maintenance not fitting elsewhere | deps bump, tooling config, gitignore |
| `build` | Build system / packaging | webpack, tsconfig, Dockerfile |
| `ci` | CI config | GitHub Actions, pipeline edits |
| `revert` | Reverting a prior commit | `git revert` output |
| `wip` | Intentional in-progress snapshot | only if user explicitly asks for a WIP commit |

Scope (optional) goes in parens: `feat(upload): ...`, `fix(auth): ...`. Use it when the repo's existing log does; skip it otherwise.

### 4. Draft the message

**Subject line** (≤ 72 chars):

- `<prefix>[(<scope>)]: <imperative summary>`
- Imperative mood: "add", "fix", "remove" — not "added", "fixes", "removing".
- Concrete about *what changed*, not vague: `fix: handle null user in header` beats `fix: bug`.
- No trailing period.

**Body** (optional, add when the subject can't carry the meaning alone):

- Blank line after subject.
- Wrap at ~72 chars.
- Explain *why* or *what the reader needs to know* — not a line-by-line diff recap.
- Skip the body entirely for small, self-explanatory changes. Don't pad.

**Never include**:

- "Generated with Claude Code" / co-author trailers unless the repo's log already has them or the user asks.
- Issue/PR numbers you invented.
- File lists (`Modified: foo.ts, bar.ts`) — the diff already shows that.
- Marketing language ("improve", "enhance") without saying what specifically.

### 5. Show and commit

Show the user the final message and the list of files being committed, then run:

```bash
git commit -m "$(cat <<'EOF'
<subject>

<body if any>
EOF
)"
```

Use a heredoc even for single-line messages — it keeps quoting safe across shells.

After the commit:

- Run `git status` to confirm it landed and show what (if anything) remains uncommitted.
- Report the short SHA and subject back to the user in one line.

### 6. If the commit fails

- **Pre-commit hook failed** → read the hook output, fix the underlying issue if trivial (formatter, lint autofix), re-stage, and create a **new** commit. Do not `--amend`. Do not `--no-verify`.
- **Nothing to commit** → report `git status` and stop.
- **Merge/rebase in progress** → stop and tell the user; bommit doesn't drive merge resolution.

## Red flags

### Always

- **Stage files by name.** Pick each path explicitly — no wildcards that could sweep in secrets or junk.
- **Confirm the convention once** per session before the first commit (or match the existing `git log` and say so).
- **Honor the captured convention** for every subsequent bommit in the session — don't drift back to defaults.
- **Stop and ask** when the diff touches anything that looks like a secret (`.env`, `*.pem`, `credentials.*`, `*_rsa`, private keys).
- **Propose splitting** when the diff spans unrelated concerns — offer to commit a subset now and the rest separately.
- **Create a new commit** on pre-commit hook failure after fixing the issue — never reach for `--amend` to paper over it.
- **Report back** with the short SHA + subject on success, or a clear reason on refusal.

### Never

- **Never `git add -A` or `git add .`** — too easy to stage secrets, build artifacts, or unrelated work.
- **Never `--amend`** unless the user explicitly asks.
- **Never `--no-verify`** unless the user explicitly asks — hook failures are signals, not obstacles.
- **Never push, branch, rebase, or merge** — bommit stops at the commit.
- **Never commit files that look like secrets**, even if the user seems to want it — stop and confirm first.
- **Never invent** ticket numbers, issue references, co-authors, or "Generated with …" trailers unless the repo's log already uses them or the user asks.
- **Never commit across unrelated concerns** in one shot.
- **Never pad the message** with marketing words ("improve", "enhance") that don't say what actually changed.

## Examples

### Simple fix

Diff: one-line null check added in `src/header.tsx`.

```
fix(header): guard against null user before reading name
```

No body needed.

### New feature with context worth preserving

Diff: new `/api/exports` endpoint, 3 files.

```
feat(api): add CSV export endpoint for orders

Adds GET /api/exports/orders?from=&to= returning a streaming CSV.
Uses the existing OrderRepo query path; auth mirrors /api/orders.
```

### Refactor

Diff: extracted `formatCurrency` into shared util, 6 call sites updated, no behavior change.

```
refactor: extract formatCurrency into lib/money

No behavior change. Consolidates six inlined formatters so the
rounding rule lives in one place.
```

### Docs-only

Diff: README typo + new install section.

```
docs: fix typo and add Cursor install section to README
```

### User asked for Japanese subjects

Convention captured in step 1: Japanese subject, no prefix.

```
ヘッダーでユーザーが null のときに落ちる不具合を修正
```

Honor the convention — don't reintroduce English prefixes.

## Output

One commit (or a refusal with a clear reason), plus a one-line report:

```
✅ committed a1b2c3d — fix(header): guard against null user before reading name
```

That's it. No summary of what the diff did — the message itself is the summary.
