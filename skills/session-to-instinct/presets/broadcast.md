---
id: broadcast
kind: extraction-preset
atoms: [failure-cluster, success-pattern, evaluator]
emit_targets: [claude-path, cursor-mdc, agents-md, gemini-md, copilot-md, skill-constraint]
---

# broadcast — emit everywhere

Same extraction as `standard`, but every approved instinct is rendered for every supported harness target.

## Atoms

Same as [`standard`](standard.md): `failure-cluster` + `success-pattern` + `evaluator`.

## Emit

All common harness targets:
- `claude-path` (Claude Code)
- `cursor-mdc` (Cursor)
- `agents-md` (Codex)
- `gemini-md` (Gemini CLI)
- `copilot-md` (GitHub Copilot)
- `skill-constraint` (any agent skill)

`broadcast_targets` is set to all of the above.

## Use when

- Polyglot teams using multiple AI assistants on the same repo
- You want one instinct file in the skill, many readers in the field
