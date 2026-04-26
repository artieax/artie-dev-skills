# atom: open-questions-log

| Type | Cost | Depends on |
|---|---|---|
| reporter | low | `independent-evaluator` |

After the evaluator runs, ask it to report what it could not determine from the SKILL.md. This is the standard **Open Questions Log** from requirements engineering (IEEE 29148 ambiguity tracking).

## When to add

Whenever you run `independent-evaluator`. Pairs naturally with `assumptions-log` — together they tell you what the SKILL.md left ambiguous vs. what the evaluator filled in.

## Inputs

- evaluator session (or SKILL.md + input replay)

## Output

```json
{
  "open_questions": [
    { "step": 2, "issue": "SKILL.md does not specify what to do when X is missing" }
  ]
}
```

## Prompt addition

Append to the `independent-evaluator` prompt:

```
After execution, also report:
open_questions: instructions you could not follow because the SKILL.md was ambiguous or silent.
Format: [{ "step": N, "issue": "..." }]
```

## Common mistakes

- Asking for open questions without giving the evaluator permission to admit confusion → it confabulates instead of reporting honestly.
- Treating an empty list as "all clear" without checking against fresh adversarial fixtures (use `hold-out` for that).
