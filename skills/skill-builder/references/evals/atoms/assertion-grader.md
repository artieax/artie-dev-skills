# atom: assertion-grader

| Type | Cost | Depends on |
|---|---|---|
| validator | low | `independent-evaluator` |

Per-fixture **structured assertions with literal evidence**. Each assertion is
a checkable claim about the actual output (e.g., "output contains a JSON block
with fields x/y/z"); the grader returns `{passed, evidence}` per assertion.

Modeled after Anthropic's official `skill-creator` grader.md. Differs from
`acceptance-gate` (which validates SKILL.md `## Requirements` MUST items at the
**skill level**): this atom validates **fixture-level** output properties.

## Two-tier validation

Combine both atoms for full coverage:

| Atom | Scope | Question |
|---|---|---|
| `acceptance-gate` | skill level | "Does the skill obey its own RFC 2119 rules?" |
| `assertion-grader` | fixture level | "Does each fixture's actual output match its expected properties?" |

## When to add

- Fixtures have specific expected properties beyond "ran successfully"
- You want to catch shape regressions (missing field, wrong format) without
  hand-diffing `actual.md` every time
- Combined with `independent-evaluator` for the executor preset

## Inputs

- per-fixture assertions in `fixtures/<scenario>/assertions.json`:

  ```json
  {
    "assertions": [
      "Output contains a markdown table with `Skill` and `Purpose` columns",
      "Output references `dependency-graph.md`",
      "Output has at least 3 distinct trigger phrases listed"
    ]
  }
  ```
- `actual.md` from `independent-evaluator`

## Output

Per fixture (`grading.json`):

```json
{
  "fixture": "happy-path",
  "n": 3,
  "assertions": [
    {
      "text": "Output contains a markdown table with `Skill` and `Purpose` columns",
      "passed": true,
      "evidence": "| Skill | Purpose |\n|---|---|"
    },
    {
      "text": "Output references `dependency-graph.md`",
      "passed": false,
      "evidence": "no occurrence of 'dependency-graph' in 1240-char output"
    },
    {
      "text": "Output has at least 3 distinct trigger phrases listed",
      "passed": true,
      "evidence": "3 bullet entries under '## When to use'"
    }
  ],
  "pass_rate": 0.67
}
```

Aggregated across fixtures, append one row to `references/eval-log.jsonl`:

```jsonl
{"pipeline":"executor","version":"v2","date":"2026-04-26","assertion_pass_rate":0.83,"failed_assertions":["happy-path: references dependency-graph.md"]}
```

## Prompt

The grader runs `prompts/assertion-grader.md` once per assertion. Each call is
independent (no shared context across assertions), so a wrong evidence in
assertion 1 cannot bias assertion 2.

## Common mistakes

- **Vague assertions.** "Output is good" is not gradable. Each assertion must be
  *literally checkable* — a property a fresh reader of the output text alone
  can verify.
- **No evidence.** An assertion that passes without literal evidence quoted
  from the output is hand-wavy. The prompt forces evidence ≤ 200 chars; if you
  edit the prompt, keep this rule.
- **Reusing gate assertions.** `acceptance-gate` already covers the SKILL.md
  RFC 2119 rules. `assertion-grader` should describe *fixture-output*
  properties, not skill-level invariants.
- **Treating `pass_rate` as the only signal.** Track *which assertion failed*
  in `failed_assertions[]` — a 0.83 pass rate with the same 1 assertion always
  failing tells you exactly what to fix.
