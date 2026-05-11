---
id: ideal-gap
kind: extraction-method
reads: session-log
writes: instincts/<slug>.md
default_algo: llm
default_polarity_bias: bad
typical_promotion_target: rule
---

# ideal-gap — delta against a hypothetically superior model

At each key decision point in the session, ask: **"If a more capable model had been running this session, what would it have done differently here — and why?"**

The output is the **gap** between what actually happened and what the ideal would have been. These gaps become instincts that constrain future behavior toward the ceiling.

## What it looks for

- **Efficiency deltas** — current model took 8 tool calls; an optimal model would have needed 3. Why? What was unknown or mis-estimated?
- **Framing mismatches** — the approach was valid but suboptimal. A smarter model would have chosen a different axis entirely.
- **Tooling blind spots** — wrong tool selected for several turns before correction. A model with deeper tool knowledge would have picked correctly on turn 1.
- **Judgment asymmetries** — overly conservative where decisive action was safe; overconfident where caution was warranted.
- **Planning horizon failures** — no multi-step lookahead caused backtracking. A better planner would have anticipated the dependency.
- **Inference gaps** — explicit information existed in context that the model failed to use. A more attentive model would have read it without prompting.

## What "superior model" means here

Grounded only in plausible capability improvements:
- Deeper domain knowledge (git internals, macOS quirks, framework APIs)
- Better multi-step planning (anticipate 3 steps ahead, not 1)
- Faster hypothesis generation (fewer trial-and-error cycles)
- More accurate uncertainty estimation (knowing what you don't know)
- Better intent inference (read between the lines of user messages)

**Not** superhuman abilities. The counterfactual must be achievable with better knowledge or process — not telepathy or access to information that wasn't present.

## Output shape

Each gap → one instinct with:
- `polarity: bad` (we did something suboptimal) or `never` (we made a clearly wrong choice that a capable model would never make)
- `best_preset: when-dont-when` (default — comparing two approaches is the core structure) or `decision-table` (when multiple parallel choices existed)
- `promotion_targets: [rule, doc]`
- `signals.confidence` left null — needs `evaluator` to confirm the gap is real and reproducible, not one-off

The body's `## Corrective` must describe the **superior behavior** concretely, not just say "do better." If you can't write what the ideal model would have done in 1–3 sentences, the gap isn't sharp enough to commit.

## Grounding check

Before writing, the atom self-checks:
1. "Is this gap something a real model could close with better knowledge or process?" — if no, drop it
2. "Did the gap cause a measurable cost?" (extra turns, user correction, wrong output) — if no cost, it's opinion not gap
3. "Is the corrective actionable as a rule?" — if it requires situational judgment that can't be articulated, it's not ready for a harness

## Best paired with

- `--algo llm` only — counterfactual reasoning requires whole-session synthesis; keyword/diff cannot generate "what would X have done?"
- `evaluator` atom downstream — gap instincts over-fit easily ("this specific session was hard") and need scoring before commit
- `head-start` for complementary coverage: `head-start` targets initialization (`what rule at msg 1?`); `ideal-gap` targets execution quality at each step

## How it differs from sibling atoms

| atom | question | scope |
|---|---|---|
| `failure-cluster` | what went wrong and how do we avoid it? | explicit failures, errors, corrections |
| `head-start` | what rule at msg 1 would have skipped this session? | initialization / context gap |
| `ideal-gap` | what would a better model have done differently at each step? | execution quality, capability ceiling |

`ideal-gap` is the only atom that requires the model to reason counterfactually about its own behavior. The others describe what happened; this one describes what *should have* happened.

## When NOT to use

- Sessions that ran near-optimally — no meaningful delta to extract
- Sessions where failures were caused by missing user context that no model could have inferred — environment gap, not capability gap
- Sessions < 10 messages — not enough decision points to find systematic gaps
- Exploration / research sessions where the "ideal" path is undefined by nature
