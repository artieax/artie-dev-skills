# atom: independent-evaluator

| Type | Cost | Depends on |
|---|---|---|
| runner | medium | — |

Have an **independent agent** (no prior context about the skill's design intent) attempt to execute the SKILL.md against a fixture input. The evaluator only sees the SKILL.md and the input — never the design discussion.

This is the **Independent V&V** (IEEE 1012) principle applied to skills, equivalent to clean-room execution: the runner never reads the spec author's head. See `references/lineage.md`.

## When to add

After **any Workflow change**, or whenever you want to verify the SKILL.md is actually executable rather than merely well-written. The author and the evaluator must be different agent sessions.

## Inputs

- SKILL.md
- `fixtures/<scenario>/input.md`

## Output

- `actual.md` — what the skill produced
- (used as the upstream signal for `open-questions-log`, `assumptions-log`, `acceptance-gate`, `runtime-telemetry`)

## Prompt template

```
You are an independent evaluator. You have no context about how this skill was designed.
Execute the SKILL.md below against the provided input. Produce the output the skill describes.

=== SKILL.md ===
<paste>
=== INPUT ===
<paste fixture input.md>
```

## Common mistakes

- Reusing the same Claude session that authored the skill → the evaluator "knows" the design intent and papers over ambiguity (this defeats the IV&V principle).
- Picking a fixture that exercises only the happy path. Include at least one edge-case fixture.
