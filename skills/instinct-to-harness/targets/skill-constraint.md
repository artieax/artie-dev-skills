---
id: skill-constraint
kind: harness-target
provider: any            # SKILL.md is read by whichever agent runs that skill
reads: instinct + atom (rendering recipe)
writes: instincts/<slug>/variants/skill-constraint.md
deploys_to: <target-skill>/SKILL.md (append into a section chosen by polarity)
default_method: append
polarity_aware: true      # rendering and section choice change with instinct.polarity
---

# skill-constraint — append rule into a sibling SKILL.md

Generate a one-line rule to append to another agent skill's `SKILL.md`.
Rendering and section are chosen by the instinct's `polarity`:

| `polarity` | rendering | target section |
|---|---|---|
| `never` / `bad` | prohibition (Do Not) | `## やってはいけないこと` / `## Constraints` / `## Do Not` |
| `good` | preference / recipe | `## おすすめ` / `## Prefer` / `## Recipes` |

> The target name keeps the historical `skill-constraint` id for backward-compat,
> but it now covers both negative *constraints* and positive *preferences*.

## Variant template

### `polarity: never | bad` (prohibition)

```markdown
- <prohibition>（詳細 → `<detail-ref>`）
```

or in English:

```markdown
- <prohibition> (see `<detail-ref>` for details)
```

### `polarity: good` (preference)

```markdown
- Prefer <action> when <condition>（詳細 → `<detail-ref>`）
```

or in English:

```markdown
- Prefer <action> when <condition> (see `<detail-ref>` for details)
```

### `<detail-ref>` resolution

The variant must reference a detail file that actually exists at deploy time.
To make this deterministic regardless of `DEPLOY --all` iteration order, the resolution
runs in a **two-pass deploy** and reads from a **dependency-aware shared state**, never
from in-flight `harness.deployed` mutations:

**BUILD time** — render the variant with a placeholder, e.g. `__DETAIL_REF__`.
Also emit a companion detail file at `instincts/<slug>/variants/skill-constraint.detail.md`
so option 2 below has source content even when claude-path is not in play.

**DEPLOY pass 1 — plan** — for each slug being deployed:
1. Take a *snapshot* of the slug's targets after applying this DEPLOY's diff (i.e. the eventual `harness.deployed` state at end of run, not the running mutation).
2. Decide the detail-ref deterministically from that snapshot:
   1. If the snapshot includes `claude-path` → `.claude/rules/<slug>.md`
   2. Else if `target_skill` resolves and that skill has a `references/` dir → copy the companion detail file to `<target-skill>/references/<slug>.md` and link to it
   3. Else → no `(see …)` suffix; rule body is inline only
3. Targets that are siblings of `claude-path` (e.g. `skill-constraint`, append-style) are placed in a **second wave** so they always render after `claude-path` finishes pass 1's plan.

**DEPLOY pass 2 — apply** — execute the planned actions in this order:
1. file-creating targets first (`claude-path`, `claude-global`, `cursor-mdc`)
2. append-style targets second (`agents-md`, `gemini-md`, `copilot-md`, `skill-constraint`)
3. side-effecting copies (e.g. companion detail files) interleaved with their consumer in step 2

Within each wave the order is alphabetical by target id for reproducibility.

### UNDEPLOY: cascading repair

`UNDEPLOY --slug X --target claude-path` MUST cascade through anything that linked to it.
Because pass 1 records the dependency graph in `manifest.json > deployments.<target>.depends_on`
(every dependent target lists the targets whose external paths it cites), UNDEPLOY:

1. Removes the requested target's external file (and its companion `detail_ref` file, if any)
2. Updates `harness.deployed` (and `manifest.json` deploy state) for that target
3. Walks `manifest.json` for any other deployed target whose `depends_on` list contains the
   just-removed target id
4. For each such dependent (typically `skill-constraint`):
   - Re-runs the two-pass plan (pass 1, step 2) against the new `harness.deployed` snapshot
   - If the new plan differs, rewrites the dependent's external append block (and any
     companion `detail_ref` file) atomically with the new rendering (option 2 or 3)
   - Updates `deployments.<dependent>.last_synced` and recomputes `depends_on` from the new plan

Dropping cascade is forbidden: leaving a `(see .claude/rules/<slug>.md)` reference
in a sibling SKILL.md after the rule file has been removed is a dangling link bug.

Reading from `harness.deployed` snapshots (not `harness.built`) is the invariant —
building a claude-path variant without deploying it must not produce a dangling link,
and undeploying a variant must not leave dangling links in append targets.

## DEPLOY behaviour

- Method: `append` to `<target-skill>/SKILL.md`
- Section auto-detected by polarity (table above); created at end of file if absent
- `target_skill` resolution order:
  1. CLI flag `--target-skill <skill-name>`
  2. Source instinct's frontmatter `target_skill` field
  3. `.instinct.yml > emit.targets.skill-constraint.target_skill`
  4. Heuristic fallback: instinct's `path_scope` matched against known `<repo>/.agent/skill/*/` paths

If none of (1)–(4) resolves, DEPLOY fails fast with a clear error (the variant stays built; only deployment is blocked).

## Best paired with

- Rendering atom: `invariant-guard` (clean one-liner) for `polarity: never | bad`
- Rendering atom: `kata` or `decision-table` for `polarity: good`
- Instincts whose `path_scope` is inside the target skill's domain

## Anti-pattern

Don't use this for instincts that aren't relevant to a specific other skill — that just adds noise to that SKILL.md.
