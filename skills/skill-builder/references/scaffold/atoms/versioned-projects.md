# atom: versioned-projects

Adds a `projects/<name>/v<N>/` directory tree for skills that produce iterative outputs the user wants to track, compare, or roll back.

## When to include

- The skill produces outputs for a named project that evolve over time
- Users need to compare or roll back between versions
- The skill itself benefits from versioned self-improvement (eval-driven iteration)

If the skill produces a single non-revisable output, skip — git history is enough.

## Layout

```
skills/<name>/
├── SKILL.md
├── references/
│   └── eval-log.jsonl
└── projects/
    └── <project-name>/
        ├── v1/
        │   ├── input.md          # what was fed in
        │   └── output/           # generated artifacts
        ├── v2/
        │   ├── input.md
        │   └── output/
        └── current.md            # pointer: "active version = v2"
```

## File conventions

- `input.md` — what triggered this version (user request, eval signal, regression)
- `output/` — generated artifacts. Never overwrite a previous version's output
- `current.md` — single-line pointer to the active version

## SKILL.md additions

```markdown
## Version management

- Each run creates a new `v<N>/` folder under `projects/<project-name>/`
- `current.md` is updated to point to the latest successful version
- Never overwrite a previous version's `output/` — always increment N

### Rollback

To roll back, update `current.md` to point to the desired version. The old `output/` is preserved.
```

## Self-referential variant

The atom can also manage the skill's own iteration cycles. In that case `<project-name>` = the skill name, and each version captures `input.md` + `changes.md` + `eval.json` + `skill.md` (a frozen snapshot of `SKILL.md` at that version). See `references/archetypes.md#versioned` for the full template.

`skill.md` is required if you plan to use `scripts/optimize.py`: the optimizer needs the SKILL.md content of the version that scored, not the change-notes in `input.md`. Save it with:

```bash
cp skills/<name>/SKILL.md skills/<name>/projects/<name>/v<N>/skill.md
```
