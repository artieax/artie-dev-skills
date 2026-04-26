# Lineage — prior art behind the eval atoms

The eval-atom vocabulary in this skill is a deliberate restatement of well-established software-engineering practice. Each atom maps to a much older, broadly-known source. This file is the index linking the two.

The motivation is conservative: rather than invent new terminology for each measurement, name each atom after the discipline it descends from. That makes the design easier to review, easier to extend, and easier to explain to engineers from a non-LLM background.

---

## Mapping table

| Atom | Source discipline | Primary reference |
|---|---|---|
| `acceptance-gate` | Acceptance Test–Driven Development; Definition of Done (Scrum); RFC 2119 keywords for priorities | RFC 2119 (Bradner, 1997); ATDD (Koskela, *Practical Unit Testing*); Scrum DoD |
| `independent-evaluator` | Independent Verification & Validation; Clean-room Software Engineering | IEEE Std 1012 (V&V); Mills/Dyer/Linger, *Cleanroom Software Engineering* (IBM, 1987) |
| `open-questions-log` | Requirements engineering — ambiguity tracking and clarification logs | IEEE/ISO/IEC 29148 (Requirements Engineering) |
| `assumptions-log` | Project-management Assumptions Log; Architectural Decision Record | PMBOK *Assumptions Log*; Nygard, *Documenting Architecture Decisions* (2011) |
| `runtime-telemetry` | Application Performance Monitoring; runtime observability | Standard APM practice; OpenTelemetry vocabulary |
| `hold-out` | Train/test split; hold-out validation | Standard machine-learning evaluation methodology |
| `regression-diff` | Regression testing | Beizer, *Software Testing Techniques* |
| `adversarial` | Negative testing; adversarial test cases | Standard software QA practice |
| `collision-scan` | Namespace / API conflict detection | Standard SE practice for shared registries |
| `convergence-check` | Iterative-development stop condition; optimization convergence criteria | Classical optimization / numerical analysis |
| `static-score` | Code review rubrics; checklist-based quality assessment | Fagan inspections; checklist-driven review |

---

## Why RFC 2119 priorities for `## Requirements`

RFC 2119 (1997) standardised `MUST` / `SHOULD` / `MAY` (and their negations) as the canonical prioritisation vocabulary for technical specifications. Reusing it here gives:

- **Recognisable severity.** Anyone who has written or read a protocol spec already knows what `MUST` blocks and what `SHOULD` warns.
- **Compatibility with downstream tooling.** Acceptance gates, lint rules, and policy engines that already understand RFC 2119 can consume the same checklist without translation.
- **No bespoke severity vocabulary.** "critical", "high", "important" all have project-local meanings; RFC 2119 has one.

This is also why `acceptance-gate` keys its pass condition on `MUST` items only — it is the standard ATDD interpretation of a Definition of Done.

---

## Why an "independent" evaluator

The IV&V (Independent Verification & Validation) principle — codified for safety-critical systems in IEEE Std 1012 and applied for decades by NASA on flight software — says the verifier must be organisationally and informationally separate from the implementer. The same principle, transplanted to skills, becomes: the agent that executes the SKILL.md against fixtures must not be the same session that authored it. Reusing the author session contaminates the evaluation because the author "knows what was meant" and patches over ambiguity that a real downstream user would hit.

Cleanroom Software Engineering (IBM, 1987) makes a closely related claim from the testing side: testers must not see the implementation in order to remain unbiased. The independent-evaluator atom is the agent-skill version of the same constraint.

---

## Why two reporters (`open-questions-log` + `assumptions-log`)

Requirements engineering has long distinguished:

- **Open questions** — places where the specification is silent or contradictory and the implementer needs an answer. Tracked in IEEE/ISO/IEC 29148-style ambiguity logs.
- **Assumptions** — places where the implementer chose a reasonable default in the absence of guidance. Tracked in PMBOK Assumptions Logs and ADRs (Nygard 2011).

Both are useful. Open questions reveal omissions in the spec; assumptions reveal where the spec is silent enough that any plausible default looked acceptable. Conflating them loses signal.

---

## Why the gate is binary

Definition of Done (Scrum) and ATDD (Koskela, Adzic) both treat acceptance as binary: either every Must-pass criterion is satisfied or the work is not done. The eval pipeline preserves this — `all_must_passed` is the gate; non-`MUST` failures accumulate in the log but do not block.

This is intentionally not a weighted score. Weighted scores invite the failure mode where a low-priority pass compensates for a high-priority fail; binary `MUST` gates do not.

---

## What this skill adds on top

The classical references above each address one piece. This skill's contribution is the **composition**: a small atom catalog with explicit dependencies (`*-log` and `*-gate` atoms require `independent-evaluator`), preset combinations for common situations (`quick`, `executor`, `measured`, `diff`, `boundary`, `full`), and an iteration loop that stops when convergence-check sees the eval signal stabilise.

The atoms are deliberately not novel; the composition mechanism is.
