---
id: broadcast
kind: emit-preset
targets: [claude-path, cursor-mdc, agents-md, gemini-md, copilot-md, skill-constraint]
providers: [claude, cursor, codex, gemini, copilot, any]   # implicitly enabled while this preset is active
default_atom_per_target:
  claude-path: auto
  cursor-mdc: auto
  agents-md: invariant-guard
  gemini-md: invariant-guard
  copilot-md: anti-pattern-gallery
  skill-constraint: auto      # polarity-aware (see ../targets/skill-constraint.md)
---

# broadcast — every common harness

Render every approved instinct for every supported AI assistant.

## Targets

- [`claude-path`](../targets/claude-path.md)
- [`cursor-mdc`](../targets/cursor-mdc.md)
- [`agents-md`](../targets/agents-md.md)
- [`gemini-md`](../targets/gemini-md.md)
- [`copilot-md`](../targets/copilot-md.md)
- [`skill-constraint`](../targets/skill-constraint.md)

## Rendering policy

- claude-path / cursor-mdc: `auto` — preserve the instinct's own `best_preset`
- agents-md / gemini-md: force `invariant-guard` for short bullet renderings
- copilot-md: force `anti-pattern-gallery` (Copilot's strength is NG/OK contrast)
- skill-constraint: `auto` (polarity-aware)

## Provider implication

This preset's `providers:` list is **implicitly applied** when the preset is active —
selecting `broadcast` flips `emit.providers.<id>.enabled: true` for every provider it
needs. Users who want to keep a provider disabled while running broadcast must override
explicitly (`emit.providers.cursor.enabled: false` after `preset: broadcast`).

Without this rule the bundled `cursor-mdc` / `agents-md` / `gemini-md` / `copilot-md`
targets would silently fall out of the emission set because the built-in defaults in
the full schema disable those providers.

## Use when

- Polyglot teams running multiple AI assistants on the same repo
