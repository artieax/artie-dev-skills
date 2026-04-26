# atom: apps-dir

Adds an `apps/` directory for standalone applications (GUI, CLI, web, TUI, etc.) that a skill can launch, open, or coordinate with.

## When to include

- The skill needs a visual interface beyond terminal output
- A reusable tool (CLI binary, dashboard, inspector) lives alongside the skill and is invoked from Workflow steps
- An app is shared by multiple sub-skills under the same orchestrator

If the operation is shell-only with no user interface, use `scripts-dir` instead. `apps/` is for artifacts that have their own build toolchain or runtime.

## Layout

```
skills/<name>/
├── SKILL.md
└── apps/
    └── <app-name>/             # one directory per app
        ├── README.md           # what it does, how to run it
        └── ...                 # free-form — Cargo.toml, package.json, etc.
```

Each `<app-name>/` directory is fully self-contained. There are no constraints on its internal structure; the app manages its own build system and dependencies.

## App naming

| Convention | Example |
|---|---|
| `kebab-case` noun | `eval-viewer`, `score-dashboard`, `diff-browser` |
| No leading verb | `diff-browser`, not `view-diffs` |
| Reflect the app's domain, not the skill's phase | `timeline-ui`, not `step3-ui` |

## Skill integration patterns

**Launch from a Workflow step**

```markdown
### 4. Review results

```bash
cd apps/eval-viewer && npm run dev
```

Opens the eval viewer at `http://localhost:5173`. Leave it running while reviewing.
```

**Open a built binary**

```markdown
### 3. Inspect diff

```bash
open apps/diff-browser/dist/diff-browser.app
```
```

**Pass data via file**

Skills write output files; apps read them. Avoid piping skill state directly into an app process — use a well-known path in `references/` or `data/` as the handoff point.

## What goes in apps vs scripts

| Situation | Use |
|---|---|
| Single shell command or pipeline | inline in SKILL.md |
| 2-10 commands, reusable logic | `scripts-dir` |
| Has a build step (compile, bundle) | `apps-dir` |
| Needs a window / browser / TUI | `apps-dir` |
| End-user runs it independently | `apps-dir` |
