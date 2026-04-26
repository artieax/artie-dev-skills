# atom: atomic-builder

Declares that this skill's core job is generating structured output by running **EXTRACT → PICK → BUILD** from a catalog of components (atoms, presets, or any domain-specific parts).

Add this atom when your skill *is* a builder — it receives a description and produces a draft by combining parts from a catalog, not when it merely scaffolds one thing as a one-off step.

## When to include

- The skill's primary output is a generated artifact assembled from a catalog of parts
- The skill needs to support both "catalog mode" (parts defined in files) and "exemplar mode" (parts extracted from existing high-scoring examples)
- The same scaffold mechanism will be reused or improved over time (optimized few-shots, evals)

Do **not** add this atom if the skill just calls `atomic-builder` once as a workflow step. This atom is for skills that *own* and *operate* the EXTRACT → PICK → BUILD pipeline themselves.

## What this atom adds

### Directories

```
skills/<name>/
├── SKILL.md
├── references/
│   └── scaffold/
│       ├── index.md            # catalog: parts table + presets
│       └── atoms/              # one .md per part
│           └── <part>.md
├── prompts/
│   ├── scaffold-system.md      # system frame for BUILD
│   └── scaffold-user.md        # user turn template for BUILD
└── data/
    └── optimized_prompt.json   # optional: few-shot demos injected at BUILD
```

### Execution modes

The skill must declare which execution mode(s) it supports. Inherit from [`execution-modes.md`](execution-modes.md) — Mode C (inline) is always the default; Modes B and A are opt-in.

## SKILL.md workflow pattern

```markdown
### 1. EXTRACT — build the part pool

**Preset shortcut:** if context makes the preset unambiguous, skip EXTRACT and PICK and go straight to BUILD.

**Catalog mode (default):**
Read `references/scaffold/index.md`. Open individual `atoms/<name>.md` only when you need the full implementation template.

**Exemplar mode:** (when repo has ≥ 2 high-scoring outputs, or user says "base it on existing X")
Pick 2–3 exemplars and extract parts:

```
atomic-builder: EXTRACT <path-to-exemplar-a>
atomic-builder: EXTRACT <path-to-exemplar-b>
```

Tag each extracted part `good` (amplify) or `bad` (invert).

### 2. PICK — select parts for this output

Required parts: [list the always-required parts for this skill's domain]

Optional parts: add based on the conditions in `references/scaffold/index.md`.

Narrow to a focused working set (target 5–10 parts). Name the preset if the combination matches one.

### 3. BUILD — generate the draft

```
atomic-builder: BUILD target=<output-file> for "<description>"
```

Read `prompts/scaffold-system.md` as the system frame.  
Render `prompts/scaffold-user.md` with the pick set and description.  
If `data/optimized_prompt.json` exists, inject few-shot examples.

The BUILD output is a first draft. Fill in domain-specific details, then run the eval pipeline before treating it as done.
```

## Catalog file conventions

`references/scaffold/index.md` must contain:

| Section | Contents |
|---|---|
| **Part catalog** | Table: part name → purpose → when to add |
| **Presets** | Named combinations of parts (at minimum: `minimal`) |

Individual `atoms/<part>.md` files follow: `when to include` → `layout or template` → `integration notes`.

## Optimized few-shot demos (optional)

If `data/optimized_prompt.json` exists, BUILD injects examples via the `scaffold-fewshot-item.md` template. Generate this file by running the optimization script or via the eval pipeline. Full lifecycle → [`execution-modes.md`](execution-modes.md#building-the-optimized-prompt-artifact).

## Dependency graph

If this skill calls `atomic-builder` (the scaffold meta-skill) as a subprocess, record the edge:

```
<this-skill> --> atomic-builder
```
