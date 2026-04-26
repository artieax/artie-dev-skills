# archetypes — domain-specific atom combinations

Archetypes are atom combinations chosen by what the skill *does*, not by file size. Each archetype below names its atom combination at the top so it composes cleanly with the [atom catalog](scaffold/index.md#atom-catalog) and the [presets](scaffold/index.md#presets--named-atom-combinations).

---

## versioned

**Atom combination:** `standard` + `versioned-projects`

```
frontmatter + trigger + workflow + redflag + output + requirements
+ references-dir + versioned-projects
```

**Use when:** The skill produces iterative outputs for a named project, and the user needs to track, compare, or roll back between versions.

### Directory layout

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

### SKILL.md additions

```markdown
## Version management

- Each run creates a new `v<N>/` folder under `projects/<project-name>/`
- `current.md` is updated to point to the latest successful version
- Never overwrite a previous version's `output/` — always increment N

### Rollback

To roll back, update `current.md` to point to the desired version.
The old version's `output/` is preserved and can be re-used as-is.
```

### Skill improvement as a project (self-referential use)

The `versioned` archetype can also be used to manage the improvement iterations of the skill itself — treating each eval cycle as a versioned project run.

```
skills/<name>/
├── SKILL.md
├── references/
│   └── eval-log.jsonl
└── projects/
    └── <name>/                    # skill name = project name
        ├── v1/
        │   ├── input.md           # what problem / user request triggered this iteration
        │   ├── changes.md         # what changed from the previous version
        │   └── eval.json          # scores at this version
        ├── v2/
        │   ├── input.md
        │   ├── changes.md
        │   └── eval.json
        └── current.md             # pointer: "active version = v2"
```

`input.md` for skill iterations:
```markdown
# v2 — input

## Trigger
User asked: "the workflow section is too long, worktree steps are unclear"

## Focus
Rewrite Phase 3 (ITERATE) with explicit worktree commands and exit criteria.

## Branch
iter/skill-builder-v2
```

`changes.md` for skill iterations:
```markdown
# v2 — changes

- Rewrote Phase 3 with `git worktree add` as the primary command
- Added exit criteria table (≥7 all metrics or +15% improvement)
- Removed duplicate layout descriptions from Phase 2 (moved to scaffold.md)
```

`eval.json` mirrors `eval-log.jsonl` for that version:
```json
{
  "version": "v2",
  "date": "2026-04-25",
  "scores": {
    "trigger_precision": 8,
    "workflow_coverage": 9,
    "output_clarity": 8,
    "red_flag_completeness": 8,
    "dep_accuracy": 9
  },
  "total": 42
}
```

### When NOT to use this archetype

- The skill produces a single, non-revisable output → use `minimal` or `standard`
- Versions are already tracked by git commits and no human-readable summary is needed

---

## comparator

**Atom combination:** `orchestrator` + 4 × `child-skill` (`-collect` / `-compare` / `-recommend` / `-report`)

```
parent:  frontmatter + trigger + workflow + redflag + output + requirements
         + orchestrator + references-dir
each child: frontmatter + trigger + workflow + redflag + output + requirements
```

**Use when:** The skill's job is to evaluate multiple libraries, approaches, or implementations, and recommend or compose a result from the comparison.

### Directory layout

Split phases into independent top-level skills — never nest them inside the orchestrator.

```
skills/<name>/                      # orchestrator: calls the phase skills in order
├── SKILL.md
└── references/
    ├── comparison-matrix.md        # rows = options, cols = criteria
    ├── decision-log.jsonl          # why a choice was made, per run
    └── eval-log.jsonl

skills/<name>-collect/              # fetch candidates & their metadata
└── SKILL.md

skills/<name>-compare/              # score each candidate per criterion
└── SKILL.md

skills/<name>-recommend/            # synthesise scores → recommendation
└── SKILL.md

skills/<name>-report/               # format output for the user
└── SKILL.md
```

### comparison-matrix.md template

```markdown
# Comparison matrix — <topic>

| Library / Option | Criterion A | Criterion B | Criterion C | Total |
|---|---|---|---|---|
| option-1 | 8 | 6 | 9 | 23 |
| option-2 | 5 | 9 | 7 | 21 |

**Winner:** option-1 (23/30) — strong on A and C; acceptable on B.
**Runner-up:** option-2 — prefer if Criterion B is the bottleneck.
```

### Internal list registry

When the comparator's domain has a stable-but-growing set of candidates (OCR libs, formatters, image tools), store an internal list rather than running web search on every invocation:

```
skills/<name>/
└── references/
    ├── <domain>-list.md        # curated candidate list  ← add list-registry atom
    ├── comparison-matrix.md
    └── decision-log.jsonl
```

The `-collect` phase reads `references/<domain>-list.md` first, then optionally augments with a targeted web search for items newer than the latest `Added` date.

To auto-expand the list over time, wire it to `skill-auto-tuner` (see [`atoms/list-registry.md`](atoms/list-registry.md)).

---

### SKILL.md orchestration section

```markdown
## Orchestration

1. **collect** — read `references/<domain>-list.md`; optionally augment with web search
2. **compare** — score each candidate; write scores to `comparison-matrix.md`
3. **recommend** — read matrix; write recommendation + rationale
4. **report** — format for user; append run to `decision-log.jsonl`

Each phase skill can be triggered independently if the user wants to re-run just one phase.
```

### When NOT to use this archetype

- There is only one option to evaluate → no comparison needed
- Comparison is a one-off and doesn't need to be revisited → inline the logic in a single SKILL.md

---

## sandbox

**Atom combination:** `standard` + `sandbox-dir`

```
frontmatter + trigger + workflow + redflag + output + requirements
+ references-dir + sandbox-dir
```

**Use when:** You want to verify that a skill actually works as intended — without side effects — and extract improvement signals from the results.

**Runtime: [Deno](https://deno.com/)** — single binary, identical commands on Windows and Mac, built-in permission flags prevent unintended file/network access.

```
# Install (Windows & Mac)
curl -fsSL https://deno.land/install.sh | sh   # Mac/Linux
irm https://deno.land/install.ps1 | iex        # Windows PowerShell
```

### Directory layout

```
skills/<name>/
├── SKILL.md
├── references/
│   └── eval-log.jsonl
└── sandbox/
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
    │       └── score.json          # per-metric scores for this run
    └── insights.md                 # aggregated signals across runs
```

### sandbox/deno.json

```json
{
  "tasks": {
    "run":    "deno run --allow-read=./fixtures,./runs --allow-write=./runs run.ts",
    "run:all": "deno run --allow-read=./fixtures,./runs --allow-write=./runs run.ts --all",
    "diff":   "deno run --allow-read=./runs run.ts --diff"
  }
}
```

Run a fixture:
```bash
# Mac / Linux
deno task run -- --fixture happy-path

# Windows (same command)
deno task run -- --fixture happy-path
```

### sandbox/run.ts template

```ts
// run.ts — fixture runner
// Usage: deno task run -- --fixture <name> [--all] [--diff]

import { parseArgs } from "jsr:@std/cli/parse-args";
import { join } from "jsr:@std/path";
import { ensureDir } from "jsr:@std/fs";

const args = parseArgs(Deno.args);
const fixtureDir = "./fixtures";
const runsDir = "./runs";

async function runFixture(name: string) {
  const timestamp = new Date().toISOString().replace(/[:.]/g, "-").slice(0, 19);
  const outDir = join(runsDir, timestamp);
  await ensureDir(outDir);

  const input = await Deno.readTextFile(join(fixtureDir, name, "input.md"));
  const expected = await Deno.readTextFile(join(fixtureDir, name, "expected.md"));

  // --- replace this block with actual skill invocation ---
  const actual = `[skill output for fixture: ${name}]\n\n${input}`;
  // -------------------------------------------------------

  await Deno.writeTextFile(join(outDir, "actual.md"), actual);
  await Deno.writeTextFile(join(outDir, "diff.md"), diffText(expected, actual));
  await Deno.writeTextFile(join(outDir, "score.json"), JSON.stringify({
    run: timestamp,
    fixture: name,
    skill_version: "v1",
    scores: { trigger_precision: null, workflow_coverage: null, output_clarity: null,
               red_flag_completeness: null, dep_accuracy: null },
    total: null,
    notes: "score manually after reviewing actual.md vs expected.md"
  }, null, 2));

  console.log(`✅ run saved → ${outDir}`);
}

function diffText(expected: string, actual: string): string {
  const a = expected.split("\n");
  const b = actual.split("\n");
  return b.map((line, i) => a[i] === line ? `  ${line}` : `- ${a[i] ?? ""}\n+ ${line}`).join("\n");
}

if (args.all) {
  for await (const entry of Deno.readDir(fixtureDir)) {
    if (entry.isDirectory) await runFixture(entry.name);
  }
} else if (args.fixture) {
  await runFixture(args.fixture as string);
} else {
  console.error("Usage: deno task run -- --fixture <name>  |  --all");
  Deno.exit(1);
}
```

### score.json schema

```json
{
  "run": "2026-04-25T14-30-00",
  "fixture": "happy-path",
  "skill_version": "v1",
  "scores": {
    "trigger_precision": 8,
    "workflow_coverage": 6,
    "output_clarity": 7,
    "red_flag_completeness": 5,
    "dep_accuracy": 9
  },
  "total": 35,
  "worst_metric": "red_flag_completeness",
  "notes": "output format did not match expected structure"
}
```

### insights.md template

```markdown
# Insights — <skill-name>

## Recurring signals

| Signal | Seen in runs | Hypothesis | Action |
|---|---|---|---|
| output_clarity < 7 | run1, run2, run3 | Output section is vague | Rewrite Output with concrete file paths |
| edge-ambiguous always fails | run1, run2 | Trigger overlaps with <other-skill> | Add Do not trigger case |

## Suggested next iteration

- [ ] Fix: <specific change derived from signals>
- [ ] Re-run fixture `edge-ambiguous` after fix
- [ ] Target total score ≥ 40 before merging
```

### SKILL.md sandbox section

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

### Fixture naming

| Name | Tests |
|---|---|
| `happy-path` | Most common trigger, everything goes right |
| `edge-no-input` | Trigger with missing or empty input |
| `edge-ambiguous` | Trigger phrase that could match two skills |
| `regression-<slug>` | Previously failed scenario, added to prevent recurrence |

### When NOT to use this archetype

- The skill is a one-liner with no branching logic → manual spot-check is enough
- The skill calls external APIs with real side effects → mock the boundary or use a dedicated integration test
