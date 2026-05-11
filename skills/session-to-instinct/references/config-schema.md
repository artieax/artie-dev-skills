# .instinct.yml — config schema

Both `session-to-instinct` and `instinct-to-harness` read the same config file.
Place it in the project root. User overrides go in `.instinct.local.yml` (gitignore this file).

Priority (highest wins): **CLI flags > `.instinct.local.yml` > `.instinct.yml` > built-in defaults**

---

## Vocabulary

The two skills share the **atom × preset pipeline** pattern. Same words, different roles per skill:

| word | session-to-instinct | instinct-to-harness |
|---|---|---|
| **atom** | extraction-method recipe (`failure-cluster`, `evaluator`, …) | rendering-recipe (`invariant-guard`, `kata`, …) |
| **target** | n/a | harness destination (`claude-path`, `cursor-mdc`, …) |
| **preset** | named bundle of extraction atoms | named bundle of harness targets (with rendering atom per target) |
| **instinct** | output: one `instincts/<slug>.md` per observation | input: read from sibling skill; output: variants under `instincts/<slug>/` |

---

## Minimal config (recommended starting point)

```yaml
# .instinct.yml
version: 1

extract:
  atoms:
    failure-cluster: { enabled: true,  algo: keyword,  weight: 1.0 }
    success-pattern: { enabled: true,  algo: semantic, weight: 0.7 }
    evaluator:       { enabled: true,                  weight: 1.2 }

emit:
  routes:
    rule:
      enabled: true
      targets: [claude-path]
      default_atom: invariant-guard
    skill:
      enabled: true
      targets: [skill-constraint]
      default_atom: kata
    doc:
      enabled: false
      targets: [agents-md]
      default_atom: story-arc

  targets:
    claude-path:       { enabled: true, default_atom: auto }
    skill-constraint:  { enabled: true, default_atom: auto }
```

---

## Full schema

```yaml
version: 1   # schema version; bump when breaking changes are introduced

# ── session-to-instinct ──────────────────────────────────────────────────────

extract:

  # Which extraction-method atoms are active. Keys must match files in atoms/.
  atoms:
    failure-cluster:
      enabled: true
      algo: keyword          # keyword | semantic | diff | llm | auto
      weight: 1.0            # relative weight when evaluator scores candidates
    success-pattern:
      enabled: false
      algo: semantic
      weight: 0.7
    head-start:
      enabled: false
      algo: llm              # head-start needs whole-session synthesis
      weight: 1.1            # high weight because rules generalize across sessions
    diff-outcome:
      enabled: false
      algo: diff
      weight: 0.5
    incident-driven:
      enabled: false
      algo: llm
      weight: 1.5
    evaluator:
      enabled: false
      weight: 1.2            # evaluator's own weight when merging multi-atom output
    human-curated:
      enabled: false         # pauses for REVIEW before BUILD
    dream-assisted:
      enabled: false         # reads existing instincts/*.md instead of raw sessions

  # Default algo when an atom has algo: auto or no algo set
  default_algo: keyword      # keyword | semantic | diff | llm

  # Promotion gate (applied at the end of EXTRACT before BUILD)
  promotion:
    auto_publish: false       # if true, skip REVIEW; instincts go straight to approved
    require_review: true      # show REVIEW prompt before BUILD (ignored if auto_publish)
    min_confidence: 0.0       # evaluator: drop candidates below this score (0.0 = keep all)
    min_support_count: 1      # evaluator: drop candidates with fewer session occurrences

  # Output — one markdown file per instinct under instincts/<slug>.md
  instincts_dir: null         # null = <skill-root>/instincts/
  rebuild_index: true         # auto-regenerate instincts.index.jsonl after each EXTRACT

# ── instinct-to-harness ──────────────────────────────────────────────────────

emit:

  # Provider gate — disable a whole AI vendor in one switch.
  # Each target file in instinct-to-harness/targets/ has a frontmatter `provider:` field.
  # Disabling a provider here drops every target tagged with that provider, regardless of
  # what emit.targets.<id>.enabled says.
  providers:
    claude:   { enabled: true }      # claude-path, claude-global
    cursor:   { enabled: false }     # cursor-mdc
    codex:    { enabled: false }     # agents-md
    gemini:   { enabled: false }     # gemini-md
    copilot:  { enabled: false }     # copilot-md
    any:      { enabled: true }      # vendor-agnostic: skill-constraint, system-prompt

  # High-level routing gate keyed by instinct.promotion_targets.
  # Decides whether instincts may be distributed to rules / docs / skills / security-rules at all.
  routes:
    rule:
      enabled: true
      targets: [claude-path]          # candidate harness targets when promotion_targets includes "rule"
      default_atom: invariant-guard   # rendering atom used at this route by default
    skill:
      enabled: true
      targets: [skill-constraint]
      default_atom: kata
    doc:
      enabled: false
      targets: [agents-md, gemini-md]
      default_atom: story-arc
    security-rule:
      enabled: false
      targets: [claude-global]
      default_atom: invariant-guard
    consolidation:
      enabled: true                   # reserved route for dream-assisted output
      targets: []                     # MUST stay empty: consolidation produces no harness emission
      default_atom: null              # rendering atoms do not apply

  # Per-target enablement and rendering atom defaults.
  # default_atom wins over the route default; use auto to fall back to instinct.best_preset.
  targets:
    claude-path:       { enabled: true,  default_atom: auto }
    claude-global:     { enabled: false, default_atom: auto }
    cursor-mdc:        { enabled: false, default_atom: auto }
    agents-md:         { enabled: false, default_atom: auto }
    gemini-md:         { enabled: false, default_atom: auto }
    copilot-md:        { enabled: false, default_atom: anti-pattern-gallery }
    skill-constraint:
      enabled: false
      default_atom: auto         # polarity-aware: never/bad → invariant-guard, good → kata
      target_skill: null         # default <target-skill> when an instinct has no per-instinct target_skill
    system-prompt:     { enabled: false, default_atom: kata }

  # BROADCAST without --targets uses this list (must be a subset of enabled targets)
  broadcast_targets: [claude-path]

  # When true, an explicit CLI --target may bypass a disabled route.
  # Default false = config remains the safety rail unless implementation exposes an override flag.
  allow_route_override: false

  # Overwrite an existing external harness file at DEPLOY time without --force
  allow_overwrite: false
```

---

## Named presets

Each skill has its own preset registry, so the config exposes **two** preset keys:

```yaml
# .instinct.yml
version: 1

extract:
  preset: standard          # session-to-instinct preset (extraction atoms)

emit:
  preset: standard          # instinct-to-harness preset (harness targets)
```

A top-level `preset:` is also accepted as a shorthand that fans out to both —
**but only when the same preset id exists in both registries** (`minimal`, `standard`,
`broadcast`). Names that exist on only one side (`safe`, `research` — extract-only)
must be set under `extract.preset` explicitly; loaders must error out when a
top-level `preset:` references a name missing from either registry.

```yaml
# Shorthand: applies to both extract and emit
version: 1
preset: standard

# Mixed: extract uses safe (extract-only), emit uses minimal
version: 1
extract:
  preset: safe
emit:
  preset: minimal
```

### session-to-instinct presets (defined in `presets/<id>.md`)

| preset | atoms enabled | typical emit |
|---|---|---|
| `minimal` | `failure-cluster` (keyword) | `claude-path` |
| `standard` | `failure-cluster` + `success-pattern` + `evaluator` | `claude-path` + `skill-constraint` |
| `broadcast` | same as `standard` | all common targets |
| `safe` | `failure-cluster` + `incident-driven` + `human-curated` | `claude-path` only |
| `research` | all atoms except `human-curated` | `claude-path` + `agents-md` + `gemini-md` |

### instinct-to-harness presets (defined in `instinct-to-harness/presets/<id>.md`)

| preset | targets bundled |
|---|---|
| `minimal` | `claude-path` |
| `standard` | `claude-path` + `skill-constraint` |
| `broadcast` | claude-path + cursor-mdc + agents-md + gemini-md + copilot-md + skill-constraint |

A preset key is overridden field-by-field by anything else in the same file.
Presets implicitly enable the targets they bundle (`emit.targets.<id>.enabled: true`)
even when the full schema example below shows that field as `false`; that example
documents the *built-in defaults* before any preset is applied.

```yaml
version: 1
extract:
  preset: standard            # start from standard (extraction)
  atoms:
    evaluator:
      weight: 2.0             # override just this field
emit:
  preset: standard            # start from standard (emit)
  routes:
    doc:
      enabled: true
      targets: [agents-md]
      default_atom: story-arc
  targets:
    cursor-mdc:
      enabled: true
      default_atom: decision-table   # add cursor-mdc on top of standard
```

---

## .instinct.local.yml (user override)

Same schema as `.instinct.yml`. Merged on top after the project config is loaded.
Intended for personal algo preferences or enabling atoms not shared with the team.

```yaml
# .instinct.local.yml  ← gitignore this
extract:
  default_algo: llm           # personal preference: always use llm
  promotion:
    min_confidence: 0.85      # stricter gate than team default
```

---

## Resolution example

Given:
```yaml
# .instinct.yml
preset: minimal              # shorthand: applies to both extract and emit
extract:
  atoms:
    success-pattern: { enabled: true }
```
```yaml
# .instinct.local.yml
extract:
  default_algo: llm
```

Resolved:
- `failure-cluster`: enabled (from minimal), algo `llm` (local override of default), weight 1.0
- `success-pattern`: enabled (added on top of minimal), algo `llm`
- all other extraction atoms: disabled
- emit `claude-path`: enabled (minimal default)
- `default_algo`: `llm` (local override)

---

## Resolution rules

### Extraction (session-to-instinct)

For each candidate atom listed in `extract.atoms`:

1. Start from the preset's atom set (if `preset:` is set)
2. Override per-atom fields from `.instinct.yml > extract.atoms.<id>`
3. Override per-atom fields from `.instinct.local.yml > extract.atoms.<id>`
4. CLI flags (`--atoms a,b,c`, `--algo X`) win last

Per-atom algo resolution:
1. CLI `--algo`
2. `extract.atoms.<id>.algo`
3. `extract.default_algo`
4. atom file's `default_algo` field
5. log-shape auto-detect (`@@` → diff; > 10 KB → llm; else keyword)

### Emit (instinct-to-harness)

**Canonical precedence — both this document and `instinct-to-harness/SKILL.md` MUST follow this order verbatim.**

For each instinct entering EMIT, the target set is computed in exactly these steps:

1. **Source list** — pick the highest-priority source that exists:
   1. CLI `--targets <list>` (explicit override)
   2. CLI `--preset <name>` → preset's `targets:`
   3. `emit.preset` in `.instinct.yml` → preset's `targets:`
   4. Top-level `preset:` shorthand → preset's `targets:`
   5. Instinct's `promotion_targets` → expand each through `emit.routes.<promotion-target>.targets` (skip routes where `enabled: false`, unless `emit.allow_route_override: true` and CLI `--target` overrides)
2. **Preset auto-enable** — if (1) chose a preset, that preset's `providers:` and bundled targets are flipped to `enabled: true` for the duration of this run unless the user overrides them after the `preset:` line in `.instinct.yml`.
3. **Per-instinct route filter** — when source (1) was a preset (sources 2–4) or CLI `--targets` (source 1), intersect the target set with the routes the instinct allows: `expand(instinct.promotion_targets) via emit.routes.<pt>.targets`. This stops `preset: standard` from emitting `skill-constraint` for an instinct whose `promotion_targets` is `[rule]` only. Source 5 (`promotion_targets`) is already route-correct and is not re-filtered.

   **Route-mismatch handling for explicit CLI targets:** if a CLI `--target`/`--targets` names a target the filter would drop (i.e. the instinct's `promotion_targets` does not route to it), the run **hard-errors** with an explicit message unless `emit.allow_route_override: true`. When `allow_route_override: true`, the named CLI target is unioned back in **for that one instinct only** and continues through gates 4–5; presets and `emit.targets` defaults are NOT unioned in by `allow_route_override` — only the CLI-named target.
4. **Provider gate**:
   - If CLI `--provider <list>` is set, keep only targets whose `provider:` matches the list. `provider: any` targets are NOT auto-included; pass `any` in the list (`--provider claude,any`) to keep them.
   - Otherwise, drop targets where `emit.providers.<provider>.enabled: false`. `provider: any` targets follow `emit.providers.any.enabled`.
5. **Per-target enablement** — drop targets where `emit.targets.<target>.enabled: false` (after step 2's preset auto-enable).
6. **Final set** — what survives steps 1–5 is the emission set for this instinct.

CLI `--target <id>` is a *post-hoc* override that bypasses step 1 only when `emit.allow_route_override: true`; it still passes through the provider and per-target gates (steps 4–5).

Per-target rendering-atom resolution:
1. CLI `--atom`
2. `emit.targets.<target>.default_atom`
3. `emit.routes.<promotion-target>.default_atom`
4. instinct's `best_preset`
5. heuristic fallback (see `instinct-to-harness/SKILL.md`)
