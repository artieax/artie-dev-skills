# atom: assumptions-log

| Type | Cost | Depends on |
|---|---|---|
| reporter | low | `independent-evaluator` |

Report decisions the evaluator made where the SKILL.md gave no guidance — the silent assumptions. This is the **Assumptions Log** from project management practice (PMBOK) and the cousin of an **Architectural Decision Record** (ADR, Nygard 2011): both record choices made in the absence of explicit instruction.

## When to add

Whenever you run `independent-evaluator`. Pairs with `open-questions-log`: open questions flag **omissions**, the assumptions log flags **silent fills**.

## Output

```json
{
  "assumptions": [
    { "step": 3, "assumed": "SKILL.md was silent on format, so I chose markdown table" }
  ]
}
```

## Prompt addition

```
assumptions: decisions you made where SKILL.md gave no guidance.
Format: [{ "step": N, "assumed": "..." }]
```

## Common mistakes

- Ignoring the assumptions log because the output looked fine — silent assumptions are the next iteration's bugs.
- Conflating with `open-questions-log`. They are distinct: "I didn't know" vs "I picked something without being told to".
