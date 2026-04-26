# atom: description-optimization

| Type | Cost | Depends on |
|---|---|---|
| optimizer | medium | none (operates on SKILL.md frontmatter only) |

Tune the `description` field in the SKILL.md frontmatter to maximize **trigger
precision** against a 20-query eval set. Inspired by Anthropic's official
`skill-creator` description optimization loop.

The atom is a *pre-runtime* optimizer — it changes only the `description`
field, never the workflow. Improvements here directly affect routing: a tighter
description avoids both undertriggering (Claude misses real cases) and
overtriggering (Claude routes adjacent-skill queries here).

## When to add

- `trigger_precision` < 8/10 in `static-score`
- After adding/removing trigger phrases in `## When to use`
- After a `collision-scan` flagged overlap with another skill — fixing the
  description here avoids re-running the boundary tightening loop later
- Before publishing — last cheap win on routing accuracy

## Inputs

- `SKILL.md` (frontmatter `description` field)
- `data/trigger_eval_set.json` — 20-query eval set:
  - 10 with `should_trigger: true`
  - 10 with `should_trigger: false`
  - If absent, the optimizer **generates one from the SKILL.md** (cached for reuse)

## Pipeline

```
1. Generate eval set (if missing) ─→ prompts/eval-set-gen.md (20 queries)
2. Score current description       ─→ prompts/trigger-judge.md per query
3. Generate N variants             ─→ prompts/description-variant.md
4. Score each variant
5. Pick best (max accuracy; tie-break by closeness to current)
6. Write data/optimized_description.json
```

## Output

`data/optimized_description.json`:

```json
{
  "current": {
    "description": "Create, iterate, evaluate, and improve agent skills ...",
    "accuracy": 0.80,
    "false_positives": ["create a new repo", "make a new branch"],
    "false_negatives": ["scaffold a skill that does X"]
  },
  "best": {
    "description": "Create, scaffold, iterate, and evaluate agent skills end-to-end ...",
    "accuracy": 0.95,
    "false_positives": [],
    "false_negatives": ["foo"]
  },
  "n_variants_tried": 8,
  "all_history": [ /* every variant + score */ ]
}
```

## Run

`optimize_description.py` is a *shared* tool that lives at
`skills/skill-builder/scripts/`. Target skills don't ship their own copy —
always invoke it via its shared path and pass `--skill-root`.

```bash
# From the target skill root
cd skills/<name>/
python ../skill-builder/scripts/optimize_description.py --skill-root .                  # 8 variants, default model
python ../skill-builder/scripts/optimize_description.py --skill-root . --variants 12
python ../skill-builder/scripts/optimize_description.py --skill-root . \
    --eval-set ./data/trigger_eval_set.json
python ../skill-builder/scripts/optimize_description.py --skill-root . --apply          # write best back to SKILL.md

# Or from the repo root
python skills/skill-builder/scripts/optimize_description.py --skill-root skills/<name>
python skills/skill-builder/scripts/optimize_description.py --skill-root skills/<name> --apply
```

`--apply` overwrites the `description:` line in the SKILL.md frontmatter.
Always review the diff before committing.

## Common mistakes

- **Generating the eval set with the same agent that wrote the SKILL.md.** The
  set will inherit the author's blind spots. Use a fresh subagent (Mode B), or
  generate it on a different host.
- **Too few variants.** 4–6 is the floor; 8–12 gives stable winners. Below 4 the
  best-of-N is essentially "current vs. one challenger" — high variance.
- **Optimizing on a single fixture's accuracy.** Always run on the full 20.
  100% on 5 queries is not trustworthy.
- **Auto-applying without review.** Description changes affect routing
  globally — diff and read the new description before merging.
