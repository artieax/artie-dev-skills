# atom: baseline-comparison

| Type | Cost | Depends on |
|---|---|---|
| comparator | medium | `independent-evaluator` (run twice per fixture) |

Run the same task twice — once **with the skill loaded** and once **without** —
and quantify the value the skill adds. Reports `pass_rate`, `duration_s`, and
`tokens` for both, plus per-axis deltas and a verdict.

Modeled after Anthropic's official `skill-creator` benchmark (with-skill /
baseline split). Where `regression-diff` answers *"did v(N) improve vs.
v(N-1)?"*, this atom answers *"does the skill help at all vs. doing the task
without it?"*.

## When to add

- Before publishing — proves the skill is worth installing
- After a major Workflow change — confirms the new flow still beats the
  no-skill baseline
- Combine with `runtime-telemetry` for the cost side of the value equation

## Inputs

- SKILL.md
- `fixtures/<scenario>/input.md` (and optional `expected.md`)
- Two execution modes per fixture:
  - **`with_skill`** — the evaluator is given SKILL.md + input
  - **`without_skill`** — the evaluator is given only the fixture input (no SKILL.md)
- Run **≥ 3 times per side** to dampen LLM variance, report mean ± stddev

## Output

```json
{
  "fixtures_run": ["happy-path", "edge-ambiguous"],
  "n_runs_per_side": 5,
  "with_skill": {
    "pass_rate": 0.85,
    "pass_rate_stddev": 0.07,
    "duration_s": 12.4,
    "tokens": 8500
  },
  "without_skill": {
    "pass_rate": 0.40,
    "pass_rate_stddev": 0.12,
    "duration_s": 8.2,
    "tokens": 5500
  },
  "delta": {
    "pass_rate": 0.45,
    "duration_s": 4.2,
    "tokens": 3000
  },
  "verdict": "skill provides value: pass_rate +45pp at +51% time/token cost"
}
```

### Verdict thresholds

| `delta.pass_rate` | Verdict |
|---|---|
| `≥ +0.10` | `skill provides value` |
| `0.00 < delta < +0.10` | `marginal value` |
| `≤ 0` | `skill regresses baseline` — do not publish |

## Common mistakes

- **Running each side once.** LLM variance is high; ≥ 3 runs per side is the
  minimum for the report to be trusted. ≥ 5 is better.
- **Comparing `pass_rate` only.** A skill that doubles `pass_rate` while
  tripling tokens may not be worth shipping. Read all three axes.
- **Forgetting context isolation.** The `without_skill` run must use a fresh
  agent that has never seen the SKILL.md. Use Mode B (Task subagent) — that's
  what the `independent-evaluator` atom is for.
- **Using only the happy path.** Run at least one edge fixture too — the skill
  may shine only on the non-trivial cases.
