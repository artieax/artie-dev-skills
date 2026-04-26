# atom: static-score

| Type | Cost | Depends on |
|---|---|---|
| evaluator | low | — |

Pass the SKILL.md to a fresh Claude instance. Score 5 metrics, 0–10 each.

## When to add

**Foundational.** Almost every pipeline includes this — it's the cheapest signal of quality and the only atom usable on a draft that hasn't been executed yet.

## Inputs

- SKILL.md (full text)

## Output

```json
{
  "scores": {
    "trigger_precision": N,
    "workflow_coverage": N,
    "output_clarity": N,
    "red_flag_completeness": N,
    "dep_accuracy": N
  },
  "total": N,
  "top_improvement": "..."
}
```

## Prompt template

```
Evaluate the SKILL.md below. Score each metric 0–10 with a 1–2 sentence rationale.
Metrics: trigger_precision, workflow_coverage, output_clarity, red_flag_completeness, dep_accuracy.
Output as JSON with scores, total, and top_improvement.

=== SKILL.md ===
<paste>
```

## Common mistakes

- Scoring with a Claude instance that already saw the skill design discussion → biased toward generous scores.
- Treating `top_improvement` as optional. It's the input for the next iteration's focus.
