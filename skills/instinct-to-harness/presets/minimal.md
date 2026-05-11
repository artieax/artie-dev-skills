---
id: minimal
kind: emit-preset
targets: [claude-path]
default_atom_per_target:
  claude-path: auto
---

# minimal — claude-path only

The smallest viable emit set. Everything goes to `.claude/rules/`; no broadcast.

## Targets

- [`claude-path`](../targets/claude-path.md)

## Use when

- Solo workflow on Claude Code
- Smoke test before enabling broader broadcast
