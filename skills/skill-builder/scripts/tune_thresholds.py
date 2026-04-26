# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "optuna>=3.6.0",
# ]
# ///
"""
tune_thresholds.py — Optuna-based convergence threshold tuner

Reads accumulated eval history from data/evals.jsonl, simulates the
convergence algorithm across all skill version sequences, and finds the
(convergence_threshold, improvement_threshold, min_quality, metric_weights)
quadruple that maximizes quality × efficiency.

Usage:
    uv run scripts/tune_thresholds.py
    uv run scripts/tune_thresholds.py --trials 200 --show-plots
    uv run scripts/tune_thresholds.py --skill-root skills/skill-builder

Pass `--with plotly` to uv run for `--show-plots`.

Output:
    data/tuned_thresholds.json   — best params to paste into iteration.md
    Prints recommended replacements for the defaults in iteration.md

Threshold semantics — see references/iteration.md → "Iteration exit
criteria" for the full prose. Short version:

    convergence_threshold (default 7.0)
        Per-metric pass threshold (out of 10). When *every* metric is at
        or above this floor, the skill has "converged" and we exit.

    improvement_threshold (default 15%)
        Plateau-stop threshold. When the latest version's weighted score
        improves by *less than* this percentage over the previous
        version (and the improvement is non-negative — see "regression"
        note below), the loop has plateaued. We exit with
        status=plateaued — but only if min_quality is already met (see
        below).

    min_quality (default 7.0)
        Quality floor that gates the plateau-stop. Without this gate, a
        skill stuck at 4/10 with tiny gains would also plateau and exit
        prematurely. With it, low-improvement at low quality forces the
        loop to keep going (or hit the 5-iteration cap), so we never
        merge a low-scoring skill just because it stopped improving.

    Regression handling
        ``improvement < 0`` is *not* a plateau — it's a regression. The
        plateau gate explicitly requires ``improvement >= 0`` and that
        no individual metric dropped against the previous version.
        Regressions are a continue / revert / redesign signal, never a
        stop signal; ``references/iteration.md`` documents the same
        contract for human readers.
"""

import argparse
import json
import os
from collections import defaultdict
from typing import Optional

import optuna
optuna.logging.set_verbosity(optuna.logging.WARNING)


METRICS = [
    "trigger_precision",
    "workflow_coverage",
    "output_clarity",
    "red_flag_completeness",
    "dep_accuracy",
]

# Defaults from iteration.md
DEFAULT_CONVERGENCE = 7.0
DEFAULT_IMPROVEMENT = 15.0
DEFAULT_MIN_QUALITY = 7.0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_version_sequences(data_path: str) -> list[list[dict]]:
    """
    Group eval records by skill_name, sort by version, return sequences.

    A sequence = list of eval dicts for a single skill, oldest first.
    Only sequences with >= 2 versions are useful for threshold tuning.
    """
    if not os.path.exists(data_path):
        return []

    by_skill: dict[str, list[dict]] = defaultdict(list)
    # Force UTF-8: cached records embed em dashes / arrows / non-ASCII
    # notes (locale defaults like cp1252 / cp932 raise on these).
    with open(data_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("total") is not None:
                by_skill[rec["skill_name"]].append(rec)

    sequences = []
    for skill_name, recs in by_skill.items():
        # Sort by version number (v1 < v2 < v3 ...)
        recs.sort(key=lambda r: _version_num(r.get("version", "v0")))
        if len(recs) >= 2:
            sequences.append(recs)

    return sequences


def _version_num(v: str) -> int:
    try:
        return int(v.lstrip("v"))
    except ValueError:
        return 0


# ---------------------------------------------------------------------------
# Convergence simulation
# ---------------------------------------------------------------------------

def simulate(
    sequence: list[dict],
    convergence_threshold: float,
    improvement_threshold: float,
    weights: dict[str, float],
    min_quality: float = DEFAULT_MIN_QUALITY,
) -> tuple[int, float]:
    """
    Simulate the iteration loop on a version sequence with given thresholds.

    Two independent exit gates (mirrors references/iteration.md):

      Pass gate (`all_above`):
          Every metric is at or above ``convergence_threshold``. Exit
          with status=converged.

      Plateau-stop gate (`plateaued`):
          The latest improvement over the previous version is a *small
          non-negative* gain (``0 <= improvement < improvement_threshold``)
          AND the current weighted score is already above ``min_quality``
          AND no individual metric regressed against the previous
          version. The combined clause is the safety belt:

          * ``improvement >= 0`` blocks a regressing run from being
            mislabelled as "plateaued" — a v3 that drops to 7.1 from a
            v2 of 8.5 would otherwise satisfy ``improvement < 15%`` and
            silently exit with status=plateaued, freezing a strictly
            worse skill. Negative improvement is a *regression*, which
            is a redesign / revert / continue signal — never a stop
            signal.
          * ``weighted >= min_quality`` stops a low-scoring skill stuck
            at 4/10 with tiny gains from "plateauing" out at low
            quality.
          * ``not metric_regressed`` blocks the case where the weighted
            average improved (because of weight reshuffling) while one
            metric quietly regressed — e.g. trigger_precision drops
            but the other four metrics nudge up. We treat any
            per-metric regression as "not actually plateaued; keep
            iterating".

    Returns:
        (stop_index, quality_at_stop)
        stop_index: index in sequence where we would have stopped (0-based)
        quality_at_stop: weighted score at that version (0-10)
    """
    prev_weighted: Optional[float] = None
    prev_scores: Optional[dict] = None
    stop_index = len(sequence) - 1  # default: ran everything

    for i, rec in enumerate(sequence):
        scores = rec.get("scores", {})
        if not scores:
            continue

        # Weighted average score (0–10)
        weighted = sum(
            scores.get(m, 0) * weights.get(m, 1.0) for m in METRICS
        ) / sum(weights.get(m, 1.0) for m in METRICS)

        # Pass gate: all metrics >= convergence_threshold
        all_above = all(
            scores.get(m, 0) >= convergence_threshold for m in METRICS
        )

        # Plateau-stop gate: small *non-negative* improvement AND quality
        # >= floor AND no per-metric regression. The non-negative clause
        # is the critical guard: without it, a regressing version
        # (improvement < 0) would also satisfy `improvement < threshold`
        # and silently freeze a strictly worse skill as "plateaued". See
        # the docstring for the full rationale.
        plateaued = False
        if prev_weighted is not None and prev_weighted > 0 and prev_scores is not None:
            improvement = (weighted - prev_weighted) / prev_weighted * 100
            small_positive_gain = 0 <= improvement < improvement_threshold
            metric_regressed = any(
                scores.get(m, 0) < prev_scores.get(m, 0) for m in METRICS
            )
            if (
                small_positive_gain
                and weighted >= min_quality
                and not metric_regressed
            ):
                plateaued = True

        if all_above or (plateaued and i > 0):
            stop_index = i
            break

        prev_weighted = weighted
        prev_scores = scores

    quality = _weighted_score(sequence[stop_index].get("scores", {}), weights)
    return stop_index, quality


def _weighted_score(scores: dict, weights: dict) -> float:
    if not scores:
        return 0.0
    total_w = sum(weights.get(m, 1.0) for m in METRICS)
    return sum(scores.get(m, 0) * weights.get(m, 1.0) for m in METRICS) / total_w


# ---------------------------------------------------------------------------
# Objective
# ---------------------------------------------------------------------------

def objective(trial: optuna.Trial, sequences: list[list[dict]]) -> float:
    convergence_threshold = trial.suggest_float("convergence_threshold", 5.0, 9.5)
    improvement_threshold = trial.suggest_float("improvement_threshold", 3.0, 35.0)
    # min_quality is the floor that gates the plateau-stop. Search a band
    # below convergence (we want plateau-stop to fire earlier than the
    # pass gate, but not below 5/10 — anything less is "merge a broken
    # skill" territory).
    min_quality = trial.suggest_float("min_quality", 5.0, 8.5)

    weights = {m: trial.suggest_float(f"w_{m}", 0.5, 2.0) for m in METRICS}

    # Normalize weights to sum to len(METRICS) so absolute scale stays consistent
    total_w = sum(weights.values())
    weights = {m: v / total_w * len(METRICS) for m, v in weights.items()}

    total_efficiency = 0.0
    total_quality = 0.0
    total_possible = 0

    for seq in sequences:
        if len(seq) < 2:
            continue
        max_iters = len(seq) - 1
        stop_idx, quality = simulate(
            seq,
            convergence_threshold,
            improvement_threshold,
            weights,
            min_quality=min_quality,
        )
        iters_saved = max_iters - stop_idx
        total_efficiency += iters_saved / max(max_iters, 1)
        total_quality += quality
        total_possible += 1

    if total_possible == 0:
        return 0.0

    avg_efficiency = total_efficiency / total_possible
    avg_quality = total_quality / total_possible

    # Penalize stopping at low quality (< 6.5/10 → bad)
    quality_penalty = max(0.0, 6.5 - avg_quality) * 0.5

    # Objective: maximize quality-weighted efficiency
    score = avg_quality * 0.55 + avg_efficiency * 10 * 0.45 - quality_penalty
    return score


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------

def summarize(best_params: dict, sequences: list[list[dict]]) -> None:
    ct = best_params["convergence_threshold"]
    it = best_params["improvement_threshold"]
    mq = best_params.get("min_quality", DEFAULT_MIN_QUALITY)
    weights = {m: best_params[f"w_{m}"] for m in METRICS}

    print("\n=== Simulation with best params ===")
    for seq in sequences:
        name = seq[0]["skill_name"]
        stop_idx, quality = simulate(seq, ct, it, weights, min_quality=mq)
        print(
            f"  {name}: stop at v{stop_idx + 1}/{len(seq)}  "
            f"quality={quality:.1f}/10"
        )

    print("\n=== Recommended updates for iteration.md ===")
    print(f"  convergence_threshold : {ct:.1f}  (was {DEFAULT_CONVERGENCE:.1f})")
    print(f"  improvement_threshold : {it:.1f}%  (was {DEFAULT_IMPROVEMENT:.1f}%)")
    print(f"  min_quality           : {mq:.1f}  (was {DEFAULT_MIN_QUALITY:.1f})")
    print("\n  Metric weights (relative):")
    for m in METRICS:
        marker = " *" if best_params[f"w_{m}"] > 1.2 else ""
        print(f"    {m:<30} {best_params[f'w_{m}']:.2f}{marker}")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Tune convergence thresholds with Optuna")
    parser.add_argument("--skill-root", default=".", help="Skill root directory. Default: .")
    parser.add_argument("--trials", type=int, default=100, help="Optuna trials (default: 100)")
    parser.add_argument(
        "--show-plots", action="store_true",
        help="Show Optuna visualization plots (requires matplotlib + plotly)"
    )
    args = parser.parse_args()

    skill_root = os.path.abspath(args.skill_root)
    data_path = os.path.join(skill_root, "data", "evals.jsonl")
    output_path = os.path.join(skill_root, "data", "tuned_thresholds.json")

    print(f"Loading eval history from {data_path} ...")
    sequences = load_version_sequences(data_path)

    if not sequences:
        print(
            "No multi-version sequences found.\n"
            "Need at least 2 completed evals for the same skill.\n"
            "Run collect_evals.py after accumulating more eval.json files."
        )
        return

    print(f"Found {len(sequences)} skill sequence(s) with >= 2 versions:")
    for seq in sequences:
        totals = [f"v{i+1}:{r['total']}" for i, r in enumerate(seq)]
        print(f"  {seq[0]['skill_name']}: {' → '.join(totals)}")

    # Run optimization
    print(f"\nRunning {args.trials} Optuna trials ...")
    study = optuna.create_study(direction="maximize")
    study.optimize(lambda t: objective(t, sequences), n_trials=args.trials)

    best = study.best_params
    print(f"\nBest value: {study.best_value:.4f}")

    summarize(best, sequences)

    # Save results
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    result = {
        "convergence_threshold": best["convergence_threshold"],
        "improvement_threshold": best["improvement_threshold"],
        "min_quality": best.get("min_quality", DEFAULT_MIN_QUALITY),
        "metric_weights": {m: best[f"w_{m}"] for m in METRICS},
        "optuna_best_value": study.best_value,
        "trials": args.trials,
        "n_sequences": len(sequences),
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)
    print(f"\nSaved to {output_path}")

    if args.show_plots:
        try:
            import optuna.visualization as vis
            fig = vis.plot_param_importances(study)
            fig.show()
            fig2 = vis.plot_optimization_history(study)
            fig2.show()
        except ImportError:
            print("[warn] Re-run with plotly available: uv run --with plotly scripts/tune_thresholds.py --show-plots")


if __name__ == "__main__":
    main()
