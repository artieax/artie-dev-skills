# atom: collision-scan

| Type | Cost | Depends on |
|---|---|---|
| scanner | low | — |

Compare trigger phrases across all skills in the repo. Flags overlaps that would route the same user phrase to two skills.

## When to add

When trigger phrases change, or before publishing. Cheap enough to run as part of CI.

## Inputs

- SKILL.md trigger section
- all other skills' trigger sections in the repo

## Output

```json
{
  "collisions": [
    {
      "skill_a": "skill-builder",
      "skill_b": "agent-config-manager",
      "overlapping_phrase": "create a new skill",
      "severity": "high",
      "fix": "Add Do not trigger boundary for private repos"
    }
  ],
  "clean": false
}
```

## Common mistakes

- Treating `severity: low` collisions as ignorable. They block the boundary tightening loop later.
- Comparing only against published skills. Compare against in-progress branches too — collisions discovered post-merge are painful.
