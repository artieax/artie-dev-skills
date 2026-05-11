---
id: dream-assisted
kind: maintenance-method
reads: instincts/*.md (existing pool, NOT raw sessions)
writes: instincts/*.md (consolidates / retires)
default_algo: llm
default_polarity_bias: any
typical_promotion_target: consolidation
---

# dream-assisted — clean up the instinct pool

Unlike the other modes, this one does **not** read raw sessions. It reads the *existing* `instincts/` folder and reorganises it: merge duplicates, retire stale or contradicted instincts, surface conflicts.

## What it does

1. Reads every `instincts/*.md`
2. Clusters by domain + topic similarity (semantic embedding)
3. For each cluster:
   - **merge**: 2+ instincts saying the same thing → combine into one with stronger `signals.support_count`
   - **retire**: instincts contradicted by newer ones → set `review_status: rejected` with note
   - **conflict**: 2 instincts in opposition → surface for human decision
4. Writes a `dream-report.md` summarising the consolidations
5. Updates affected `instincts/<slug>.md` files in place (frontmatter only; body preserved)

## When to use

- Periodic maintenance (monthly / quarterly)
- After bulk imports — when many similar candidates were added at once
- When the instinct pool feels noisy or contradictory

## Why it matters

Without consolidation, the pool grows monotonically and `instinct-to-harness` emits the same rule under three slightly different names. Dream-assisted prunes that.

## Inspired by

Anthropic Managed Agents' "Dreaming" feature, applied to instinct pools instead of memory stores.

## When NOT to use

- Pool is small (< 20 instincts) → not worth the cycles
- Pool was just curated by hand → don't undo human work without consent
