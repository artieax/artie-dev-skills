# atom: list-registry

A curated candidate list stored in `references/` that a comparator or orchestrator skill reads at run-time, instead of performing web search on every invocation.

## When to include

- The skill compares or selects from a domain with a stable-but-growing set of candidates (libraries, tools, APIs, models)
- Deterministic, offline-capable execution is preferred
- The list needs periodic expansion without touching SKILL.md

## Template

```markdown
# <domain>-list — candidate registry

<!-- Auto-expansion via skill-auto-tuner. Manual additions go above the divider. -->

| Name | Description | Source | Added |
|---|---|---|---|
| option-a | One-line description | URL or "manual" | YYYY-MM-DD |
```

## Layout

```
skills/<name>/
├── SKILL.md
└── references/
    └── <domain>-list.md    ← this atom
```

## Wiring to skill-auto-tuner

Add an entry to the skill-auto-tuner schedule so the list grows automatically:

```jsonl
{"skill":"<name>","target":"references/<domain>-list.md","schedule":"0 9 1 * *","task":"search for new <domain> candidates; propose additions as a PR"}
```

The auto-tuner outputs `proposals/YYYY-MM-DD.md`; review and merge to expand the list.

## collect-phase integration

The `-collect` child skill reads this list before any web search:

```markdown
## Workflow

1. Read `../references/<domain>-list.md` — use as the starting candidate set
2. Optionally augment with a targeted web search for items newer than the latest `Added` date
3. Output merged candidate list to `comparison-matrix.md`
```

## When NOT to include

- The candidate set is static and will never change — inline it directly in SKILL.md
- Candidates are generated dynamically per-run from user input — no registry needed
