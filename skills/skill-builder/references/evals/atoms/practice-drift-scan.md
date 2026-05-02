# atom: practice-drift-scan

| Type | Cost | Depends on |
|---|---|---|
| proposer | high | none (operates on SKILL.md + caller-supplied sources) |

Scan external sources for current skill-authoring practices, compare against
the target skill, and emit a list of **proposals** — new atoms, new SKILL.md
sections, scripts, or scaffold tweaks — that look worth adopting.

The atom is a *discovery* primitive, not an applier. It produces a structured
proposal set; a human (or a downstream `acceptance-gate` run) decides what
ships. Unlike [`description-optimization`](description-optimization.md), which
is closed-loop over the existing SKILL.md text, this atom is open-loop and
pulls signal in from outside the repo.

The atom is **content-agnostic**: it does not hardcode source URLs, a research
cadence, or a delivery channel. The caller's harness — a GitHub Action,
`/schedule`, `/loop`, a `Stop` hook, or a manual invocation — supplies the
source list and decides when to run. This keeps the atom portable across
projects whose maintainers trust different channels.

## When to add

- Skill is past its initial authoring sprint and entering a maintenance phase
- Periodic refresh (monthly / quarterly) to catch drift from current practice
- Contributors have run dry on improvement ideas — use external signal as a
  prompt
- After a major upstream release (new model family, new agent framework,
  new harness feature) that may obsolete parts of the skill

Skip when the skill is still in active churn — proposals will collide with
in-flight work.

## Inputs

- `SKILL.md` (full text)
- Existing atom / scaffold / reference inventory under the skill's directory
  (used for dedup)
- `sources` — caller-supplied list. Each entry is one of:
  - URL (docs page, blog post, RSS feed)
  - GitHub repo (`owner/name` — scanned for `SKILL.md` / `agents.md` patterns)
  - Local path (e.g. another skill in the same monorepo to compare against)
- Optional `focus` string — narrow the scan ("eval techniques only",
  "trigger-precision improvements", etc.). Empty = broad scan.

The atom does **not** invent sources. If the caller passes none, it returns
`{"proposals": [], "error": "no sources supplied"}` and stops.

## Pipeline

```
1. Fetch each source                  ─→ caller's preferred fetcher
                                          (WebFetch, gh, fs read, etc.)
2. Extract candidate practices         ─→ free-form list of (name, evidence URL)
3. Dedup against existing inventory    ─→ drop anything already covered by
                                          an atom / SKILL.md section / script
4. Score each candidate                ─→ {fit_for_this_skill, novelty,
                                            evidence_strength} 0–10 each
5. Emit proposals with diff sketches   ─→ never write to disk; output only
```

Step 1's mechanics (which fetcher, auth, rate limits) are the harness's
responsibility — the atom just expects fetched text.

## Output

```json
{
  "scan_date": "2026-05-02",
  "skill": "skills/<name>",
  "sources_consulted": [
    {"source": "https://...", "fetched_chars": 18234},
    {"source": "owner/repo", "fetched_chars": 4120}
  ],
  "proposals": [
    {
      "title": "Add a `failure-mode-log` atom",
      "target": "atom",
      "target_path": "references/evals/atoms/failure-mode-log.md",
      "rationale": "Three of the surveyed projects ship a per-run failure log distinct from open-questions. Current skill conflates them.",
      "evidence": ["https://..."],
      "diff_sketch": "New file. ~40 lines. Mirrors open-questions-log structure.",
      "fit_for_this_skill": 8,
      "novelty": 9,
      "evidence_strength": 7
    },
    {
      "title": "Tighten `## When to use` with negative examples",
      "target": "skill_md",
      "target_path": "SKILL.md",
      "rationale": "Anthropic skill-creator guide now recommends 3+ negative examples; current skill has 1.",
      "evidence": ["https://..."],
      "diff_sketch": "Add 2 bullets under `Do not trigger`.",
      "fit_for_this_skill": 9,
      "novelty": 5,
      "evidence_strength": 9
    }
  ],
  "rejected": [
    {"candidate": "Add a benchmark harness", "reason": "duplicate — covered by `baseline-comparison`"},
    {"candidate": "Memory-augmented agents", "reason": "out of scope — orthogonal to skill authoring"}
  ]
}
```

Targets are open-set. `atom`, `skill_md`, `script`, `scaffold`, `reference`,
`prompt`, `workflow` are the common ones; the atom may emit other strings if
a proposal genuinely doesn't fit.

## Example

Walk-through of one scan against `skills/skill-builder` itself.

**Caller config** (lives in the harness, not in this atom):

```yaml
skill: skills/skill-builder
focus: "eval techniques and skill-authoring patterns"
sources:
  - https://docs.anthropic.com/claude/docs/skills          # official guide
  - https://www.anthropic.com/engineering                  # eng blog index
  - anthropics/skills                                       # github reference
  - skills/pluginize                                        # sibling skill in monorepo
```

**Step 1 — fetch.** Harness pulls each source via WebFetch / `gh repo view` / fs read; the atom receives the raw text plus a per-source `fetched_chars` count.

**Step 2 — extract candidates.** Free-form list, e.g.:

```
- "per-run failure log separate from open-questions"   (anthropic eng blog)
- "fixture-level provenance tags"                       (anthropics/skills)
- "negative example minimum of 3 in `When to use`"      (docs.anthropic.com)
- "memory-augmented session loops"                      (anthropic eng blog)
- "auto-bundled multi-skill plugin manifest"            (skills/pluginize)
```

**Step 3 — dedup.** Walks `references/evals/atoms/`, `references/scaffold/`, `prompts/`, `scripts/`, plus the SKILL.md text. Drops anything covered. The "auto-bundled multi-skill plugin manifest" is rejected here — already the job of the sibling `pluginize` skill.

**Step 4 — score** each survivor on `{fit_for_this_skill, novelty, evidence_strength}` (0–10).

**Step 5 — emit.** Final output:

```json
{
  "scan_date": "2026-05-02",
  "skill": "skills/skill-builder",
  "sources_consulted": [
    {"source": "https://docs.anthropic.com/claude/docs/skills", "fetched_chars": 22140},
    {"source": "https://www.anthropic.com/engineering", "fetched_chars": 8430},
    {"source": "anthropics/skills", "fetched_chars": 16200},
    {"source": "skills/pluginize", "fetched_chars": 5210}
  ],
  "proposals": [
    {
      "title": "Add a `failure-mode-log` atom",
      "target": "atom",
      "target_path": "references/evals/atoms/failure-mode-log.md",
      "rationale": "Surveyed projects ship a per-run failure log distinct from open-questions. Current skill conflates them under open-questions-log.",
      "evidence": ["https://www.anthropic.com/engineering/<post>", "anthropics/skills/<path>"],
      "diff_sketch": "New file ~40 lines, mirrors open-questions-log structure with a failure_kind enum.",
      "fit_for_this_skill": 8,
      "novelty": 9,
      "evidence_strength": 7
    },
    {
      "title": "Require 3+ negative examples in `## When to use`",
      "target": "skill_md",
      "target_path": "skills/skill-builder/SKILL.md",
      "rationale": "Anthropic skill-creator guide now recommends ≥3 negative examples; current skill has 1.",
      "evidence": ["https://docs.anthropic.com/claude/docs/skills"],
      "diff_sketch": "Add 2 bullets under `Do not trigger` plus update `references/scaffold/minimal.md` template.",
      "fit_for_this_skill": 9,
      "novelty": 5,
      "evidence_strength": 9
    },
    {
      "title": "Add fixture-level provenance tags to assertion-grader output",
      "target": "atom",
      "target_path": "references/evals/atoms/assertion-grader.md",
      "rationale": "anthropics/skills tags every assertion with the fixture id + source line. Lets eval-log readers jump straight to the failing case.",
      "evidence": ["anthropics/skills/<path>"],
      "diff_sketch": "Edit Output section: add `provenance: {fixture_id, line}` to per-assertion record.",
      "fit_for_this_skill": 7,
      "novelty": 6,
      "evidence_strength": 6
    }
  ],
  "rejected": [
    {"candidate": "auto-bundled multi-skill plugin manifest", "reason": "out of scope — owned by `pluginize` skill"},
    {"candidate": "memory-augmented session loops", "reason": "out of scope — orthogonal to skill authoring"}
  ]
}
```

**What happens next** is the caller's call. A typical wiring:

1. Harness writes the JSON to `tmp/practice-drift-scan/<date>.json`
2. Opens a PR with the proposals as a checklist in the body
3. Maintainer ticks off proposals to accept; rejected ones get a one-line note in the PR for the next scan to dedup against

## Triggering — out of scope

The atom describes *what to do*, not *when*. Wiring is the caller's choice:

- GitHub Action (`workflow_dispatch` + `cron`)
- Claude Code `/schedule` or `/loop`
- `Stop` hook in `settings.json` that fires after sessions in the skill's repo
- Manual: a maintainer runs the atom on demand

Each path supplies its own `sources` list — typically pinned in a config file
the harness reads (so the atom stays portable and the source list stays in
version control).

## Common mistakes

- **Hardcoding sources inside the atom.** The whole point is portability —
  the atom must accept any source list. If you find yourself writing default
  URLs into the procedure, move them into the caller's config.
- **Auto-applying proposals.** Output is advisory. A proposal that survives
  dedup can still be a bad fit; require a human PR or an `acceptance-gate`
  run before anything is written.
- **Skipping dedup.** Without checking the existing inventory, the same
  proposal resurfaces every run and the output becomes noise.
- **Sourcing from a single channel.** One blog's recommendations become
  the skill's de facto roadmap. Mix at least two unrelated source types
  (e.g. official docs + a community repo).
- **Confusing popularity with fit.** A pattern can be widely adopted and
  still wrong for this skill's scope. Score `fit_for_this_skill` separately
  from `novelty` — high novelty + low fit is a reject.
- **Letting the proposer write the dedup judgment.** If the same agent
  proposes and dedups, novelty bias inflates the proposal count. Run the
  dedup pass with a fresh subagent or a deterministic check against the
  inventory listing.
