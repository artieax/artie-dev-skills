# atom: nested-sub-skill

A sub-skill that lives inside its parent's directory tree at `skills/<parent>/skills/<child>/`. Scoped to the parent — not a top-level skill.

## When to include

Use nested over top-level ([`child-skill`](child-skill.md)) when:

| Condition | Use |
|---|---|
| Phase is an internal step — users wouldn't invoke it alone | nested |
| Phase should NOT appear in the global `skills/` listing | nested |
| Phase is reusable by other orchestrators | top-level |
| User says "just run the X phase" makes sense standalone | top-level |

Rule of thumb: if putting it in `ls skills/` would be noise, nest it.

## Layout

```
skills/<parent>/
├── SKILL.md
├── references/
└── skills/
    ├── <child-a>/
    │   └── SKILL.md
    └── <child-b>/
        └── SKILL.md
```

The `skills/` sub-directory mirrors the top-level convention — any tooling that discovers SKILL.md files recursively will pick them up automatically.

## SKILL.md rules

Same atom set as a standalone skill (`frontmatter` + `trigger` + `workflow` + `redflag` + `output` + `requirements`), with these adjustments:

- `description` — note the parent context: `'<verb> … (step of <parent>)'`
- `trigger` → "Do not trigger" — redirect full-pipeline requests to `<parent>`
- No independent eval tracking needed unless the phase is complex enough to warrant it

## Parent SKILL.md reference

Reference nested sub-skills with the repo-relative path:

```markdown
### 2. Run <child-a>

→ `skills/<parent>/skills/<child-a>/SKILL.md`
```

## Dependency graph

Nested sub-skills are still nodes. Use the relative path as the node ID:

```
<parent> --> <parent>/skills/<child-a>
<parent> --> <parent>/skills/<child-b>
```

Or with sklock, list them under `depends`:

```yaml
depends:
  - skills/<parent>/skills/<child-a>
  - skills/<parent>/skills/<child-b>
```
