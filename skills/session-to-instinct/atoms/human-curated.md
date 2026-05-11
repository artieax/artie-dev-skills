---
id: human-curated
kind: extraction-method
reads: existing instincts (review_status: pending)
writes: instincts/<slug>.md (frontmatter only — review_status, body edits) + reviews/<slug>.md
default_algo: keyword
default_polarity_bias: any
typical_promotion_target: any
runs_during: REVIEW          # operates on built-pending instincts, not raw sessions
---

# human-curated — AI suggests, human decides

This atom runs **during the REVIEW phase**, not EXTRACT. EXTRACT always writes
candidate instincts to disk (with `review_status: pending`); `human-curated` then
walks the pending queue and asks the human to confirm each one before it can be
emitted by `instinct-to-harness`.

This split means:

- **Single command surface**: nothing new before BUILD — the existing EXTRACT → REVIEW flow already covers it.
- **Resumable**: if the human stops mid-review, the remaining candidates stay `pending` on disk.
- **Deterministic logs**: every accept/reject/edit/defer appends to `reviews/<slug>.md`.

## What it does

1. Walks `instincts/*.md` filtered by `review_status: pending` (most recent first)
2. Presents each candidate with: title, polarity, body, current `promotion_targets`, `target_skill` (if any)
3. User responds: `accept` / `reject` / `edit` / `skip` / `defer`
4. Updates the source instinct's frontmatter:
   - `accept` → `review_status: approved`
   - `reject` → `review_status: rejected`
   - `edit` → user-supplied text wins; `review_status: approved`
   - `defer` → `review_status: deferred`
   - `skip` → unchanged (left `pending` for next pass)
5. Appends a corresponding entry to `reviews/<slug>.md` for every action except `skip`

## When to use

- Initial rollout (first month) — establish what counts as a real instinct in this team
- Security-sensitive environments — auto-publish is too risky
- Cultural fit — what's "obvious" varies between teams; humans calibrate the bar

## Why it matters

The evaluator catches statistical noise but can't catch *cultural mismatch* — rules that are technically correct but wrong for this team. Human curation handles that.

## When NOT to use

- High-volume nightly batches — humans can't keep up
- After enough atoms have accumulated to trust the evaluator gate

## Best paired with

- `--algo keyword` for fast candidate generation (the human is the bottleneck, not extraction)
