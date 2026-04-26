"""
optimize.py — scaffold prompt optimizer (BootstrapFewShot via claude -p)

Reads accumulated eval data from data/evals.jsonl, then runs a
BootstrapFewShot-style selection: for each held-out example, generate a
scaffold with candidate few-shot demos and score it. Keep the demo set that
maximizes the 5-metric score.

Saves selected demos to data/optimized_prompt.json for use in Phase 2.

Usage:
    # From skill root (e.g. skills/skill-builder/)
    python scripts/optimize.py
    python scripts/optimize.py --max-demos 3 --trials 10
    python scripts/optimize.py --no-optimize   # dry-run: show training data only

    # Generate using saved demos:
    python scripts/optimize.py --generate \\
        --description "..." --requirements "..."

This module is a thin orchestration layer. Prompts live in prompts/*.md
(loaded by prompts.py); claude CLI calls live in agent.py.

Stdlib only. `claude` CLI must be installed and authenticated.
"""

from __future__ import annotations

import argparse
import itertools
import json
import os
import random
import re
import sys
from typing import Optional

# Ensure sibling modules import when run as `python scripts/optimize.py`
sys.path.insert(0, os.path.dirname(__file__))
import prompts
from agent import call, call_json, AgentConfig, AgentError, get_call_count, set_call_budget


METRICS = [
    "trigger_precision",
    "workflow_coverage",
    "output_clarity",
    "red_flag_completeness",
    "dep_accuracy",
]


# Strict numeric coercion shared by the LLM-judge path and the
# stored-scores path. The judge schema asks for an int 0..10, but a
# degraded model can return ``{"trigger_precision": "high"}`` or
# ``{"trigger_precision": True}``. ``float("high")`` raises and
# ``float(True)`` silently becomes 1.0 — both are score-corrupting.
#
# The same risk exists on the stored-scores side: ``data/evals.jsonl`` is
# produced by ``collect_evals.py``, which streams ``eval.json`` scores
# verbatim. Hand-edited or legacy records can carry ``"7"`` (string) or
# ``True`` and would either crash with TypeError or silently coerce to 1.
#
# Out-of-range / non-finite numbers are also rejected: a degraded model
# can return 999, -3, NaN, or inf, all of which corrupt the [0, 1]
# normalised total downstream (a single 999 dominates the median and
# pushes the final score above 1.0). Clamp to [0, 10] — the public
# contract of every metric prompt — and drop NaN/inf entirely. This
# matches the same defensive policy generate_review.py applies in
# ``_coerce_number(value, 0, 10)``.
def _coerce_metric(value: object) -> Optional[float]:
    """Return a clamped float in [0, 10], or None if the value is not a
    real finite number. Bools are explicitly rejected (they are an
    ``int`` subclass in Python, so ``True`` would otherwise sneak in
    as 1.0)."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    n = float(value)
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return max(0.0, min(10.0, n))


# ---------------------------------------------------------------------------
# Agent calls (one function per logical "turn")
# ---------------------------------------------------------------------------

def generate_scaffold(
    description: str,
    requirements: str,
    demos: list[dict],
    cfg: Optional[AgentConfig] = None,
) -> str:
    """Generate a SKILL.md draft with optional few-shot demos."""
    few_shot_block = ""
    if demos:
        items = [
            prompts.render(
                "scaffold-fewshot-item",
                i=i,
                description=d["description"],
                requirements=d["requirements"],
                scaffold=d["scaffold"],
            )
            for i, d in enumerate(demos, 1)
        ]
        few_shot_block = "\n".join(items) + "\n[Now generate]\n"

    user = prompts.render(
        "scaffold-user",
        few_shot_block=few_shot_block,
        description=description,
        requirements=requirements,
    )
    return call(user, system=prompts.load("scaffold-system"), cfg=cfg)


def score_scaffold(
    scaffold: str,
    stored_scores: Optional[dict] = None,
    cfg: Optional[AgentConfig] = None,
    rounds: int = 3,
) -> float:
    """
    Return a scaffold score normalized to [0, 1].

    If stored_scores is provided (from eval.json), use them directly — free
    and consistent. Otherwise call claude `rounds` times and take the median
    per metric (LLM-as-judge has high single-shot variance; median-of-3 is
    the cheapest meaningful damping).

    Both paths run every per-metric value through ``_coerce_metric()``.
    The stored-scores path used to add ints directly, so a hand-edited
    or legacy ``data/evals.jsonl`` carrying ``"7"`` (string) would
    raise ``TypeError`` and ``True`` would silently sum as 1. Now the
    same defensive coercion applies — a single un-coercible metric
    fails the path back to ``0.0`` so the demo set is dropped rather
    than poisoning the optimizer.
    """
    if stored_scores and all(stored_scores.get(m) is not None for m in METRICS):
        coerced: list[float] = []
        for m in METRICS:
            v = _coerce_metric(stored_scores.get(m))
            if v is None:
                print(
                    f"  [warn] stored_scores[{m!r}] not a number "
                    f"({type(stored_scores.get(m)).__name__}="
                    f"{stored_scores.get(m)!r}); dropping this scaffold from "
                    "the optimizer (re-run collect_evals.py to refresh)"
                )
                return 0.0
            coerced.append(v)
        return sum(coerced) / 50.0

    user = prompts.render("score", scaffold=scaffold)
    schema = ('{"trigger_precision": N, "workflow_coverage": N, '
              '"output_clarity": N, "red_flag_completeness": N, "dep_accuracy": N}')

    rolls: list[dict] = []
    for _ in range(max(1, rounds)):
        try:
            rolls.append(call_json(user, cfg=cfg, schema_hint=schema))
        except AgentError as e:
            print(f"  [warn] scoring round failed: {e}")
    if not rolls:
        return 0.0

    # Median per metric, then sum.
    def _median(xs: list[float]) -> float:
        xs = sorted(xs)
        n = len(xs)
        return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2

    medians: dict[str, float] = {}
    for m in METRICS:
        samples: list[float] = []
        for r in rolls:
            if not isinstance(r, dict):
                continue
            coerced_sample = _coerce_metric(r.get(m))
            if coerced_sample is None:
                if r.get(m) is not None:
                    print(f"  [warn] metric {m!r} not a number "
                          f"({type(r.get(m)).__name__}={r.get(m)!r}); "
                          "dropping this sample")
                continue
            samples.append(coerced_sample)
        medians[m] = _median(samples) if samples else 0.0

    return sum(medians.values()) / 50.0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_trainset(data_path: str) -> list[dict]:
    """
    Load eval records into few-shot training examples.

    Each example needs `scaffold` to be the actual SKILL.md content scored
    by the eval — *not* the change-log notes. Records without a SKILL.md
    snapshot are skipped (with a warning) because using change notes as
    few-shot demos teaches the model to write change logs, not skills.
    """
    if not os.path.exists(data_path):
        print(f"[warn] {data_path} not found — run collect_evals.py first")
        return []

    examples = []
    skipped_no_snapshot = 0
    # Cached `skill_md` snapshots round-trip non-ASCII (em dashes, arrows,
    # ≥) verbatim — locale defaults silently corrupt them on Windows.
    with open(data_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("total") is None:
                continue

            # Prefer skill_md (current schema). Fall back to input_md only
            # if it actually looks like a SKILL.md (legacy records).
            skill_md = rec.get("skill_md") or ""
            if not skill_md:
                legacy = rec.get("input_md") or ""
                if _looks_like_skill_md(legacy):
                    skill_md = legacy
            if not skill_md:
                skipped_no_snapshot += 1
                continue

            change_notes = rec.get("change_notes") or rec.get("input_md", "")
            examples.append({
                "id": rec["id"],
                "description": _extract_description(skill_md, change_notes, rec["skill_name"]),
                "requirements": _extract_requirements(skill_md, change_notes),
                "scaffold": skill_md,
                "scores": rec.get("scores", {}),
                "total": rec.get("total", 0),
            })
    if skipped_no_snapshot:
        print(f"[warn] skipped {skipped_no_snapshot} record(s) with no SKILL.md "
              f"snapshot — re-run collect_evals.py after saving "
              f"projects/<name>/v<N>/skill.md, or commit eval.json so git history "
              f"can resolve it")
    return examples


def _looks_like_skill_md(text: str) -> bool:
    """Cheap heuristic: a SKILL.md starts with YAML frontmatter."""
    return text.lstrip().startswith("---\n") and "\nname:" in text[:300]


def _extract_description(skill_md: str, change_notes: str, skill_name: str) -> str:
    """Pull description from SKILL.md frontmatter; fall back to change notes."""
    for line in skill_md.splitlines()[:30]:
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    # Legacy fallback — change_notes
    for i, line in enumerate(change_notes.splitlines()):
        if line.strip().startswith(("## Goals", "## Description", "## Changes")):
            desc_lines = []
            for l in change_notes.splitlines()[i + 1:]:
                if l.startswith("##"):
                    break
                stripped = l.strip("- ").strip()
                if stripped:
                    desc_lines.append(stripped)
            if desc_lines:
                return " ".join(desc_lines[:3])
    return f"A skill named '{skill_name}' for the artie-dev-skills OSS library."


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _strip_html_comments(text: str) -> str:
    """Remove ``<!-- ... -->`` blocks (including multi-line)."""
    return _HTML_COMMENT_RE.sub("", text)


def _extract_requirements(skill_md: str, change_notes: str) -> str:
    """Pull the ## Requirements list from SKILL.md; fall back to change notes.

    HTML comments are stripped *before* the line scan. The previous
    line-by-line ``startswith("<!--")`` filter only dropped the *first*
    line of a multi-line comment, leaking the body (e.g. "RFC 2119
    priorities; ...") into the requirements list passed to the
    optimizer.
    """
    lines = _strip_html_comments(skill_md).splitlines()
    for i, line in enumerate(lines):
        if line.strip().lower().startswith("## requirements"):
            req_lines = []
            for l in lines[i + 1:]:
                if l.startswith("##"):
                    break
                stripped = l.strip()
                if stripped:
                    req_lines.append(stripped)
            if req_lines:
                return "\n".join(req_lines[:8])
    # Legacy fallback
    for i, line in enumerate(change_notes.splitlines()):
        if any(kw in line.lower() for kw in ("requirement", "constraint", "goals")):
            req_lines = []
            for l in change_notes.splitlines()[i + 1:]:
                if l.startswith("##"):
                    break
                stripped = l.strip()
                if stripped:
                    req_lines.append(stripped)
            if req_lines:
                return "\n".join(req_lines[:5])
    return (
        "Follow the standard 7-phase lifecycle "
        "(CREATE/SCAFFOLD/ITERATE/EVALS/AUTO-DEPS/AUTO-SPLIT/SCHEDULE). "
        "Worktree-first. English only. Flat skills/ structure."
    )


# ---------------------------------------------------------------------------
# Bootstrap few-shot selection
# ---------------------------------------------------------------------------

def _build_candidates(
    trainset: list[dict], max_demos: int, trials: int, rng: random.Random
) -> list[tuple[int, ...]]:
    """Deterministic candidate set given a seeded RNG."""
    if len(trainset) <= max_demos:
        return list(
            itertools.combinations(
                range(len(trainset)),
                min(max_demos, len(trainset) - 1),
            )
        )
    indices = list(range(len(trainset)))
    candidates = [
        tuple(rng.sample(indices, min(max_demos, len(indices) - 1)))
        for _ in range(trials)
    ]
    # Dedupe while preserving the first-seen order (set() loses determinism).
    seen: set[tuple[int, ...]] = set()
    ordered: list[tuple[int, ...]] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered[:trials]


def estimate_cost(
    n_candidates: int,
    n_held_out_per_candidate: int,
    score_rounds: int,
) -> dict:
    """
    Estimate total claude calls for a bootstrap run.

    Each (candidate, held_out) pair runs:
      - 1 generate_scaffold call
      - score_rounds score calls

    Stored eval scores are intentionally NOT a factor: bootstrap scores
    *newly generated* scaffolds, which never have stored scores. Treating
    `has_stored_scores=True` as "free scoring" silently underestimated the
    real call count by 3-4x.
    """
    score_calls_per_pair = max(1, score_rounds)
    per_pair = 1 + score_calls_per_pair
    total = n_candidates * n_held_out_per_candidate * per_pair
    return {
        "candidates": n_candidates,
        "held_out_per_candidate": n_held_out_per_candidate,
        "score_rounds": score_rounds,
        "calls_per_pair": per_pair,
        "estimated_total_calls": total,
    }


def bootstrap_select(
    trainset: list[dict],
    max_demos: int,
    trials: int,
    cfg: Optional[AgentConfig] = None,
    rng: Optional[random.Random] = None,
    score_rounds: int = 3,
    candidates: Optional[list[tuple[int, ...]]] = None,
) -> tuple[list[dict], float]:
    """Try `trials` random demo subsets, pick the highest-scoring one.

    If `candidates` is provided, evaluate exactly those subsets. Callers that
    persist the candidate set (e.g. for seed-based replay) should build it
    once via `_build_candidates()` and pass it in — otherwise this function
    would advance `rng` a second time and evaluate a *different* subset than
    the one the caller saved.
    """
    if candidates is None:
        rng = rng or random.Random()
        candidates = _build_candidates(trainset, max_demos, trials, rng)

    best_demos: list[dict] = []
    best_score = -1.0

    print(f"Evaluating {len(candidates)} demo candidate set(s) ...")
    for i, demo_indices in enumerate(candidates):
        demos = [trainset[j] for j in demo_indices]
        held_out = [ex for j, ex in enumerate(trainset) if j not in demo_indices] or trainset

        scores = []
        for ex in held_out:
            scaffold = generate_scaffold(ex["description"], ex["requirements"], demos, cfg=cfg)
            s = score_scaffold(scaffold, cfg=cfg, rounds=score_rounds)
            scores.append(s)
            print(f"  [{i+1}/{len(candidates)}] held-out={ex['id']} score={s:.2f}")

        avg = sum(scores) / len(scores) if scores else 0.0
        if avg > best_score:
            best_score = avg
            best_demos = demos

    return best_demos, best_score


# ---------------------------------------------------------------------------
# Generate mode
# ---------------------------------------------------------------------------

def generate_from_optimized(
    output_path: str,
    description: str,
    requirements: str,
    cfg: Optional[AgentConfig] = None,
) -> None:
    if not os.path.exists(output_path):
        print(f"No optimized prompt found at {output_path}")
        print("Run without --generate first to optimize.")
        sys.exit(1)
    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)
    demos = data.get("few_shot_examples", [])
    score = data.get("score")
    score_str = f"{score:.2f}" if isinstance(score, (int, float)) else "?"
    print(f"Using {len(demos)} few-shot demo(s) (score={score_str})")
    scaffold = generate_scaffold(description, requirements, demos, cfg=cfg)
    print("\n" + "=" * 60)
    print(scaffold)
    print("=" * 60)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(description="Optimize scaffold generation prompt using claude -p")
    parser.add_argument("--skill-root", default=".", help="Skill root dir (default: .)")
    parser.add_argument("--max-demos", type=int, default=3, help="Max few-shot demos (default: 3)")
    parser.add_argument("--trials", type=int, default=8, help="Demo subset trials (default: 8)")
    parser.add_argument("--no-optimize", action="store_true", help="Dry-run: show training data only")
    parser.add_argument("--generate", action="store_true", help="Generate scaffold using saved demos")
    parser.add_argument("--description", default="", help="Skill description (--generate mode)")
    parser.add_argument("--requirements", default="", help="Skill requirements (--generate mode)")
    parser.add_argument("--model", help="Claude model (e.g. sonnet, opus)")
    parser.add_argument("--budget", type=float, help="Max USD per claude call")
    parser.add_argument("--seed", type=int, default=None,
                        help="Random seed for demo subset sampling (default: nondeterministic). "
                             "Persisted to optimized_prompt.json for reproducibility.")
    parser.add_argument("--max-calls", type=int, default=None,
                        help="Process-wide cap on total claude calls (also reads SKILL_BUILDER_MAX_CALLS).")
    parser.add_argument("--estimate-only", action="store_true",
                        help="Print expected call count and dollar bound, then exit (no claude calls).")
    parser.add_argument("--score-rounds", type=int, default=3,
                        help="Median-of-N for LLM scoring rounds (default: 3). "
                             "Bootstrap always scores newly-generated scaffolds, "
                             "so this is the actual per-pair scoring cost.")
    args = parser.parse_args()

    cfg = AgentConfig(model=args.model, budget_usd=args.budget)

    if args.max_calls is not None:
        set_call_budget(args.max_calls)

    skill_root = os.path.abspath(args.skill_root)
    data_path = os.path.join(skill_root, "data", "evals.jsonl")
    output_path = os.path.join(skill_root, "data", "optimized_prompt.json")

    if args.generate:
        if not args.description:
            print("--generate requires --description")
            sys.exit(1)
        generate_from_optimized(output_path, args.description, args.requirements, cfg=cfg)
        return

    print(f"Loading training data from {data_path} ...")
    trainset = load_trainset(data_path)
    if not trainset:
        print("No training data found. Run collect_evals.py first.")
        sys.exit(1)

    print(f"Loaded {len(trainset)} example(s):")
    for ex in trainset:
        print(f"  {ex['total']:>2}/50  {ex['id']:<30}  {ex['description'][:50]}")

    if len(trainset) < 8:
        print(
            f"\n[warn] Only {len(trainset)} training example(s).\n"
            "Few-shot demo selection has high variance below ~8 examples — the\n"
            "optimizer can over-fit to one or two atypical SKILL.md instances.\n"
            "Recommended: ≥ 8 records before treating the output as load-bearing."
        )

    if args.no_optimize:
        print("\n--no-optimize: skipping optimization.")
        return

    if len(trainset) < 2:
        print("[error] Need at least 2 examples to hold one out. Aborting.")
        sys.exit(1)

    seed = args.seed
    if seed is None:
        # Generate and persist a seed so the run is replayable even when not
        # explicitly seeded. Range matches Python's typical seed convention.
        seed = random.randrange(2**31 - 1)
    rng = random.Random(seed)

    candidates = _build_candidates(trainset, args.max_demos, args.trials, rng)
    held_out_per = max(1, len(trainset) - args.max_demos)
    estimate = estimate_cost(
        n_candidates=len(candidates),
        n_held_out_per_candidate=held_out_per,
        score_rounds=args.score_rounds,
    )
    print("\nCost estimate:")
    print(f"  candidates              : {estimate['candidates']}")
    print(f"  held-out per candidate  : ~{estimate['held_out_per_candidate']}")
    print(f"  calls per (cand, ho)    : {estimate['calls_per_pair']}"
          f"  (1 generate + {estimate['calls_per_pair'] - 1} score)")
    print(f"  estimated total calls   : {estimate['estimated_total_calls']}")
    if cfg.budget_usd is not None:
        upper = estimate["estimated_total_calls"] * cfg.budget_usd
        print(f"  upper-bound spend       : <= ${upper:.2f}  (per-call cap × calls)")
    print(f"  seed                    : {seed} "
          f"({'auto-generated' if args.seed is None else 'user-provided'})")
    if args.estimate_only:
        print("\n--estimate-only: not running optimizer.")
        return

    print(f"\nBootstrap selection: max_demos={args.max_demos}, trials={args.trials}")
    # Pass the pre-built candidate list so the saved `candidate_sets` is
    # exactly what gets evaluated. If we passed only `rng`, bootstrap_select
    # would call _build_candidates again on an already-advanced RNG and
    # evaluate a *different* subset than the one we just persisted, breaking
    # --seed replay.
    best_demos, best_score = bootstrap_select(
        trainset, args.max_demos, args.trials,
        cfg=cfg, score_rounds=args.score_rounds,
        candidates=candidates,
    )

    print(f"\nBest score: {best_score:.2f} ({len(best_demos)} demo(s))")
    for d in best_demos:
        print(f"  demo: {d['id']}")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result = {
        "seed": seed,
        "few_shot_examples": [
            {"description": d["description"], "requirements": d["requirements"], "scaffold": d["scaffold"]}
            for d in best_demos
        ],
        "candidate_sets": [list(c) for c in candidates],
        "score": best_score,
        "n_demos": len(best_demos),
        "n_calls_actual": get_call_count(),
        "n_calls_estimated": estimate["estimated_total_calls"],
        "max_demos": args.max_demos,
        "trials": args.trials,
        "score_rounds": args.score_rounds,
        "trainset_ids": [ex["id"] for ex in trainset],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {output_path}")
    print(f"Actual claude calls: {get_call_count()} "
          f"(estimated: {estimate['estimated_total_calls']})")
    print("\nUsage:")
    print("  python scripts/optimize.py --generate --description '...' --requirements '...'")
    print(f"  python scripts/optimize.py --seed {seed}   # replay this run")


if __name__ == "__main__":
    main()
