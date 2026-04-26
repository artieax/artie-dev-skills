# v4 — changes

## From v3 (skill-creator → skill-builder rename + lifecycle scripts)

### 1. Rename: `skill-creator` → `skill-builder`
- frontmatter `name:` and the H1 in SKILL.md updated.
- `description:` rewritten to describe the new scope: scaffold, worktree
  iteration, evals, dependency registration, splitting, periodic
  improvement.

### 2. Phase map / references restructured
- Phase 2 now points at `references/scaffold/index.md` plus
  `references/scaffold/atomic-builder.md` and
  `references/scaffold/execution-modes.md`.
- Phase 4 points at `references/evals/index.md`,
  `references/evals/preset-selection.md`,
  `references/evals/review-viewer.md`, and `references/lineage.md`.
- New atom catalogs under `references/scaffold/atoms/` and
  `references/evals/atoms/`.

### 3. New `## Requirements` runner contract
- The canonical, copy-paste-from-anywhere invocation is now Form B
  (`--skill-root skills/<target-skill>` from the repo root). Form A
  (run from the target skill root) is documented as the interactive
  shorthand.
- Red flags now call out the `data/evals.jsonl` write modes
  (`--force` vs `--rebuild`) and the XSS / numeric-coercion contract for
  HTML rendering.

### 4. Lifecycle scripts shipped under `scripts/`
- `collect_evals.py` — append/force/rebuild modes, atomic writes,
  `--allow-missing-skill-md` footgun guard.
- `generate_review.py` — self-contained HTML viewer with whitelist
  field projection, numeric coercion, and HTML escaping.
- `optimize.py` — bootstrap few-shot scaffold optimizer with seeded
  candidate sets and process-wide call budget.
- `optimize_description.py` — description trigger-precision optimizer
  with single-line frontmatter contract enforcement.
- `smoke_test.py` — pre-merge sanity checks for SKILL.md and scripts.

### 5. SSOT fix vs. previous v3 pointer
- `current.md` previously read `active version = v3`, but
  `v3/skill.md` was still the old `name: skill-creator` snapshot.
  v4 captures the live SKILL.md so the optimizer's training row matches
  the file Claude actually loads.

### 6. Eval status
- No fresh eval has been run against v4 yet. `eval.json` carries
  `total: null` and `scores: {}` so `collect_evals.py` writes the
  snapshot but `optimize.py` skips the row (it ignores rows whose
  `total is None`). `references/eval-log.jsonl` will get a v4 entry
  the next time the eval pipeline runs.
