# atom: sandbox-dir

Adds a `sandbox/` directory with fixtures, runs, and insights for validating the skill itself before shipping.

## When to include

- You want to verify the skill works before merging
- The skill's output structure needs to be checked against expectations
- You want regression coverage as the skill evolves

If the skill is a one-liner with no branching, manual spot-check is enough — skip this atom.

## Runtime

[Deno](https://deno.com/) — single binary, identical commands on Windows and Mac, built-in permission flags prevent unintended file/network access.

```bash
# Mac/Linux
curl -fsSL https://deno.land/install.sh | sh

# Windows PowerShell
irm https://deno.land/install.ps1 | iex
```

## Layout

```
skills/<name>/sandbox/
├── deno.json                   # task runner + import map
├── run.ts                      # fixture runner (cross-platform)
├── fixtures/
│   └── <scenario-name>/
│       ├── input.md            # minimal realistic trigger input
│       └── expected.md         # what a correct output looks like
├── runs/
│   └── <YYYYMMDD-HHMMSS>/
│       ├── actual.md           # what the skill produced
│       ├── diff.md             # expected vs actual delta
│       └── score.json          # per-metric scores
└── insights.md                 # aggregated signals across runs
```

## Templates

Full `deno.json`, `run.ts`, `score.json`, and `insights.md` templates → `references/archetypes.md#sandbox`.

## SKILL.md sandbox section

```markdown
## Sandbox validation

Before merging any version of this skill, run at least 3 fixtures:

1. `happy-path` — baseline correctness
2. One edge case (empty / ambiguous input)
3. One regression fixture from a previous failed run

Run: `cd sandbox && deno task run:all`

Merge gate: total sandbox score ≥ **35 / 50** across all fixtures.
If any single metric < **5**, fix before merging regardless of total.
```

## Fixture naming

| Name | Tests |
|---|---|
| `happy-path` | Most common trigger, everything goes right |
| `edge-no-input` | Trigger with missing or empty input |
| `edge-ambiguous` | Trigger phrase that could match two skills |
| `regression-<slug>` | Previously failed scenario, added to prevent recurrence |
