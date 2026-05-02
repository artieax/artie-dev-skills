"""
optimize.py — scaffold prompt optimizer (Mode D stdout-delegate)

Reads accumulated eval data from data/evals.jsonl, then runs a
BootstrapFewShot-style selection: for each held-out example, generate a
scaffold with candidate few-shot demos and score it. Keep the demo set that
maximizes the 5-metric score.

Saves selected demos to data/optimized_prompt.json for use in Phase 2.

Because this script uses Mode D (stdout-delegate), LLM calls are emitted as
__LLM_DELEGATE__ directives and processed by the host after the script exits.
Multi-turn chains are handled by splitting the pipeline into four phases:

  1. --prepare        Load trainset, build candidates, save work state.
                      No LLM calls.

  2. --emit-scaffolds For each (candidate, held-out) pair, emit a scaffold
                      generation directive. The host processes all and writes
                      tmp/optimize/scaffolds/{i}_{j}.md.

  3. --emit-scores    Read generated scaffolds, emit a score directive for each.
                      The host writes tmp/optimize/scores/{i}_{j}.json.

  4. --finalize       Read all scores, pick the best demo set, write
                      data/optimized_prompt.json.

Usage:
    # From skill root (e.g. skills/skill-builder/)

    python scripts/optimize.py --prepare [--max-demos 3] [--trials 8] [--seed N]
    # → SKILL.md: process __LLM_DELEGATE__ lines (none emitted in this phase)

    python scripts/optimize.py --emit-scaffolds
    # → SKILL.md: process __LLM_DELEGATE__ lines (scaffold generation)

    python scripts/optimize.py --emit-scores
    # → SKILL.md: process __LLM_DELEGATE__ lines (scoring)

    python scripts/optimize.py --finalize

    # Or, generate a scaffold from saved demos directly:
    python scripts/optimize.py --generate --description "..." --requirements "..."
    # (no __LLM_DELEGATE__ emitted; prints scaffold prompt for host to render inline)

Stdlib only. No claude CLI or API key needed.
"""

from __future__ import annotations

import argparse
import glob
import itertools
import json
import os
import random
import re
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))
import prompts
from agent import call_emit, read_result, read_json, result_exists, save_state, load_state


METRICS = [
    "trigger_precision",
    "workflow_coverage",
    "output_clarity",
    "red_flag_completeness",
    "dep_accuracy",
]

_WORK_STATE = "tmp/optimize/work.json"
_SCAFFOLD_DIR = "tmp/optimize/scaffolds"
_SCORE_DIR = "tmp/optimize/scores"


# ---------------------------------------------------------------------------
# Metric coercion (shared by score-reading path)
# ---------------------------------------------------------------------------

def _coerce_metric(value: object) -> Optional[float]:
    """Return a clamped float in [0, 10], or None if not a real finite number."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    n = float(value)
    if n != n or n in (float("inf"), float("-inf")):
        return None
    return max(0.0, min(10.0, n))


def _score_from_dict(scores_dict: dict) -> float:
    """Normalize a scores dict (5 metrics, 0–10 each) to [0, 1]."""
    total = 0.0
    for m in METRICS:
        v = _coerce_metric(scores_dict.get(m))
        if v is None:
            return 0.0
        total += v
    return total / 50.0


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_trainset(data_path: str) -> list[dict]:
    """Load eval records into few-shot training examples."""
    if not os.path.exists(data_path):
        print(f"[warn] {data_path} not found — run collect_evals.py first")
        return []

    examples = []
    skipped = 0
    with open(data_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rec = json.loads(line)
            if rec.get("total") is None:
                continue
            skill_md = rec.get("skill_md") or ""
            if not skill_md:
                legacy = rec.get("input_md") or ""
                if _looks_like_skill_md(legacy):
                    skill_md = legacy
            if not skill_md:
                skipped += 1
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
    if skipped:
        print(f"[warn] skipped {skipped} record(s) with no SKILL.md snapshot")
    return examples


def _looks_like_skill_md(text: str) -> bool:
    return text.lstrip().startswith("---\n") and "\nname:" in text[:300]


def _extract_description(skill_md: str, change_notes: str, skill_name: str) -> str:
    for line in skill_md.splitlines()[:30]:
        if line.startswith("description:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    return f"A skill named '{skill_name}' for the artie-dev-skills OSS library."


_HTML_COMMENT_RE = re.compile(r"<!--.*?-->", re.DOTALL)


def _strip_html_comments(text: str) -> str:
    return _HTML_COMMENT_RE.sub("", text)


def _extract_requirements(skill_md: str, change_notes: str) -> str:
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
    return (
        "Follow the standard 7-phase lifecycle "
        "(CREATE/SCAFFOLD/ITERATE/EVALS/AUTO-DEPS/AUTO-SPLIT/SCHEDULE). "
        "Worktree-first. English only. Flat skills/ structure."
    )


# ---------------------------------------------------------------------------
# Candidate building
# ---------------------------------------------------------------------------

def _build_candidates(
    trainset: list[dict], max_demos: int, trials: int, rng: random.Random
) -> list[tuple[int, ...]]:
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
    seen: set[tuple[int, ...]] = set()
    ordered: list[tuple[int, ...]] = []
    for c in candidates:
        if c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered[:trials]


# ---------------------------------------------------------------------------
# Prompt builders
# ---------------------------------------------------------------------------

def _scaffold_prompt(description: str, requirements: str, demos: list[dict]) -> str:
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
    return prompts.render(
        "scaffold-user",
        few_shot_block=few_shot_block,
        description=description,
        requirements=requirements,
    )


def _score_prompt(scaffold: str) -> str:
    return prompts.render("score", scaffold=scaffold)


# ---------------------------------------------------------------------------
# Phase 1: prepare
# ---------------------------------------------------------------------------

def phase_prepare(
    data_path: str,
    max_demos: int,
    trials: int,
    seed: Optional[int],
) -> None:
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
            f"\n[warn] Only {len(trainset)} training example(s). "
            "Recommended ≥ 8 before treating output as load-bearing."
        )
    if len(trainset) < 2:
        print("[error] Need at least 2 examples to hold one out. Aborting.")
        sys.exit(1)

    if seed is None:
        seed = random.randrange(2**31 - 1)
    rng = random.Random(seed)
    candidates = _build_candidates(trainset, max_demos, trials, rng)

    pairs: list[dict] = []
    for i, demo_indices in enumerate(candidates):
        held_out_indices = [j for j in range(len(trainset)) if j not in demo_indices]
        if not held_out_indices:
            held_out_indices = list(range(len(trainset)))
        for j_idx, j in enumerate(held_out_indices):
            pairs.append({
                "candidate_idx": i,
                "demo_indices": list(demo_indices),
                "held_out_idx": j,
                "pair_id": f"{i}_{j_idx}",
            })

    state = {
        "seed": seed,
        "max_demos": max_demos,
        "trials": trials,
        "trainset": trainset,
        "candidates": [list(c) for c in candidates],
        "pairs": pairs,
    }
    save_state(_WORK_STATE, state)

    print(f"\nPrepared {len(candidates)} candidate set(s), {len(pairs)} scaffold task(s).")
    print(f"Seed: {seed}")
    print(f"State saved to {_WORK_STATE}")
    print("\nNext: run --emit-scaffolds")


# ---------------------------------------------------------------------------
# Phase 2: emit scaffold directives
# ---------------------------------------------------------------------------

def phase_emit_scaffolds() -> None:
    state = load_state(_WORK_STATE)
    if state is None:
        print(f"[error] Work state not found at {_WORK_STATE}. Run --prepare first.")
        sys.exit(1)

    trainset = state["trainset"]
    pairs = state["pairs"]
    system = prompts.load("scaffold-system")
    n = 0

    for pair in pairs:
        out = os.path.join(_SCAFFOLD_DIR, f"{pair['pair_id']}.md")
        if result_exists(out):
            continue  # already processed
        demos = [trainset[j] for j in pair["demo_indices"]]
        ex = trainset[pair["held_out_idx"]]
        prompt = _scaffold_prompt(ex["description"], ex["requirements"], demos)
        call_emit(prompt, out=out, system=system)
        n += 1

    if n == 0:
        print("All scaffold directives already processed. Run --emit-scores next.")
    else:
        print(f"Emitted {n} scaffold directive(s). Process __LLM_DELEGATE__ lines, then run --emit-scores.")


# ---------------------------------------------------------------------------
# Phase 3: emit score directives
# ---------------------------------------------------------------------------

def phase_emit_scores() -> None:
    state = load_state(_WORK_STATE)
    if state is None:
        print(f"[error] Work state not found at {_WORK_STATE}. Run --prepare first.")
        sys.exit(1)

    pairs = state["pairs"]
    schema = (
        '{"trigger_precision": N, "workflow_coverage": N, '
        '"output_clarity": N, "red_flag_completeness": N, "dep_accuracy": N}'
    )
    n = 0
    missing_scaffolds = 0

    for pair in pairs:
        scaffold_path = os.path.join(_SCAFFOLD_DIR, f"{pair['pair_id']}.md")
        score_path = os.path.join(_SCORE_DIR, f"{pair['pair_id']}.json")
        if result_exists(score_path):
            continue  # already scored
        if not result_exists(scaffold_path):
            missing_scaffolds += 1
            continue
        scaffold = read_result(scaffold_path)
        prompt = _score_prompt(scaffold)
        call_emit(prompt, out=score_path, json_mode=True, id=f"score_{pair['pair_id']}")
        n += 1

    if missing_scaffolds:
        print(f"[warn] {missing_scaffolds} scaffold file(s) missing — run --emit-scaffolds first.")
    if n == 0:
        print("All score directives already processed. Run --finalize next.")
    else:
        print(f"Emitted {n} score directive(s). Process __LLM_DELEGATE__ lines, then run --finalize.")


# ---------------------------------------------------------------------------
# Phase 4: finalize
# ---------------------------------------------------------------------------

def phase_finalize(output_path: str) -> None:
    state = load_state(_WORK_STATE)
    if state is None:
        print(f"[error] Work state not found at {_WORK_STATE}. Run --prepare first.")
        sys.exit(1)

    trainset = state["trainset"]
    candidates = state["candidates"]
    pairs = state["pairs"]

    # Aggregate scores per candidate
    candidate_scores: dict[int, list[float]] = {i: [] for i in range(len(candidates))}
    missing = 0
    for pair in pairs:
        score_path = os.path.join(_SCORE_DIR, f"{pair['pair_id']}.json")
        if not result_exists(score_path):
            missing += 1
            continue
        try:
            scores_dict = read_json(score_path)
        except (ValueError, json.JSONDecodeError) as e:
            print(f"  [warn] could not parse {score_path}: {e}")
            continue
        s = _score_from_dict(scores_dict)
        candidate_scores[pair["candidate_idx"]].append(s)

    if missing:
        print(f"[warn] {missing} score file(s) missing — run --emit-scores first.")

    # Pick best candidate
    best_i = -1
    best_score = -1.0
    for i, scores in candidate_scores.items():
        if not scores:
            continue
        avg = sum(scores) / len(scores)
        print(f"  candidate {i}: avg_score={avg:.3f} ({len(scores)} pairs)")
        if avg > best_score:
            best_score = avg
            best_i = i

    if best_i == -1:
        print("[error] No candidates scored successfully.")
        sys.exit(1)

    best_demos = [trainset[j] for j in candidates[best_i]]
    print(f"\nBest candidate: {best_i} (score={best_score:.3f}, {len(best_demos)} demo(s))")
    for d in best_demos:
        print(f"  demo: {d['id']}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    result = {
        "seed": state.get("seed"),
        "few_shot_examples": [
            {"description": d["description"], "requirements": d["requirements"], "scaffold": d["scaffold"]}
            for d in best_demos
        ],
        "candidate_sets": candidates,
        "score": best_score,
        "n_demos": len(best_demos),
        "max_demos": state.get("max_demos"),
        "trials": state.get("trials"),
        "trainset_ids": [ex["id"] for ex in trainset],
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {output_path}")
    print("\nUsage:")
    print("  python scripts/optimize.py --generate --description '...' --requirements '...'")


# ---------------------------------------------------------------------------
# Generate from saved demos (Mode C helper)
# ---------------------------------------------------------------------------

def generate_from_optimized(output_path: str, description: str, requirements: str) -> None:
    """Print the scaffold prompt with few-shot demos for the host to render inline."""
    if not os.path.exists(output_path):
        print(f"No optimized prompt at {output_path}. Run --prepare / --emit-scaffolds / --emit-scores / --finalize first.")
        sys.exit(1)
    with open(output_path, encoding="utf-8") as f:
        data = json.load(f)
    demos = data.get("few_shot_examples", [])
    score = data.get("score")
    score_str = f"{score:.2f}" if isinstance(score, (int, float)) else "?"
    print(f"Using {len(demos)} few-shot demo(s) (score={score_str})")
    system = prompts.load("scaffold-system")
    prompt = _scaffold_prompt(description, requirements, demos)
    print("\n--- System prompt ---")
    print(system)
    print("\n--- User prompt (render inline with your host LLM) ---")
    print(prompt)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Optimize scaffold generation prompt (Mode D stdout-delegate)"
    )
    parser.add_argument("--skill-root", default=".", help="Skill root dir (default: .)")

    phase_group = parser.add_mutually_exclusive_group(required=True)
    phase_group.add_argument("--prepare", action="store_true",
                             help="Phase 1: load trainset, build candidates, save state")
    phase_group.add_argument("--emit-scaffolds", action="store_true",
                             help="Phase 2: emit scaffold generation directives")
    phase_group.add_argument("--emit-scores", action="store_true",
                             help="Phase 3: emit scoring directives")
    phase_group.add_argument("--finalize", action="store_true",
                             help="Phase 4: read scores, pick best, save optimized_prompt.json")
    phase_group.add_argument("--generate", action="store_true",
                             help="Print scaffold prompt (uses saved demos) for host to render")
    phase_group.add_argument("--no-optimize", action="store_true",
                             help="Dry-run: show training data only")

    parser.add_argument("--max-demos", type=int, default=3)
    parser.add_argument("--trials", type=int, default=8)
    parser.add_argument("--seed", type=int, default=None)
    parser.add_argument("--description", default="", help="For --generate")
    parser.add_argument("--requirements", default="", help="For --generate")
    args = parser.parse_args()

    skill_root = os.path.abspath(args.skill_root)
    os.chdir(skill_root)

    data_path = os.path.join(skill_root, "data", "evals.jsonl")
    output_path = os.path.join(skill_root, "data", "optimized_prompt.json")

    if args.no_optimize:
        trainset = load_trainset(data_path)
        print(f"Loaded {len(trainset)} example(s). (--no-optimize: skipping)")
        return

    if args.prepare:
        phase_prepare(data_path, args.max_demos, args.trials, args.seed)
    elif args.emit_scaffolds:
        phase_emit_scaffolds()
    elif args.emit_scores:
        phase_emit_scores()
    elif args.finalize:
        phase_finalize(output_path)
    elif args.generate:
        if not args.description:
            print("--generate requires --description")
            sys.exit(1)
        generate_from_optimized(output_path, args.description, args.requirements)


if __name__ == "__main__":
    main()
