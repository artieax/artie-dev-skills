"""
optimize_description.py — tune SKILL.md description for trigger precision (Mode D)

Reads SKILL.md, generates a 20-query eval set (or loads a cached one),
generates N description variants, scores each on the eval set, and picks
the description with the highest accuracy.

Because this script uses Mode D (stdout-delegate), LLM calls are emitted as
__LLM_DELEGATE__ directives. Multi-turn dependencies are handled via phases:

  1. --emit-eval-set   If no usable cached eval set exists, emit one
                       eval-set-gen directive.
                       The host writes data/trigger_eval_set.json.

  2. --emit-variants   Emit one description-variant directive.
                       The host writes tmp/desc_opt/variants.json.

  3. --emit-judgments  Read eval set + variants, emit one trigger-judge
                       directive per (variant, query) pair.
                       The host writes tmp/desc_opt/judge_{v}_{q}.json.

  4. --finalize [--apply]
                       Read all judgment results, pick best description,
                       write data/optimized_description.json.
                       With --apply: also rewrite SKILL.md.

Phases 1 and 2 can run in parallel (neither depends on the other).

Usage:
    cd skills/<name>/
    python ../skill-builder/scripts/optimize_description.py --skill-root .

    python optimize_description.py --skill-root . --emit-eval-set
    # → host processes __LLM_DELEGATE__ (eval set gen)

    python optimize_description.py --skill-root . --emit-variants
    # → host processes __LLM_DELEGATE__ (variant generation)

    python optimize_description.py --skill-root . --emit-judgments
    # → host processes __LLM_DELEGATE__ (N × (1+V) judgments)

    python optimize_description.py --skill-root . --finalize [--apply]

Stdlib only. No claude CLI or API key needed.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Optional

sys.path.insert(0, os.path.dirname(__file__))
import prompts
from agent import call_emit, read_json, result_exists, save_state, load_state


_WORK_DIR = "tmp/desc_opt"
_VARIANTS_OUT = "tmp/desc_opt/variants.json"
_JUDGE_DIR = "tmp/desc_opt/judges"

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_DESC_LINE_RE = re.compile(
    r"^description:\s*(?P<quote>['\"]?)(?P<val>.*?)(?P=quote)\s*$",
    re.MULTILINE,
)
_UNSUPPORTED_DESC_MARKERS = {"|", ">", "|-", ">-", "|+", ">+"}

# Minimum queries required for a cached eval set to be considered usable.
_MIN_USABLE_QUERIES = 10


# ---------------------------------------------------------------------------
# SKILL.md helpers
# ---------------------------------------------------------------------------

def load_skill_md(path: str) -> tuple[str, str]:
    """Return (full_text, current_description)."""
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm = _FRONTMATTER_RE.match(text)
    if not fm:
        raise SystemExit(f"{path}: missing YAML frontmatter")
    for line in fm.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            raw_value = stripped[len("description:"):].strip()
            if raw_value in _UNSUPPORTED_DESC_MARKERS:
                raise SystemExit(
                    f"{path}: `description: {raw_value}` is a YAML "
                    "folded/block scalar; rewrite as a single-line scalar."
                )
            break
    desc_match = _DESC_LINE_RE.search(fm.group(1))
    if not desc_match:
        raise SystemExit(f"{path}: no `description:` line in frontmatter")
    raw_value = desc_match.group("val").strip()
    if desc_match.group("quote") == "'":
        raw_value = raw_value.replace("''", "'")
    return text, raw_value


def _single_line_description(value: object) -> str:
    return " ".join(str(value).split())


def replace_description(skill_md: str, new_desc: str) -> str:
    new_desc = _single_line_description(new_desc)
    quoted = "'" + new_desc.replace("'", "''") + "'"
    replacement_line = f"description: {quoted}"
    fm = _FRONTMATTER_RE.match(skill_md)
    if not fm:
        return skill_md
    fm_body = fm.group(1)
    new_fm_body = _DESC_LINE_RE.sub(lambda _m: replacement_line, fm_body, count=1)
    return skill_md[: fm.start(1)] + new_fm_body + skill_md[fm.end(1):]


# ---------------------------------------------------------------------------
# Eval set helpers
# ---------------------------------------------------------------------------

def _load_cached_eval_set(eval_set_path: str) -> Optional[list[dict]]:
    if not os.path.exists(eval_set_path):
        return None
    try:
        with open(eval_set_path, encoding="utf-8") as f:
            data = json.load(f)
    except (OSError, json.JSONDecodeError):
        return None
    queries = data["queries"] if isinstance(data, dict) and "queries" in data else data
    if not isinstance(queries, list) or len(queries) < _MIN_USABLE_QUERIES:
        return None
    return queries


# ---------------------------------------------------------------------------
# Phase 1: emit eval-set generation directive
# ---------------------------------------------------------------------------

def phase_emit_eval_set(skill_md: str, eval_set_path: str) -> None:
    cached = _load_cached_eval_set(eval_set_path)
    if cached is not None:
        print(f"Usable cached eval set found ({len(cached)} queries) — skipping emit.")
        print("Run --emit-variants next (or in parallel).")
        return

    if os.path.exists(eval_set_path):
        print(f"[warn] Cached eval set at {eval_set_path} is unusable, regenerating ...")

    prompt = prompts.render("eval-set-gen", skill_md=skill_md)
    call_emit(
        prompt,
        out=eval_set_path,
        json_mode=True,
        id="eval_set_gen",
    )
    print(f"Emitted eval-set-gen directive → {eval_set_path}")
    print("Process __LLM_DELEGATE__ lines, then run --emit-variants and --emit-judgments.")


# ---------------------------------------------------------------------------
# Phase 2: emit variant generation directive
# ---------------------------------------------------------------------------

def phase_emit_variants(skill_md: str, current_desc: str, n_variants: int) -> None:
    if result_exists(_VARIANTS_OUT):
        print(f"Variants already generated at {_VARIANTS_OUT} — skipping emit.")
        return
    error_summary = "No error information yet — generate initial variants."
    prompt = prompts.render(
        "description-variant", skill_md=skill_md, n=n_variants, eval_summary=error_summary
    )
    os.makedirs(os.path.dirname(_VARIANTS_OUT), exist_ok=True)
    call_emit(prompt, out=_VARIANTS_OUT, json_mode=True, id="variant_gen")
    print(f"Emitted variant-gen directive → {_VARIANTS_OUT}")
    print("Process __LLM_DELEGATE__ lines, then run --emit-judgments.")


# ---------------------------------------------------------------------------
# Phase 3: emit judgment directives
# ---------------------------------------------------------------------------

def phase_emit_judgments(eval_set_path: str, current_desc: str) -> None:
    queries = _load_cached_eval_set(eval_set_path)
    if queries is None:
        print(f"[error] No usable eval set at {eval_set_path}. Run --emit-eval-set first.")
        sys.exit(1)

    if not result_exists(_VARIANTS_OUT):
        print(f"[error] Variants not generated yet at {_VARIANTS_OUT}. Run --emit-variants first.")
        sys.exit(1)
    try:
        raw = read_json(_VARIANTS_OUT)
    except (ValueError, json.JSONDecodeError) as e:
        print(f"[error] Could not parse variants: {e}")
        sys.exit(1)
    variants_raw = raw.get("variants") if isinstance(raw, dict) else None
    if not isinstance(variants_raw, list):
        print("[error] variants.json missing 'variants' list.")
        sys.exit(1)
    variants = [_single_line_description(v) for v in variants_raw if v and str(v).strip()]
    all_descriptions = [current_desc] + variants

    os.makedirs(_JUDGE_DIR, exist_ok=True)
    n = 0
    for v_idx, desc in enumerate(all_descriptions):
        label = "current" if v_idx == 0 else f"v{v_idx}"
        for q_idx, q in enumerate(queries):
            out = os.path.join(_JUDGE_DIR, f"{label}_{q_idx}.json")
            if result_exists(out):
                continue
            query = q.get("query", "")
            prompt = prompts.render("trigger-judge", description=desc, query=query)
            call_emit(prompt, out=out, json_mode=True, id=f"judge_{label}_{q_idx}")
            n += 1

    if n == 0:
        print("All judgment directives already processed. Run --finalize next.")
    else:
        print(f"Emitted {n} judgment directive(s). Process __LLM_DELEGATE__ lines, then run --finalize.")
        print(f"  {len(all_descriptions)} description(s) × {len(queries)} queries")


# ---------------------------------------------------------------------------
# Phase 4: finalize
# ---------------------------------------------------------------------------

def _accuracy(desc_label: str, queries: list[dict]) -> dict:
    correct = 0
    fps: list[str] = []
    fns: list[str] = []
    judge_failures: list[str] = []
    for q_idx, q in enumerate(queries):
        query = q.get("query", "")
        raw_expected = q.get("should_trigger", False)
        if not isinstance(raw_expected, bool):
            judge_failures.append(query)
            continue
        out = os.path.join(_JUDGE_DIR, f"{desc_label}_{q_idx}.json")
        if not result_exists(out):
            judge_failures.append(query)
            continue
        try:
            result = read_json(out)
        except (ValueError, json.JSONDecodeError):
            judge_failures.append(query)
            continue
        raw_actual = result.get("trigger") if isinstance(result, dict) else None
        if not isinstance(raw_actual, bool):
            judge_failures.append(query)
            continue
        if raw_actual == raw_expected:
            correct += 1
        elif raw_actual and not raw_expected:
            fps.append(query)
        else:
            fns.append(query)
    valid = len(queries) - len(judge_failures)
    return {
        "accuracy": correct / valid if valid else 0.0,
        "n": valid,
        "false_positives": fps,
        "false_negatives": fns,
        "judge_failures": judge_failures,
    }


def phase_finalize(
    eval_set_path: str,
    skill_path: str,
    current_desc: str,
    skill_md_text: str,
    apply: bool,
    output_path: str,
) -> None:
    queries = _load_cached_eval_set(eval_set_path)
    if queries is None:
        print(f"[error] No usable eval set at {eval_set_path}.")
        sys.exit(1)

    if not result_exists(_VARIANTS_OUT):
        print(f"[error] Variants file missing: {_VARIANTS_OUT}.")
        sys.exit(1)
    raw = read_json(_VARIANTS_OUT)
    variants_raw = raw.get("variants") if isinstance(raw, dict) else []
    variants = [_single_line_description(v) for v in variants_raw if v and str(v).strip()]
    all_descriptions = [current_desc] + variants

    history: list[dict] = []
    for v_idx, desc in enumerate(all_descriptions):
        label = "current" if v_idx == 0 else f"v{v_idx}"
        score = _accuracy(label, queries)
        score["description"] = desc
        history.append(score)
        mark = " ← current" if v_idx == 0 else ""
        print(f"  [{label}] accuracy={score['accuracy']:.2f}  {desc[:60]}{mark}")

    best = max(history, key=lambda h: (h["accuracy"], h["description"] == current_desc))
    print(f"\nBest accuracy: {best['accuracy']:.2f}")
    print(f"Best description: {best['description']}")

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    result = {
        "current": history[0],
        "best": best,
        "n_variants_tried": len(variants),
        "all_history": history,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print(f"\nSaved to {output_path}")

    if apply:
        if best["description"] == current_desc:
            print("(best == current; nothing to apply)")
        else:
            new_md = replace_description(skill_md_text, best["description"])
            with open(skill_path, "w", encoding="utf-8") as f:
                f.write(new_md)
            print(f"Applied best description to {skill_path}")
            print("Review the diff before committing.")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Optimize SKILL.md description for trigger precision (Mode D)"
    )
    parser.add_argument("--skill-root", default=".", help="Skill root dir (default: .)")
    parser.add_argument("--variants", type=int, default=8, help="Number of variants (default: 8)")
    parser.add_argument(
        "--eval-set", default=None,
        help="Path to cached eval set JSON (default: data/trigger_eval_set.json)",
    )
    parser.add_argument("--apply", action="store_true",
                        help="Write best description back to SKILL.md (--finalize only)")

    phase_group = parser.add_mutually_exclusive_group(required=True)
    phase_group.add_argument("--emit-eval-set", action="store_true",
                             help="Phase 1: emit eval-set-gen directive (if no cached set)")
    phase_group.add_argument("--emit-variants", action="store_true",
                             help="Phase 2: emit description-variant directive")
    phase_group.add_argument("--emit-judgments", action="store_true",
                             help="Phase 3: emit trigger-judge directives for all (desc, query) pairs")
    phase_group.add_argument("--finalize", action="store_true",
                             help="Phase 4: compute accuracies, pick best, save result")

    args = parser.parse_args()

    skill_root = os.path.abspath(args.skill_root)
    os.chdir(skill_root)

    skill_path = os.path.join(skill_root, "SKILL.md")
    eval_set_path = args.eval_set or os.path.join(skill_root, "data", "trigger_eval_set.json")
    output_path = os.path.join(skill_root, "data", "optimized_description.json")

    if not os.path.exists(skill_path):
        print(f"SKILL.md not found at {skill_path}")
        sys.exit(1)

    skill_md_text, current_desc = load_skill_md(skill_path)
    print(f"Skill root:          {skill_root}")
    print(f"Current description: {current_desc}")
    print()

    if args.emit_eval_set:
        phase_emit_eval_set(skill_md_text, eval_set_path)
    elif args.emit_variants:
        phase_emit_variants(skill_md_text, current_desc, args.variants)
    elif args.emit_judgments:
        phase_emit_judgments(eval_set_path, current_desc)
    elif args.finalize:
        phase_finalize(eval_set_path, skill_path, current_desc, skill_md_text, args.apply, output_path)


if __name__ == "__main__":
    main()
