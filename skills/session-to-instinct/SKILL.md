---
name: session-to-instinct
description: 'Read AI coding session logs and extract instincts using a catalog of pluggable extraction-method atoms; presets bundle the atoms into recipes for different use cases.'
author: '@artieax'
---

# session-to-instinct

Read raw AI coding session logs (Claude Code, Cursor, OpenCode, …) and turn each session into a set of **instincts** — structured observations stored as one markdown file per instinct.

The skill follows the **atom × preset pipeline** pattern:

- **atoms/** — extraction-method recipes; each `atoms/<id>.md` describes one way to read a session (failure-cluster, success-pattern, evaluator, …)
- **presets/** — named bundles of atoms; each `presets/<id>.md` declares which atoms to run together (`minimal`, `standard`, `safe`, …)
- **instincts/** — output; one `instincts/<slug>.md` per extracted observation

You pick a preset (or list atoms manually), choose an algo per atom (`keyword` / `semantic` / `diff` / `llm`), and the pipeline runs `EXTRACT → PICK → BUILD` to produce instincts.

## When to use

- "Extract instincts from this session"
- "Run preset standard on last night's batch"
- "EXTRACT --atoms failure-cluster,success-pattern --algo llm"
- "Turn these Claude Code sessions into rules"
- "What patterns came out of today's work?"

**Do not trigger** when:
- The user wants to convert an existing instinct into a harness file (use `instinct-to-harness`)
- The user wants to write a rule directly without going through sessions
- The request is to view or search existing instincts, not produce new ones

---

## Catalog

### Atoms — the extraction-method building blocks (`atoms/`)

| atom | reads | natural output | when to use |
|---|---|---|---|
| [`failure-cluster`](atoms/failure-cluster.md) | error lines, retries, "don't"/"never" | `polarity: never` instinct → `rule` | learn from failure |
| [`success-pattern`](atoms/success-pattern.md) | smooth flows, zero-correction sequences | `polarity: good` instinct → `skill` | learn from success |
| [`head-start`](atoms/head-start.md) | whole-session retrospect — "what rule at msg 1 would have shortened this?" | session-agnostic rule → `rule` + `doc` | recurring sessions that re-learn the same thing |
| [`diff-outcome`](atoms/diff-outcome.md) | diff statistics only (content-blind) | guideline → `doc` | privacy-sensitive sessions |
| [`incident-driven`](atoms/incident-driven.md) | secrets, destructive commands, near-misses | `polarity: never` → `security-rule` | high-severity events only |
| [`evaluator`](atoms/evaluator.md) | candidate instincts from other atoms | scored survivors | filter noise before commit |
| [`human-curated`](atoms/human-curated.md) | candidates + human review | accepted instincts only | initial rollout, calibration |
| [`dream-assisted`](atoms/dream-assisted.md) | existing `instincts/*.md` (NOT sessions) | merged / retired entries | periodic pool maintenance |
| [`ideal-gap`](atoms/ideal-gap.md) | session log — decision points vs. hypothetical superior model | `polarity: bad/never` instinct → `rule` + `doc` | extract capability ceiling deltas; what a better model would have done |

Each atom file documents its inputs, outputs, best-paired algo, and anti-patterns. Read the atom file directly for details.

### Presets — named bundles of atoms (`presets/`)

| preset | atoms bundled | emit targets |
|---|---|---|
| [`minimal`](presets/minimal.md) | `failure-cluster` | `claude-path` |
| [`standard`](presets/standard.md) | `failure-cluster` + `success-pattern` + `evaluator` | `claude-path` + `skill-constraint` |
| [`broadcast`](presets/broadcast.md) | same as standard | all common targets |
| [`safe`](presets/safe.md) | `failure-cluster` + `incident-driven` + `human-curated` | `claude-path` only |
| [`research`](presets/research.md) | all atoms except `human-curated` | `claude-path` + `agents-md` + `gemini-md` |

A preset is just a markdown file that lists atoms; users can add new presets by dropping a file into `presets/`.

### Algos — extraction techniques (parameter, not an atom)

| id | technique | speed | best for |
|---|---|---|---|
| `keyword` | regex + keyword scan | fast | quick triage, large batches |
| `semantic` | sentence clustering + polarity scoring | medium | mixed-topic sessions |
| `diff` | parse diff hunks; infer intent from prose | fast | code-heavy sessions |
| `llm` | full LLM pass | slow | high-value or ambiguous sessions |

Algos are orthogonal to atoms: any atom can run with any compatible algo. Each atom file lists its `default_algo`.

---

## Pipeline

```
session log(s)
      │
      ▼  Phase 1: EXTRACT
   resolved atom set    ← from --preset, --atoms, or .instinct.yml
   per-atom algo        ← per-atom default, --algo override, or auto-detect
      │
      ▼  Phase 2: PICK
   per-instinct fields  ← best_preset (rendering atom), promotion_targets, review_status
      │
      ▼  Phase 3: BUILD
   instincts/<slug>.md  ← one markdown file per instinct (frontmatter + body)
```

### Phase 1 — EXTRACT

1. Resolve which atoms to run. Order: `--atoms <list>` > `--preset <name>` > `extract.preset` in `.instinct.yml` > top-level `preset:` shorthand > default `minimal`.
2. For each atom, resolve its algo. **Canonical precedence — must match `references/config-schema.md → "Per-atom algo resolution"` verbatim**:
   1. CLI `--algo`
   2. `extract.atoms.<id>.algo` (per-atom config)
   3. `extract.default_algo` (project-wide default)
   4. atom file's `default_algo` field
   5. log-shape auto-detect (see rules below)
3. Run each atom; collect raw observations into an in-memory candidate pool.

Auto-detect rules when no algo is set anywhere:
- Log contains `@@` / `> diff` markers → `diff`
- Log > 10 KB and no diff markers → `llm`
- Otherwise → `keyword`

### Phase 2 — PICK

For each candidate, fill in:

- `best_preset` — which **rendering** atom from `instinct-to-harness/atoms/` will render best (`invariant-guard`, `decision-table`, …). Heuristics:
  1. `polarity: never/bad` → prefer `invariant-guard` or `symptom-cause-fix`
  2. Corrective has NG/OK code → `kata` or `anti-pattern-gallery`
  3. 3+ branches in corrective → `decision-table` or `escalation-ladder`
  4. Background-heavy → `story-arc`
  5. Two approaches compared → `when-dont-when`
- `promotion_targets` — derived from the source extraction atom + polarity (table below)
- `review_status` — `pending` unless `extract.promotion.auto_publish: true` in config

| extraction atom | polarity | promotion_targets |
|---|---|---|
| `failure-cluster` | never / bad | `[rule]` |
| `success-pattern` | good | `[skill]` |
| `head-start` | any (must generalize) | `[rule, doc]` |
| `diff-outcome` | any | `[doc]` |
| `incident-driven` | never | `[rule, security-rule]` |
| `evaluator` | any | inherited from child atom |
| `human-curated` | any | human selects at review time |
| `dream-assisted` | any | `[consolidation]` |
| `ideal-gap` | bad / never | `[rule, doc]` |

If `evaluator` is in the run, candidates pass through it next: it scores precision / coverage / annoyance and drops survivors below `min_confidence` / `min_support_count`.

### Phase 3 — BUILD

Each survivor is written as one markdown file: `instincts/<slug>.md`.

```
<skill-root>/session-to-instinct/
├── SKILL.md
├── atoms/                  ← extraction-method catalog (atoms above)
├── presets/                ← named atom bundles
├── instincts/              ← OUTPUT of this skill (one .md per observation)
│   ├── git-sequential-commits.md
│   ├── macos-bash-gotchas.md
│   └── …
├── reviews/                ← append-only review history per instinct
│   ├── git-sequential-commits.md
│   ├── macos-bash-gotchas.md
│   └── …
├── instincts.index.jsonl   ← optional auto-generated index of frontmatter
└── references/
```

`instincts/` is the source of truth for observations; `reviews/` is the source of truth for the audit trail (who said what about each instinct, when, and why). Both regenerate cleanly into `instincts.index.jsonl` via `STATUS --rebuild-index`.

#### Instinct file format

```markdown
---
id: <uuid-v4>
slug: <kebab-case>            # filename = instincts/<slug>.md
session_id: <session-hash>
source_atom: failure-cluster | success-pattern | head-start | diff-outcome | incident-driven | evaluator | human-curated | dream-assisted
domain: <git | chrome-mcp | svelte | bash | …>
polarity: never | bad | good
best_preset: invariant-guard | decision-table | symptom-cause-fix | kata | anti-pattern-gallery | escalation-ladder | story-arc | when-dont-when
enforcement_mode: rule | script | hook | null
path_scope: <glob or null>
tags: [tag1, tag2]
signals:
  confidence: null            # set by evaluator atom
  support_count: 1
candidate_actions: []
promotion_targets: [rule, skill, doc, security-rule, consolidation]
                              # one or more of the enum values; instinct-to-harness expands each through emit.routes.<value>
                              # `consolidation` is reserved for dream-assisted output and produces no harness emission
target_skill: null            # required when promotion_targets includes "skill"; resolves <target-skill> for skill-constraint deploy
review_status: pending | approved | rejected | deferred
last_reviewed_at: null        # mirrors the latest entry in reviews/<slug>.md
last_reviewer: null           # name | atom-id | "auto"; mirrors reviews/<slug>.md
extracted_at: <ISO-8601>

# Harness state — written ONLY by instinct-to-harness BUILD / DEPLOY.
# Source-of-truth for "has this already been turned into a harness file?"
harness:
  built:    []                  # target ids that have variants in instinct-to-harness/instincts/<slug>/variants/
  deployed: []                  # target ids actually placed at external paths
  last_emitted_at: null
  last_deployed_at: null
---

# <one-line title>

## Context
Where and what task triggered this.

## Trigger
What caused this behaviour.

## Observation
What happened.

## Consequence
What resulted.

## Corrective
What to do instead. *(only for `polarity: never | bad`)*
```

#### Slug rules

- `<domain>-<short-summary>`, kebab-case, ≤ 50 chars
- Stable: never renamed after first BUILD (instinct-to-harness keys on it)
- Collision: append `-2`, `-3`, … until unique

#### Append-only & dedup

- Files in `instincts/` are append-only — to retire, set `review_status: rejected`; never delete
- Duplicate check before writing: same `session_id` + normalised observation
- Override directory: `--instincts-dir <path>`

---

## Review history (`reviews/<slug>.md`)

Every REVIEW or EVAL action appends an entry to `reviews/<slug>.md`. The instinct's `review_status` field always holds the latest verdict (for fast filtering); the review file holds the *reasoning* — comments, evaluator scores, deferral notes, suggested edits.

### Review file format

```markdown
---
slug: git-sequential-commits
latest_verdict: approved | pending | rejected | deferred
review_count: 3
last_reviewed_at: <ISO-8601>
last_reviewer: <name | atom-id | "auto">
---

# Review history — git-sequential-commits

## 2026-05-09T10:00:00Z — approved (nyanko)
Confirmed in two further sessions today. Approving with no edits.
Action: set review_status: approved.

## 2026-05-08T14:00:00Z — deferred (evaluator)
signals.confidence=0.61, signals.support_count=2 — below min_confidence 0.78.
Defer until more supporting sessions accumulate.

## 2026-05-08T09:00:00Z — pending (auto)
Initial extraction by failure-cluster atom from session 5c7c3eb.
No human review yet.
```

### Entry rules

- **Append-only**: never delete or rewrite past entries — review history is the audit trail
- **Newest entry first** in the body (most recent at top, oldest at bottom)
- Frontmatter mirrors the *latest* entry only; older verdicts live in the body
- One entry per REVIEW / EVAL action; never batch silently
- The same `last_reviewed_at` value goes into both this file's frontmatter AND the source instinct's `review_status` change

### When entries are written

| trigger | reviewer | typical verdict |
|---|---|---|
| Initial EXTRACT | `auto` | `pending` |
| `EVAL` command (evaluator atom) | `evaluator` | `pending` / `deferred` / `approved` (if auto_publish) |
| `REVIEW` command (human) | user name | `approved` / `rejected` / `deferred` |
| `human-curated` atom inline review | user name | `approved` / `rejected` |
| `DREAM` consolidation | `dream-assisted` | `rejected` (with merge note pointing at survivor slug) |

### How instinct-to-harness uses the review file

instinct-to-harness reads `reviews/<slug>.md` only to display context during EMIT (e.g. show recent verdicts when prompting the user). It never writes to it.

---

## Config (`.instinct.yml`)

The config selects atoms, algos, and presets. Full schema → [`references/config-schema.md`](references/config-schema.md).

```yaml
version: 1
preset: standard          # named bundle from presets/

extract:
  atoms:                  # override atoms inside the preset
    failure-cluster: { algo: llm, weight: 1.0 }
    success-pattern: { algo: semantic, weight: 0.7 }
    evaluator:       { weight: 1.2 }
  promotion:
    auto_publish: false
    require_review: true
    min_confidence: 0.78
    min_support_count: 5
```

Priority: **CLI flags → `.instinct.local.yml` → `.instinct.yml` → defaults**

---

## Commands

| Command | Description |
|---|---|
| `EXTRACT [--preset X \| --atoms a,b,c] [--algo Y] --input <path>` | Full pipeline → writes `instincts/<slug>.md` |
| `EXTRACT --dry-run` | Show what would be written; no file changes |
| `PREVIEW` | Show classified candidates before BUILD |
| `LIST` | List instincts with key frontmatter fields |
| `LIST --emitted` | List only instincts whose `harness.built` is non-empty |
| `LIST --unemitted` | List only instincts with `review_status: approved` and empty `harness.built` |
| `LIST --undeployed` | Built but not yet deployed (`harness.built` non-empty, `harness.deployed` smaller) |
| `SHOW <slug>` | Print `instincts/<slug>.md` |
| `EVAL` | Run `evaluator` atom over pending instincts; updates `signals.*` and appends an entry to `reviews/<slug>.md` |
| `REVIEW` | Walk pending instincts; user sets `review_status`; appends a human entry to `reviews/<slug>.md`. When the `human-curated` atom is enabled in `extract.atoms`, this command is its execution point (the atom does not run during EXTRACT — see `atoms/human-curated.md`) |
| `REVIEW LOG <slug>` | Print the review history for one instinct |
| `REVIEW NOTE <slug> --comment "..."` | Append a free-form review note without changing `review_status` |
| `STATUS` | Counts by domain / polarity / source_atom / preset |
| `STATUS --rebuild-index` | Regenerate `instincts.index.jsonl` |
| `DEDUPE` | Report near-duplicates (no delete) |
| `DREAM` | Run `dream-assisted` atom over the pool |

---

## Output

```
session-to-instinct — EXTRACT complete
preset: standard
atoms run: failure-cluster (keyword), success-pattern (semantic), evaluator
input: session.md  |  instincts written: 7  |  review_status: pending
domains: git(3), bash(2), svelte(2)
polarity: never(4), bad(2), good(1)
next: REVIEW → instinct-to-harness to emit
```

---

## Red flags

**Always:**
- Start from a preset (`minimal` or `standard`) before composing atoms by hand
- Run `STATUS` before bulk extraction — know what already exists
- Include the `evaluator` atom whenever running multiple extraction atoms — it filters noise
- Set `enforcement_mode` accurately: `script`/`hook` instincts need automation, not just rules

**Never:**
- Delete files in `instincts/` to retire — set `review_status: rejected` instead
- Delete or rewrite past entries in `reviews/<slug>.md` — review history is append-only audit trail
- Hand-edit `instincts.index.jsonl` — auto-generated; use `STATUS --rebuild-index`
- Rename a `slug` after first BUILD — instinct-to-harness keys on it; `reviews/<slug>.md` does too
- Use `--algo keyword` on sessions > 30 KB — switch to `llm`
- Merge multiple sessions into a single instinct
- Skip the `evaluator` atom on batch extractions — unfiltered noise degrades downstream quality
- Change `review_status` in instinct frontmatter without writing a corresponding entry to `reviews/<slug>.md` — they must stay in sync

---

## Requirements

- Resolves atoms from `--atoms` / `--preset` / config in that priority order `MUST`
- Each atom under `atoms/` is documented in its own markdown file `MUST`
- Each preset under `presets/` is documented in its own markdown file `MUST`
- Writes one markdown file per instinct under `instincts/<slug>.md` `MUST`
- Frontmatter includes `id`, `slug`, `session_id`, `source_atom`, `domain`, `polarity`, `best_preset`, `promotion_targets`, `review_status`, `harness` `MUST`
- Every change to `review_status` appends a corresponding entry to `reviews/<slug>.md` `MUST`
- `reviews/<slug>.md` is append-only; past entries are never deleted or rewritten `MUST`
- Slug is stable: never changes after first BUILD `MUST`
- Selects algo automatically when neither flag nor atom default is set `SHOULD`
- Runs duplicate check before writing `SHOULD`
- Maintains regenerable `instincts.index.jsonl` `SHOULD`
- Supports `--dry-run` `SHOULD`
- Multi-atom config via `.instinct.yml` with per-atom weights `MAY`
