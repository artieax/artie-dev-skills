---
id: head-start
kind: extraction-method
reads: session-log
writes: instincts/<slug>.md
default_algo: llm
default_polarity_bias: any
typical_promotion_target: rule
---

# head-start — generic rules that would have shortened this session

Look back at the entire session and ask: **"What single rule, if known at message 1, would have made the rest of the session unnecessary or much shorter?"**

The output is intentionally **session-agnostic**. The rule has to generalize to any future session of similar shape — not just describe what happened this time.

## What it looks for

- **Re-discovery loops** — the AI re-learns the same fact mid-session that it could have started with
- **Misunderstood-then-clarified arcs** — the missing assumption that, if asserted up front, would have skipped the back-and-forth
- **Trial-and-error sequences** where the right answer was knowable from prior context
- **"Should have asked X first"** moments — places the agent acted before gathering a cheap-to-get fact
- **Tool-misselection** — wrong tool used for many turns before switching

## Output shape

Each instinct from this atom is:
- Written in **session-agnostic** form: no project names, no specific filenames, no this-session-only references
- `domain` set to the **broadest applicable** category (e.g., `git` not `git-pr-#42`)
- `polarity: never` for "stop doing X early" patterns; `good` for "do Y first" patterns
- `promotion_targets: [rule, doc]`
- `signals.confidence` left null — needs `evaluator` to confirm the rule generalizes

The body's `## Context` should describe the **class of situations**, not this one session. The `## Corrective` should be applicable directly without rewriting.

## Generalization gate

Before writing, the atom self-checks: "Could this instinct be lifted into a *different* repo / different stack / different person's session and still be useful?"

If the answer is no → drop it (it's a `failure-cluster` instinct, not a `head-start` instinct).

## Best paired with

- `--algo llm` — needs whole-session synthesis; surface keyword scans miss the "what was missing at message 1" framing
- `evaluator` atom downstream — generic rules over-fit fast; need scoring against a pool of sessions to confirm transfer
- `human-curated` for the first runs — confirms the rule really does generalize before auto-publish

## How it differs from sibling atoms

| atom | extracts |
|---|---|
| `failure-cluster` | this specific failure, this specific corrective |
| `success-pattern` | this specific working sequence |
| `head-start` | the **rule that would have skipped most of the session entirely**, in transferable form |

`head-start` is the only atom whose output is required to read as if the original session had never happened.

## When NOT to use

- Sessions < 5 messages — not enough scaffolding to identify head-start rules
- Sessions that succeeded smoothly on the first try — nothing to compress
- Pure exploration sessions — premature generalization is worse than no rule
- Highly project-specific sessions where every step depends on local context — generalization isn't honest
