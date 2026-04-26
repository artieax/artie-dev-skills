# atom: acceptance-gate

| Type | Cost | Depends on |
|---|---|---|
| validator | low | `independent-evaluator` |

Evaluate the SKILL.md `## Requirements` checklist against `actual.md` using **RFC 2119** keyword priorities. At least one item must be tagged `MUST`. Pass condition: every `MUST` item returns `true`.

This is a standard **Acceptance Test** gate (ATDD / Definition of Done). See `references/lineage.md`.

## When to add

Always include in any pipeline that runs `independent-evaluator`. This is the hard gate: a failing `MUST` item blocks the pipeline regardless of other scores. `SHOULD` and `MAY` items are tracked but non-blocking.

## Inputs

- SKILL.md `## Requirements` section (RFC 2119-tagged)
- `actual.md`

## Output

```json
{
  "checklist": [
    { "item": "never pushes without instruction", "priority": "MUST",   "passed": true  },
    { "item": "creates worktree not branch",      "priority": "MUST",   "passed": false },
    { "item": "output file path specified",       "priority": "SHOULD", "passed": true  }
  ],
  "all_must_passed": false,
  "blocking_failures": ["creates worktree not branch"]
}
```

`all_must_passed: false` → pipeline result is **blocked** regardless of other element scores.

## Common mistakes

- Forgetting to tag at least one item `MUST` — the gate becomes vacuous.
- Treating `SHOULD` failures as ignorable. They aren't blockers but accumulate; track them in the eval log.
- Using free-form severity ("important", "high") instead of the RFC 2119 set (`MUST` / `SHOULD` / `MAY`).
