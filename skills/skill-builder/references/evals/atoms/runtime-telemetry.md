# atom: runtime-telemetry

| Type | Cost | Depends on |
|---|---|---|
| observer | low | `independent-evaluator` |

Collect execution observables (the agent equivalent of APM telemetry) as quantitative signals on skill quality. Gathered during `independent-evaluator` runs (for example via the Deno sandbox runner).

## When to add

When you want **quantitative** signals on top of the qualitative ones from `open-questions-log` and `assumptions-log`. Useful before declaring a skill production-ready.

## Output

```json
{
  "tool_uses": 5,
  "duration_ms": 12400,
  "total_tokens": 3200,
  "retry_count": 1,
  "signals": [
    "tool_uses=5 (threshold 3): SKILL.md may lack concrete references",
    "retry_count=1: at least one instruction required clarification"
  ]
}
```

## Thresholds

| Metric | Target | Signal when exceeded |
|---|---|---|
| `tool_uses` | ≤ 3 | SKILL.md lacks references; agent had to search |
| `duration_ms` | baseline ± 20% | Agent was uncertain or over-elaborated |
| `total_tokens` | baseline ± 25% | Prompt underspecified; agent inferred heavily |
| `retry_count` | 0 | An instruction was ambiguous enough to require a redo |

## Common mistakes

- Treating high `tool_uses` as a good thing ("agent did a lot of work"). It usually means the skill failed to give concrete pointers.
- Comparing to absolute thresholds across very different skills. Use the per-skill baseline once you have one.
