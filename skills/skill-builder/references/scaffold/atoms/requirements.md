# atom: requirements

The `## Requirements` section — checklist consumed by the `Pipeline executor`'s `acceptance-gate` element. Items are tagged with **RFC 2119** keywords (`MUST` / `SHOULD` / `MAY`).

## Always include

Every SKILL.md needs this atom. At least one item must be marked `MUST` — that's how `acceptance-gate` decides pass/fail.

## Template

```markdown
## Requirements

<!-- Used by Pipeline executor's acceptance-gate element.
     RFC 2119 keywords. At least one item must be MUST — success = all MUST items passed. -->

- <requirement 1> `MUST`
- <requirement 2> `MUST`
- <requirement 3> `SHOULD`
- <requirement 4> `MAY`
```

## Rules

- **`MUST` = blocking.** If the skill produces output but a `MUST` requirement fails, the run is a failure.
- **`SHOULD` / `MAY` = non-blocking.** Tracked in evals but doesn't block the gate.
- **Each requirement is independently checkable.** "Always uses worktrees" is checkable; "Has good error handling" isn't.
- **Mark the dangerous ones `MUST`.** `Never pushes without instruction` is `MUST`; `Skill table is updated` is typically `SHOULD`.

## Common mistakes

- Zero `MUST` items → `acceptance-gate` always passes, eval is meaningless
- All items `MUST` → no signal about what actually matters
- Vague requirements that can't be programmatically scored
- Free-form severity ("important", "high") instead of the RFC 2119 set

## Examples from this repo

```markdown
- Never pushes to remote without an explicit instruction `MUST`
- Always uses `git worktree add`, never `git checkout -b` in main `MUST`
- Runs at least Pipeline quick before declaring a skill done `MUST`
- SKILL.md is written in English `SHOULD`
- Skill table in AGENTS.md is updated `SHOULD`
```
