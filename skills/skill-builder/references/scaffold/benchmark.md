# preset: benchmark

`benchmark` = `scripts` + `versioned-projects`.

```
frontmatter + trigger + workflow + redflag + output + requirements
+ references-dir + scripts-dir + versioned-projects
```

## Use when

- The skill runs repeatable benchmark campaigns and needs `projects/<project-name>/v<N>/` history
- The skill should ground its benchmark lanes or fixtures in real OSS repos, not only synthetic examples
- Each run executes scripts that collect fixtures, prepare workspaces, score outputs, and compare multiple candidates
- Benchmark lanes may mutate a repo or generate competing outputs, so each lane needs isolated state
- The user needs a winner summary in markdown after every run, not just raw JSONL scores

If the workflow is script-heavy but results do not need per-run history, use [`scripts`](scripts.md) instead.

## Directory layout

```
skills/<skill-name>/
├── SKILL.md
├── references/
│   ├── <rubric>.md
│   └── eval-log.jsonl
├── scripts/
│   ├── bench.mjs
│   ├── compare.mjs
│   └── <helper>.mjs
└── projects/
    └── <project-name>/
        ├── v1/
        │   ├── input.md
        │   └── output/
        │       ├── lanes/
        │       │   ├── lane-a.json
        │       │   └── lane-b.json
        │       ├── results.jsonl
        │       ├── report.md
        ├── v2/
        │   ├── input.md
        │   └── output/
        └── current.md
```

Ephemeral worktrees are **not** part of the saved artifact tree above. Treat them as scratch execution environments under a separate runtime path such as `.worktrees/` or `tmp/worktrees/`, and clean them up after scoring.

## How to scaffold

Run atomic-builder with the `benchmark` pick set:

```
PICK: frontmatter + trigger + workflow + redflag + output + requirements
      + references-dir + scripts-dir + versioned-projects
BUILD: skills/<skill-name>/SKILL.md + references/ + scripts/ + projects/
```

Atom-level templates:

- Content atoms — see [`minimal`](minimal.md)
- `references-dir` — [`atoms/references-dir.md`](atoms/references-dir.md)
- `scripts-dir` — [`atoms/scripts-dir.md`](atoms/scripts-dir.md)
- `versioned-projects` — [`atoms/versioned-projects.md`](atoms/versioned-projects.md)

## Parallel worktree lanes

If a benchmark lane can modify a repository or needs a distinct git state, run each lane in its own worktree.

```bash
git fetch <remote> <base-ref>
git worktree add -b bench/<project-name>-<lane> .worktrees/<project-name>-<lane> <base-ref>
```

`<base-ref>` should usually resolve to the repository's default branch once per run, rather than hard-coding `main`.

Rules:

- Keep the launcher or main working directory untouched; never branch-swap it for a benchmark lane
- Run lane-specific setup and benchmark commands inside the lane worktree only
- Write lane-level scores and artifacts back to `projects/<project-name>/v<N>/output/`
- Keep ephemeral worktrees outside the versioned `output/` tree so persisted artifacts stay clean
- Remove ephemeral worktrees after scoring: `git worktree remove <path>` then `git branch -d <branch>`
- When `--parallel <n>` is used, create one lane record per runner so the final comparison is reproducible

## OSS-first sourcing policy

Benchmark presets built from this template should search OSS candidates aggressively before inventing synthetic cases.

Rules:

- Prefer real OSS repos, issues, PRs, fixtures, and benchmark tasks when they match the target domain
- Use synthetic fixtures only to fill gaps that OSS coverage does not provide
- Record the chosen repo URL plus commit, tag, or release in `input.md` so the run is reproducible
- When multiple materially different OSS candidates exist, compare at least 2 before freezing the benchmark set
- Explain in `report.md` when a synthetic case was used instead of an OSS source

Why:

- OSS tasks usually surface edge cases, conventions, and failure modes that toy tasks miss
- The resulting rankings tend to predict real-world quality better than hand-written micro-benchmarks

## SKILL.md workflow integration

````markdown
### 2. Run benchmark lanes

```bash
node scripts/bench.mjs --project <project-name> --preset <id> --parallel <n> --report-md
```

Expected output:
- `projects/<project-name>/v<N>/input.md`
- `projects/<project-name>/v<N>/output/lanes/*.json`
- `projects/<project-name>/v<N>/output/results.jsonl`
- `projects/<project-name>/v<N>/output/report.md`
- `projects/<project-name>/current.md`
````

## Required run contract

Every benchmark run should satisfy all of the following:

- Create the next version folder under `projects/<project-name>/v<N>/`
- Freeze the benchmark corpus for that run by recording its OSS sources in `input.md`
- Preserve raw lane outputs separately from the summarized ranking
- Emit `output/report.md` on every run, even if all lanes fail or tie
- State the winner, or explicitly say `no clear winner`, based on the scoring rubric
- Update `current.md` only after the run finishes and the report is written

## Example run artifact tree

One completed run should look roughly like this:

```text
skills/<skill-name>/
└── projects/
    └── benchmark-a/
        ├── current.md
        └── v3/
            ├── input.md
            └── output/
                ├── lanes/
                │   ├── lane-a.json
                │   └── lane-b.json
                ├── results.jsonl
                └── report.md
```

## `report.md` contents

Each run's markdown report should answer the user's main question: "which approach was best this time?"

Suggested shape:

```markdown
# Benchmark report — <project-name> v<N>

## Run summary

- Preset: <preset-id>
- Parallel lanes: <n>
- Scoring rubric: <reference>
- OSS sources:
  - <repo>@<commit-or-tag>
  - <repo>@<commit-or-tag>
- Winner: <lane-id> | no clear winner

## Lane comparison

| Lane | Score | Pass rate | Duration | Cost | Notes |
|---|---:|---:|---:|---:|---|
| lane-a | 84 | 0.90 | 132s | 12k tok | strongest overall |
| lane-b | 79 | 0.85 | 101s | 10k tok | cheaper but missed edge case |

## Why the winner won

- <criterion 1>
- <criterion 2>

## Regressions / caveats

- <risk or tie note>

## Artifact paths

- `output/results.jsonl`
- `output/lanes/`
```

## Conventions

- One run = one version folder. Never overwrite a previous run's `output/`
- Keep scoring criteria in `references/<rubric>.md` or `references/<topic>.md`
- Use `results.jsonl` for per-task atoms, `lanes/*.json` for per-runner detail, and `report.md` for the human summary
- Favor OSS-backed corpora and note the exact source revision for every imported task
- Run the [`measured`](../evals/index.md#presets--named-atom-combinations) eval pipeline after major Workflow changes so value and runtime cost stay visible

## When to change shape

- Downgrade to [`scripts`](scripts.md) if per-run version history is unnecessary
- Upgrade to [`split`](split.md) if collect / execute / compare / report each become independently triggerable phases
