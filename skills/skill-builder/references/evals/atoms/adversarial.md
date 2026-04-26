# atom: adversarial

| Type | Cost | Depends on |
|---|---|---|
| tester | medium | — |

Test whether out-of-scope inputs are correctly rejected. Validates the `Do not trigger` boundary.

## When to add

When the `Do not trigger` section changes, or before publishing a skill that's adjacent to existing skills.

## Inputs

- SKILL.md
- adversarial input set (inputs the skill *should* refuse, plus borderline cases)

## Output

```json
{
  "false_positives": ["input 2: would trigger but should reject — overlaps with <adjacent-skill>"],
  "false_negatives": [],
  "ambiguous": ["input 1"],
  "boundary_score": 7
}
```

## Common mistakes

- Building the adversarial set from the same imagination that wrote the SKILL.md. Pull adversarial inputs from real-user sessions or from sibling skills' `When to use` sections.
- Treating `ambiguous` as a non-finding. Each ambiguous input is a missing line in `Do not trigger`.
