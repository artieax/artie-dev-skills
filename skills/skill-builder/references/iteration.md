# iteration — worktree loop protocol

## Overview

A protocol for improving skills safely using `git worktree`. Each improvement idea gets its own worktree, evals are run to score each variant, and the winner is cherry-picked into the main branch.

---

## Single iteration (one idea)

Always work in a worktree — never switch the branch of the main working directory, and never run `git checkout -b` there.

```bash
cd <skills-repo>

# Main worktree just makes sure its `main` is fresh; never switches branches
# while another branch is checked out, never creates a branch here.
git -C <skills-repo> fetch origin main
# (if main is currently checked out in <skills-repo>, also: git -C <skills-repo> pull --ff-only origin main)

# Create branch + worktree from main in one step (-b form, per `git-worktree(1)`).
# Without -b, `git worktree add` expects the branch to already exist — that's
# the failure mode reviewers usually hit when copy-pasting the bare form.
git worktree add -b iter/<skill-name>-v<N> ../<skill>-iter main

# Do all work inside the worktree
cd ../<skill>-iter
# Improve SKILL.md
# Run eval and check scores
# Commit with bommit when criteria are met
bommit

# (do not push — wait for an explicit instruction)

# Adopt the result without ever switching branches in the main worktree:
# either fast-forward main from a separate adoption worktree, or cherry-pick
# from one. See "Adopting the winner" below for the exact commands.
```

---

## Parallel worktree iteration (multiple ideas at once)

### Setup

```bash
cd <skills-repo>
git fetch origin main

# Idea A: focus on workflow improvement
git worktree add -b iter/<skill-name>-v<N>a ../<skill>-iter-a main

# Idea B: focus on metrics strengthening
git worktree add -b iter/<skill-name>-v<N>b ../<skill>-iter-b main
```

### Work in each worktree

```bash
# Worktree A
cd ../<skill>-iter-a
# Improve the Workflow section
# Run eval → record score

# Worktree B
cd ../<skill>-iter-b
# Improve the metrics section
# Run eval → record score
```

### Compare and adopt the winner

```
📊 Comparison:
  Idea A (workflow): total 42/50
  Idea B (metrics):  total 38/50

→ Adopting idea A
```

Two ways to adopt — both keep the main working directory untouched (no
`git checkout -b` in the main worktree, no branch swap there).

**Option 1 — dedicated adoption worktree (preferred when adopting one idea verbatim):**

```bash
cd <skills-repo>
git fetch origin main

# Create a fresh worktree branched from main; cherry-pick the winning commit
git worktree add -b iter/<skill-name>-v<N> ../<skill>-winner main
cd ../<skill>-winner
git cherry-pick <commit-hash-from-iter-a>

# (optional) push and open a PR from this worktree
# Cleanup losing worktrees + branches once the PR is open or the change is merged
cd <skills-repo>
git worktree remove ../<skill>-iter-a
git worktree remove ../<skill>-iter-b
git branch -d iter/<skill-name>-v<N>a
git branch -d iter/<skill-name>-v<N>b
```

**Option 2 — cherry-pick directly into main (only if main is currently checked out in the main worktree and you intend a direct push to main):**

```bash
cd <main-worktree>            # this is the worktree that has `main` checked out
git switch main
git pull --ff-only origin main
git cherry-pick <commit-hash-from-iter-a>

# Cleanup
git worktree remove ../<skill>-iter-a
git worktree remove ../<skill>-iter-b
git branch -d iter/<skill-name>-v<N>a
git branch -d iter/<skill-name>-v<N>b
```

In both options the rule holds: **never** run `git checkout -b <new-branch>` inside the main working directory — branches are always created via `git worktree add -b`.

---

## Iteration exit criteria

Choose the convergence standard that matches the pipeline you're using.

### Standard (Pipeline A only)

Two independent exit gates — **either** gate may stop the loop, subject
to the maximum-iterations cap below. The two gates answer different
questions and exit with different `status` values, so the caller can
tell *why* the loop ended:

| Gate | Condition | Check | Exit |
|---|---|---|---|
| **Quality** (pass) | All metrics ≥ `convergence_threshold` (default 7 / 10) | `min(scores) >= 7` | `status=converged` — skill is good enough to ship |
| **Plateau** (stop) | Latest improvement is a small *non-negative* gain AND weighted score ≥ `min_quality` AND no individual metric regressed | `0 <= improvement < 15%` and `weighted >= min_quality` and `not metric_regressed` | `status=plateaued` — more iterations are unlikely to help |

A regression (`improvement < 0`, or any per-metric drop) is *not* a
plateau — it's a continue / revert / redesign signal. Neither gate
fires; the loop keeps iterating until the Quality gate passes or the
maximum-iterations cap kicks in.

> **Threshold semantics — read this before changing the numbers.**
>
> `improvement_threshold` is a **plateau-stop threshold**, not a "merge
> threshold". When the latest version improves by *less than* this
> percentage *and* the improvement is non-negative, we declare the
> loop has plateaued and stop iterating.
>
> The previous wording read this gate as a pass-criterion ("≥ +15%
> improvement → done"), which directly contradicted the optimizer in
> `scripts/tune_thresholds.py`. The two readings disagree about which
> direction of the inequality means *exit*; treating
> `improvement_threshold` as a plateau-stop threshold is the only
> reading that lines up with the simulator.
>
> The plateau gate is dangerous on its own and needs three guards:
>
> 1. **Non-negative improvement.** Without `improvement >= 0`, a
>    regressing version (e.g. v3 weighted = 7.1 after v2 = 8.5) would
>    satisfy `improvement < 15%` and silently freeze a strictly worse
>    skill as "plateaued". Negative improvement is a regression — a
>    redesign / revert / continue signal, never a stop signal.
> 2. **`min_quality` floor.** A skill stuck at 4/10 producing 1% gains
>    would otherwise also "plateau" and exit. The floor forces the
>    loop to keep going (or hit the 5-iteration cap) until quality is
>    passable.
> 3. **No per-metric regression.** Weight reshuffling can lift the
>    *weighted* score while one metric quietly drops (e.g.
>    `trigger_precision` regresses while the other four nudge up).
>    Treat any per-metric drop as "not actually plateaued; keep
>    iterating".

Both gates respect `## Maximum iterations` below — the loop never runs
past 5 iterations regardless of which gate fires first.

### Strict (Pipeline C — hybrid + hold-out)

Pass **all three** for **2 consecutive iterations**:

| Condition | Check |
|---|---|
| No new `open_questions` | `executor_report.open_questions.length === 0` |
| Pipeline A total change ≤ +3pt | `abs(new_total - prev_total) <= 3` |
| Hold-out score drop < 15pt | `holdout_total >= train_total - 15` |

If hold-out drops ≥ 15pt → overfitting. Revert to the last pre-overfit version and redesign.

### Diminishing-returns handling

Iteration shows the classical **diminishing-returns curve** familiar from any optimization loop: the first one or two iterations land most of the achievable gain, the next few capture progressively less, and beyond that further wording-level changes stop moving the score. Use the per-skill `eval-log.jsonl` history to detect when consecutive iterations produce score deltas inside the noise floor — that's the signal to stop tuning the prose and revisit the design (Phase 1, the three design questions) instead.

### Maximum iterations

Cap at **5 iterations** per skill regardless of convergence standard.
After 5, the problem is design, not wording — revisit Phase 1 (the three design questions).

---

## Worktree naming conventions

| Purpose | Path | Branch |
|---|---|---|
| New skill (scaffold) | `../<repo>-<skill-name>` | `feature/<skill-name>` |
| Single improvement | `../<skill>-iter` | `iter/<skill>-v<N>` |
| Parallel idea A | `../<skill>-iter-a` | `iter/<skill>-v<N>a` |
| Parallel idea B | `../<skill>-iter-b` | `iter/<skill>-v<N>b` |
| Refactor | `../<skill>-refactor` | `refactor/<skill>` |

### New skill scaffold (from main)

Always use `git worktree add -b` — never `git checkout -b` in the main working directory. The `-b <new-branch>` flag is the form `git-worktree(1)` documents for creating a new branch alongside the worktree; without it the branch must already exist.

```bash
git fetch origin main
git worktree add -b feature/<name> ../<repo>-<name> main
cd ../<repo>-<name>   # all scaffold work happens here
```

### Parallel improvement branches

Pre-existing branches (no `-b`):

```bash
git worktree add ../skill-builder-iter-a iter/skill-builder-v2-workflow
git worktree add ../skill-builder-iter-b iter/skill-builder-v2-metrics
```

New branches (use `-b`, branched from main):

```bash
git worktree add -b iter/skill-builder-v2-workflow ../skill-builder-iter-a main
git worktree add -b iter/skill-builder-v2-metrics  ../skill-builder-iter-b main
# Run evals in both → compare scores → cherry-pick the winner via Option 1 or 2 above
```

---

## Commit conventions (bommit integration)

One concept per commit. Use bommit for conventional commit formatting:

```bash
feat(<skill>): add worktree iteration protocol
refactor(<skill>): extract red-flags into a dedicated section
fix(<skill>): correct path reference in setup steps
docs(<skill>): add eval score baseline to eval-log.jsonl
```

---

## Common failure patterns

### Improvement does not converge
- Cause: changing a different section instead of the one in `top_improvement`
- Fix: each iteration changes **only** the area identified by `top_improvement`

### Eval score regressed
- Cause: removed context while trying to tighten the writing
- Fix: `git diff` to review deletions; restore necessary content

### Stale worktrees left behind
- Check: `git worktree list`
- Remove: `git worktree remove <path>` → `git branch -d <branch>`

### Diff too large to compare ideas
- Fix: each iteration changes **one focus area only** (e.g. Workflow only, Red flags only)
