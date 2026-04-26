# atom: child-skill

A top-level independent skill called by an orchestrator. Has its own trigger and can be invoked directly.

## When to include

Always paired with the `orchestrator` atom when the sub-skill is **user-facing** and meaningful on its own.

If the sub-skill is an internal phase that shouldn't appear in `ls skills/`, use [`nested-sub-skill`](nested-sub-skill.md) instead.

| Use `child-skill` (top-level) | Use `nested-sub-skill` |
|---|---|
| User can invoke the phase directly | Phase is only meaningful inside the parent pipeline |
| Phase is reusable by other orchestrators | Phase is internal to one parent |
| Phase warrants its own description-optimization | Phase is lightweight enough to skip evals |

## Layout

Each child is its own top-level directory — never nested:

```
skills/<phase-name>/
├── SKILL.md
└── references/        # optional, per child
```

## SKILL.md rules

- Same atom set as a regular standalone skill (`frontmatter` + `trigger` + `workflow` + `redflag` + `output` + `requirements`)
- The trigger atom MUST cover the case where the user invokes this phase directly, not via the orchestrator
- The trigger atom's `Do not trigger` should redirect "full pipeline" requests to the orchestrator

## Naming

Use a descriptive phase name that hints at the pipeline:

| Pipeline | Children |
|---|---|
| `<name>-collect` / `<name>-compare` / `<name>-recommend` / `<name>-report` | comparator pipeline |
| `<name>-extract` / `<name>-build` | atomic-builder pipeline |

The `<orchestrator-name>-<phase>` pattern keeps related skills sorted together in `ls skills/`.

## Trigger example

```markdown
## When to use

- "<phase-specific phrase>"
- "just run the <phase> phase of <orchestrator>"

**Do not trigger** when the user wants the full pipeline — invoke `<orchestrator-name>` instead.
```

## Dependency graph

The orchestrator references each child:

```
<orchestrator-name> --> <phase-name>
```

If a child reuses another skill (e.g. `bommit`), record that edge too.
