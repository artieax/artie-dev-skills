# atomic-builder

The default scaffold mechanism. Every skill in this repo is built by selecting atoms from the [atom catalog](index.md#atom-catalog) and combining them — either as a [preset](index.md#presets--named-atom-combinations) or as a custom combination.

Atomic-builder runs in three steps: **EXTRACT → PICK → BUILD**. Exemplar skills are optional — atomic-builder works from the catalog alone, and uses exemplars to seed higher-quality drafts when they exist.

---

## When to use atomic-builder

**Always.** This is how skills are scaffolded in this repo. The presets and archetypes are atom combinations expressed as shortcuts; atomic-builder is the underlying mechanism.

Two modes:

| Mode | Source of atoms | Trigger |
|---|---|---|
| **catalog** | `references/scaffold/atoms/*.md` | default — works without exemplars |
| **exemplar** | atoms extracted from existing high-scoring skills | repo has ≥ 2 skills scoring ≥ 35/50, or user says "based on existing skills" / "参考にして作って" |

Exemplar mode amplifies what already works in this repo. Catalog mode is the fallback (and the bootstrap when the repo has no high-scoring skills yet).

---

## Pipeline steps

### 1. EXTRACT

Build the atom pool atomic-builder will draw from.

**Preset shortcut — skip EXTRACT and PICK entirely:**
If the user names a preset directly (`minimal`, `standard`, `scripts`, `split`) or if context makes the preset unambiguous, the composition is fully defined in [`index.md`](index.md). Go straight to BUILD. Do **not** read individual `atoms/*.md` files.

**Catalog mode (default):**
The pool is defined by the atom catalog table in [`index.md`](index.md). You already have the full catalog — no file reads needed. Only open individual `atoms/<name>.md` files when you need the implementation template of a specific atom not already described by `index.md`.

**Exemplar mode:**
Pick 2–3 high-scoring exemplar skills and extract atoms from each:

```
atomic-builder: EXTRACT skills/<exemplar-a>/SKILL.md
atomic-builder: EXTRACT skills/<exemplar-b>/SKILL.md
```

Focus extraction on: trigger precision, workflow structure, red flag patterns, output format clarity. Tag each extracted atom as `good` (keep) or `bad` (invert / avoid).

### 2. PICK

Decide which atoms the new skill needs.

**Required atoms:** every skill needs the six content atoms (`frontmatter` + `trigger` + `workflow` + `redflag` + `output` + `requirements`).

**Structural atoms:** add based on the conditions in the [atom catalog](index.md#atom-catalog).

**Shortcut:** if your pick set matches a preset's combination, name the preset instead — `minimal`, `standard`, `scripts`, `split` are all atom combinations.

**Exemplar mode:** narrow the extracted pool to a focused working set (target 5–10 atoms), including `good` atoms to amplify and `bad` atoms to invert.

### 3. BUILD

Generate the SKILL.md draft from the pick set:

```
atomic-builder: BUILD target=SKILL.md for "<new-skill-name>"
```

The BUILD output is a first draft. Fill in skill-specific details, then run the `quick` eval pipeline before treating it as done.

---

## Execution modes

BUILD always uses the same prompt files; only the **runner** changes (inline vs subagent vs subprocess). Summary table, host matrix, Mode A/B/C call patterns, and `optimized_prompt.json` lifecycle → [`execution-modes.md`](execution-modes.md).

## Optimized few-shot demos (optional)

If `data/optimized_prompt.json` exists, BUILD injects few-shot examples via `prompts/scaffold-fewshot-item.md`. If it does not exist, BUILD falls back to catalog atoms only. **When to generate the file, eval thresholds, and subprocess command** → [`execution-modes.md`](execution-modes.md#building-the-optimized-prompt-artifact).

---

## Examples

### Building a `minimal` skill from the catalog

```
EXTRACT: catalog (atoms/*.md)
PICK:    frontmatter + trigger + workflow + redflag + output + requirements
BUILD:   skills/<name>/SKILL.md
```

### Building a `standard` skill with an exemplar

```
EXTRACT: skills/bommit/SKILL.md (score 38/50)
PICK:    frontmatter + trigger + workflow + redflag + output + requirements + references-dir
         + good atoms: bommit's trigger.do_not_trigger, bommit's output.format
BUILD:   skills/<name>/SKILL.md + references/eval-log.jsonl
```

### Building an orchestrator pipeline

```
EXTRACT: catalog
PICK:    orchestrator (parent) + 3 × child-skill (each is its own minimal/standard combination)
BUILD:   skills/<name>/ + skills/<name>-phase-a/ + skills/<name>-phase-b/ + skills/<name>-phase-c/
```
