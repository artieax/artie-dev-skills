# atomic-builder (evals)

The default eval-pipeline mechanism. Every pipeline in this repo is built by selecting atoms from the [atom catalog](index.md#atom-catalog) and combining them — either as a [preset](index.md#presets--named-atom-combinations) or as a custom combination.

Atomic-builder runs in three steps: **EXTRACT → PICK → BUILD**. Past eval logs are optional — atomic-builder works from the catalog alone, and uses past logs to seed better defaults when they exist.

---

## When to use atomic-builder

**Always.** This is how eval pipelines are composed in this repo. The presets (`quick`, `executor`, `measured`, `diff`, `boundary`, `full`) are atom combinations expressed as shortcuts; atomic-builder is the underlying mechanism.

Two modes:

| Mode | Source of atoms | Trigger |
|---|---|---|
| **catalog** | `references/evals/atoms/*.md` | default — works without prior eval history |
| **history** | atoms whose past results matter for this skill type | repo has ≥ 5 eval records, or user says "based on past evals" / "履歴を参考に" |

History mode tunes the pick set for the kind of skill being evaluated (e.g. orchestrators benefit more from `collision-scan`; sandbox skills benefit more from `runtime-telemetry`). Catalog mode is the fallback.

---

## Pipeline steps

### 1. EXTRACT

Build the atom pool atomic-builder will draw from.

**Preset shortcut — skip EXTRACT and PICK entirely:**
If the user names a preset directly (`quick`, `executor`, `measured`, `diff`, `boundary`, `full`, `pre-runtime`) or if context makes the preset unambiguous, the composition is fully defined in [`index.md`](index.md). Go straight to BUILD. Do **not** read individual `atoms/*.md` files.

**Catalog mode (default):**
The pool is defined by the atom catalog table in [`index.md`](index.md). You already have the full catalog — no file reads needed. Only open individual `atoms/<name>.md` files when you need the implementation details of a specific atom not already described by `index.md`.

**History mode:**
Scan `data/evals.jsonl` for prior runs on similar skills, and rank atoms by signal-to-cost ratio (signals delivered per dollar of compute):

```
atomic-builder: EXTRACT data/evals.jsonl filter:archetype=<orchestrator|standard|...> tail:50
```

Read only the **last 50 records** that match the archetype filter — older runs add noise without improving signal. If the file exceeds 200 lines total, rotation may be pending (see [`../schedule.md`](../schedule.md#evals-rotation)).

Output: a ranked atom list with notes (`good` = high signal historically, `bad` = noisy / wasteful for this archetype).

### 2. PICK

Decide which atoms the eval needs.

**Required atoms:** every pipeline needs at least one **evaluator** or **runner**. In practice that means `static-score` (cheap, qualitative) or `independent-evaluator` (medium cost, behavioural).

**Dependent atoms:** some atoms require an upstream atom to have run. Honour the dependency table:

| Atom | Requires |
|---|---|
| `open-questions-log` | `independent-evaluator` |
| `assumptions-log` | `independent-evaluator` |
| `acceptance-gate` | `independent-evaluator` |
| `runtime-telemetry` | `independent-evaluator` |
| `regression-diff` | `static-score` on both versions |
| `hold-out` | `independent-evaluator` against hold-out fixtures |
| `convergence-check` (standard) | `static-score` |
| `convergence-check` (strict) | `open-questions-log` + `hold-out` |

**Shortcut:** if your pick set matches a preset's combination, name the preset instead — `quick`, `executor`, `measured`, `diff`, `boundary`, `full` are all atom combinations.

**History mode:** narrow the ranked pool to a focused set (5–8 atoms is plenty), keeping `good` atoms and dropping `bad` ones.

### 3. BUILD

Assemble the pipeline runner from the pick set:

```
atomic-builder: BUILD target=eval-pipeline name="<pipeline-name>"
```

The output is a runnable pipeline definition (the YAML form in [`index.md`](index.md#preset-definitions-yaml)). Run it, append the result to `references/eval-log.jsonl`, then iterate.

### Execution modes

Eval atoms that invoke an LLM (`independent-evaluator`, `static-score`, `adversarial`, `hold-out`) run via the same three modes as scaffold BUILD — full scaffold-side reference [`../scaffold/execution-modes.md`](../scaffold/execution-modes.md); pipeline stub [`../scaffold/atomic-builder.md`](../scaffold/atomic-builder.md#execution-modes).

| Mode | Best for in evals |
|---|---|
| **C. inline** (default) | one-off `quick` / `static-score` |
| **B. Task subagent** | `independent-evaluator` (the atom *requires* an independent agent session — Task subagent gives that for free, in background) |
| **A. subprocess** | CI gate runs, batch hold-out scoring |

Non-LLM atoms (`regression-diff`, `collision-scan`, `convergence-check`) are pure data — no mode choice needed.

---

## Examples

### Building a `quick` pipeline from the catalog

```
EXTRACT: catalog (atoms/*.md)
PICK:    static-score
BUILD:   pipelines.quick → run → eval-log.jsonl
```

### Building an `executor` pipeline with a regression guard

```
EXTRACT: catalog
PICK:    independent-evaluator + open-questions-log + assumptions-log + acceptance-gate + regression-diff
BUILD:   pipelines.executor-with-diff → run → eval-log.jsonl
```

### Building a custom pre-publish pipeline

```
EXTRACT: catalog
PICK:    static-score + independent-evaluator + acceptance-gate + adversarial + collision-scan
BUILD:   pipelines.pre-publish → run → eval-log.jsonl
```

### History-driven pick (orchestrator skill)

```
EXTRACT: data/evals.jsonl filter:archetype=orchestrator tail:50
         → top atoms: collision-scan (high), acceptance-gate (high),
           static-score (med), runtime-telemetry (low)
PICK:    collision-scan + acceptance-gate + static-score
BUILD:   pipelines.orchestrator-quick
```

---

## Why atoms (instead of fixed pipelines)

- **Composability.** A new eval need (e.g. "I want to check trigger-phrase length distribution") is one new atom file, not a fork of every preset.
- **Reviewability.** Each atom is a small markdown file with one job, one prompt, one output shape. Easy to read, easy to diff.
- **Cost-shape control.** Knowing every atom's cost lets you build cheap pre-iteration pipelines and expensive pre-merge pipelines from the same vocabulary.

The cost: presets become a coordination convention rather than a hardcoded list. That's the trade.
