"""
optimize_description.py — tune SKILL.md frontmatter `description` for trigger precision

Reads SKILL.md, generates a 20-query trigger eval set (or loads cached one),
generates N description variants, scores each on the eval set, and picks the
description with the highest accuracy.

Inspired by Anthropic's official skill-creator description optimization loop.

Usage:
    # This is a *shared* tool that lives at skills/skill-builder/scripts/.
    # Target skills don't ship their own copy, so always point --skill-root
    # at the skill you're tuning.

    # From the target skill root:
    cd skills/<name>/
    python ../skill-builder/scripts/optimize_description.py --skill-root .
    python ../skill-builder/scripts/optimize_description.py --skill-root . --variants 12

    # Or from the repo root:
    python skills/skill-builder/scripts/optimize_description.py --skill-root skills/<name>
    python skills/skill-builder/scripts/optimize_description.py --skill-root skills/<name> \\
        --eval-set skills/<name>/data/trigger_eval_set.json
    python skills/skill-builder/scripts/optimize_description.py --skill-root skills/<name> \\
        --apply   # write best back to SKILL.md

Output:
    data/optimized_description.json   — best description + accuracy + history
    data/trigger_eval_set.json        — cached 20-query set (re-used on next run)

Frontmatter contract (deliberately narrow):
    The `description:` field MUST be a single-line YAML scalar — bare,
    single-quoted, or double-quoted. Folded (`>`) and block (`|`) scalars
    are NOT supported and will raise on read. Multi-line descriptions also
    silently break the description-tuning loop because the regex below
    only captures one line.

    If you need multi-line copy, put it in a separate doc and link to it
    from the description; or extend `_DESC_LINE_RE` to handle quoted
    multi-line forms before relying on it. The smoke test
    (`scripts/smoke_test.py::check_skill_md_description`) catches
    folded/block markers before they reach this script.

Stdlib only. Requires `claude` CLI on PATH (uses agent.py).
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from typing import Optional

# Ensure sibling modules import when run as `python scripts/optimize_description.py`
sys.path.insert(0, os.path.dirname(__file__))
import prompts
from agent import call_json, AgentConfig, AgentError, get_call_count, set_call_budget


_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
# Single-line scalar only — see the "Frontmatter contract" note in the
# module docstring. Matches:
#   description: bare-words ...
#   description: 'single quoted with ''doubled'' single quotes inside'
#   description: "double quoted"
# Does NOT handle: `description: |`, `description: >`, multi-line strings.
_DESC_LINE_RE = re.compile(
    r"^description:\s*(?P<quote>['\"]?)(?P<val>.*?)(?P=quote)\s*$",
    re.MULTILINE,
)
# Folded / block scalar markers we explicitly refuse, so authors get a
# clear error rather than a half-parsed description.
_UNSUPPORTED_DESC_MARKERS = {"|", ">", "|-", ">-", "|+", ">+"}


# ---------------------------------------------------------------------------
# SKILL.md helpers
# ---------------------------------------------------------------------------

def load_skill_md(path: str) -> tuple[str, str]:
    """Return (full_text, current_description).

    Enforces the single-line-scalar frontmatter contract documented at the
    top of this module: a folded (`description: >`) or block
    (`description: |`) marker is rejected with a clear error so the
    optimizer never silently writes the wrong field back.
    """
    with open(path, encoding="utf-8") as f:
        text = f.read()
    fm = _FRONTMATTER_RE.match(text)
    if not fm:
        raise SystemExit(f"{path}: missing YAML frontmatter")

    # Reject unsupported YAML scalar forms before regex misinterprets them.
    for line in fm.group(1).splitlines():
        stripped = line.strip()
        if stripped.startswith("description:"):
            raw_value = stripped[len("description:"):].strip()
            if raw_value in _UNSUPPORTED_DESC_MARKERS:
                raise SystemExit(
                    f"{path}: `description: {raw_value}` is a YAML "
                    "folded/block scalar, which optimize_description.py does "
                    "not support. Rewrite the description as a single-line "
                    "scalar (bare, single-quoted, or double-quoted), or "
                    "extend _DESC_LINE_RE before re-running this script."
                )
            break

    desc_match = _DESC_LINE_RE.search(fm.group(1))
    if not desc_match:
        raise SystemExit(f"{path}: no `description:` line in frontmatter")
    raw_value = desc_match.group("val").strip()
    quote = desc_match.group("quote")
    # YAML single-quoted scalars escape an embedded `'` by doubling it
    # (`don''t` on disk == `don't` semantically). `replace_description()`
    # writes the doubled form, so the read path must reverse it — otherwise
    # a description with a literal apostrophe round-trips as `don''t` after
    # one --apply cycle and the optimizer prompt sees the corrupted form.
    # Double quotes use `\"` escapes, which we don't currently emit.
    if quote == "'":
        raw_value = raw_value.replace("''", "'")
    return text, raw_value


def _single_line_description(value: object) -> str:
    """Collapse any whitespace (incl. newlines) to single spaces.

    The frontmatter contract (see module docstring) is *single-line scalar
    only*. An LLM-generated variant that contains a ``\\n`` would be written
    as ``description: 'foo\\nbar'`` — a half-quoted multi-line scalar that
    contradicts this script's own read-side guard. Normalising at every
    write boundary keeps the contract intact.
    """
    return " ".join(str(value).split())


def replace_description(skill_md: str, new_desc: str) -> str:
    """Replace the description line inside the frontmatter, preserving shape.

    Uses a function replacement (not a string replacement) for ``re.sub``
    because Python interprets ``\\1`` / ``\\g<name>`` in replacement strings
    as backref tokens. An LLM-generated description containing a literal
    backslash (e.g. ``Create skills for C:\\tmp\\foo``) would either be
    silently corrupted or raise ``re.error: invalid group reference``.
    See smoke_test.check_skill_md_description for the regression guard.

    Defensively collapses whitespace so the --apply path can never write a
    multi-line scalar that the read path (load_skill_md) would then refuse.
    """
    new_desc = _single_line_description(new_desc)
    # Re-quote with single quotes; escape any embedded single quotes by doubling
    quoted = "'" + new_desc.replace("'", "''") + "'"
    replacement_line = f"description: {quoted}"

    fm = _FRONTMATTER_RE.match(skill_md)
    if not fm:
        return skill_md
    fm_body = fm.group(1)
    new_fm_body = _DESC_LINE_RE.sub(
        lambda _m: replacement_line, fm_body, count=1
    )
    return skill_md[: fm.start(1)] + new_fm_body + skill_md[fm.end(1) :]


# ---------------------------------------------------------------------------
# Eval set
# ---------------------------------------------------------------------------

# Minimum queries required for a cached eval set to be considered usable
# (matches the ``len(queries) >= 10`` heuristic in
# ``_load_cached_eval_set``). Hoisted to a module constant so the
# ``--estimate-only`` path and the live load path can never disagree on
# what counts as a valid cache.
_MIN_USABLE_QUERIES = 10


def _load_cached_eval_set(eval_set_path: str) -> Optional[list[dict]]:
    """Return a usable cached query list, or None if the cache is
    missing / unparseable / under-sized.

    Shared by ``load_or_generate_eval_set`` (live path) and the
    ``--estimate-only`` cost predictor. Keeping a single source of
    truth here means ``--estimate-only`` cannot quietly under-count by
    treating a corrupt or short cache as "free", while the live path
    regenerates and pays the extra ``eval-set-gen`` call.
    """
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


def load_or_generate_eval_set(
    skill_md: str,
    eval_set_path: str,
    cfg: AgentConfig,
) -> list[dict]:
    """Load cached eval set, or generate a new one via prompts/eval-set-gen.md."""
    cached = _load_cached_eval_set(eval_set_path)
    if cached is not None:
        print(f"  Loaded {len(cached)} cached queries from {eval_set_path}")
        return cached
    if os.path.exists(eval_set_path):
        # Cache file existed but failed validation (corrupt JSON, wrong
        # shape, or fewer than _MIN_USABLE_QUERIES). Tell the user so
        # the regeneration cost is not a surprise.
        print(f"  [warn] Cached eval set at {eval_set_path} is unusable, regenerating ...")

    print("  Generating fresh 20-query eval set ...")
    user = prompts.render("eval-set-gen", skill_md=skill_md)
    raw = call_json(
        user,
        cfg=cfg,
        schema_hint='{"queries": [{"query": "...", "should_trigger": bool, "rationale": "..."}, ...]}',
    )
    queries = raw.get("queries") if isinstance(raw, dict) else None
    if not isinstance(queries, list) or len(queries) < _MIN_USABLE_QUERIES:
        raise SystemExit(
            f"eval-set-gen did not return a usable list of queries: got {type(raw).__name__}"
        )

    os.makedirs(os.path.dirname(eval_set_path) or ".", exist_ok=True)
    with open(eval_set_path, "w", encoding="utf-8") as f:
        json.dump({"queries": queries}, f, indent=2, ensure_ascii=False)
    print(f"  Saved eval set ({len(queries)} queries) to {eval_set_path}")
    return queries


# ---------------------------------------------------------------------------
# Scoring
# ---------------------------------------------------------------------------

def score_description(
    description: str,
    eval_set: list[dict],
    cfg: AgentConfig,
) -> dict:
    """Run trigger judgments per query and compute accuracy + error breakdown.

    Judge failures are excluded from the accuracy denominator rather than
    counted as False, to avoid biasing the optimizer toward descriptions
    that suppress all triggers whenever the API is degraded.
    """
    correct = 0
    fps: list[str] = []   # false positives — triggered but shouldn't have
    fns: list[str] = []   # false negatives — should have triggered but didn't
    judge_failures: list[str] = []

    for q in eval_set:
        query = q.get("query", "")
        # Strict bool check — a hand-edited or LLM-generated cache could
        # smuggle in the string "false", and bool("false") is True. Treat
        # anything that isn't a real bool as a judge failure so it lands in
        # the "excluded from denominator" bucket rather than silently
        # flipping the expected polarity for that query.
        raw_expected = q.get("should_trigger", False)
        if not isinstance(raw_expected, bool):
            print(
                f"    [warn] should_trigger is not bool ({type(raw_expected).__name__}); "
                f"excluding {query!r}"
            )
            judge_failures.append(query)
            continue
        expected = raw_expected
        user = prompts.render("trigger-judge", description=description, query=query)
        try:
            result = call_json(
                user,
                cfg=cfg,
                schema_hint='{"trigger": bool, "confidence": 0..1, "reason": "..."}',
            )
        except AgentError as e:
            print(f"    [warn] judge failed on {query!r}: {e}")
            judge_failures.append(query)
            continue  # exclude from denominator — don't penalise or credit

        # Strict bool check on the judge's reply. The schema asks for a real
        # JSON bool, but a degraded model can still return {"trigger": "false"}
        # — and `bool("false")` is True in Python. Anything that is not a
        # real bool joins the "excluded from denominator" bucket so a
        # mis-typed judgement never silently flips the score.
        raw_actual = result.get("trigger") if isinstance(result, dict) else None
        if not isinstance(raw_actual, bool):
            print(
                f"    [warn] judge `trigger` is not bool "
                f"({type(raw_actual).__name__}={raw_actual!r}); "
                f"excluding {query!r}"
            )
            judge_failures.append(query)
            continue
        actual = raw_actual

        if actual == expected:
            correct += 1
        elif actual and not expected:
            fps.append(query)
        else:
            fns.append(query)

    valid = len(eval_set) - len(judge_failures)
    return {
        "description": description,
        "accuracy": correct / valid if valid else 0.0,
        "n": valid,
        "n_total": len(eval_set),
        "false_positives": fps,
        "false_negatives": fns,
        "judge_failures": judge_failures,
    }


# ---------------------------------------------------------------------------
# Variant generation
# ---------------------------------------------------------------------------

def generate_variants(
    skill_md: str,
    n: int,
    eval_summary: str,
    cfg: AgentConfig,
) -> list[str]:
    """Generate N alternative descriptions via prompts/description-variant.md."""
    user = prompts.render(
        "description-variant", skill_md=skill_md, n=n, eval_summary=eval_summary
    )
    raw = call_json(user, cfg=cfg, schema_hint='{"variants": ["...", ...]}')
    variants = raw.get("variants") if isinstance(raw, dict) else None
    if not isinstance(variants, list):
        raise SystemExit("description-variant did not return a JSON object with `variants`")
    # Normalise to single-line scalars at the source so downstream scoring,
    # JSON history, and --apply all agree on the same canonical form.
    normalised = [_single_line_description(v) for v in variants if v and str(v).strip()]
    return [v for v in normalised if v]


def _summarize_errors(score: dict) -> str:
    fps = score.get("false_positives", [])
    fns = score.get("false_negatives", [])
    parts: list[str] = []
    if fps:
        parts.append(
            "False positives (triggered but shouldn't): "
            + "; ".join(repr(q) for q in fps[:5])
        )
    if fns:
        parts.append(
            "False negatives (missed real triggers): "
            + "; ".join(repr(q) for q in fns[:5])
        )
    if not parts:
        parts.append("Current description scores perfectly on the eval set.")
    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Optimize SKILL.md `description` for trigger precision"
    )
    parser.add_argument("--skill-root", default=".", help="Skill root dir (default: .)")
    parser.add_argument(
        "--variants", type=int, default=8,
        help="Number of description variants to try (default: 8)",
    )
    parser.add_argument(
        "--eval-set", default=None,
        help="Path to cached eval set JSON (default: data/trigger_eval_set.json)",
    )
    parser.add_argument(
        "--apply", action="store_true",
        help="Write the best description back to SKILL.md",
    )
    parser.add_argument("--model", help="Claude model override (e.g. sonnet, opus)")
    parser.add_argument("--budget", type=float, help="Max USD per claude call")
    parser.add_argument("--max-calls", type=int, default=None,
                        help="Process-wide cap on total claude calls "
                             "(also reads SKILL_BUILDER_MAX_CALLS).")
    parser.add_argument("--estimate-only", action="store_true",
                        help="Print expected call count and dollar bound, then exit (no claude calls).")
    args = parser.parse_args()

    cfg = AgentConfig(model=args.model, budget_usd=args.budget)
    if args.max_calls is not None:
        set_call_budget(args.max_calls)

    skill_root = os.path.abspath(args.skill_root)
    skill_path = os.path.join(skill_root, "SKILL.md")
    eval_set_path = args.eval_set or os.path.join(skill_root, "data", "trigger_eval_set.json")
    output_path = os.path.join(skill_root, "data", "optimized_description.json")

    if not os.path.exists(skill_path):
        print(f"SKILL.md not found at {skill_path}")
        sys.exit(1)

    skill_md, current = load_skill_md(skill_path)
    print(f"Current description:\n  {current}\n")

    if args.estimate_only:
        # Best-effort estimate without making any claude calls. Reuse the
        # same cache validator the live path uses so a corrupt /
        # short cache file is correctly treated as "regeneration
        # required" — a stale ``os.path.exists`` check would otherwise
        # under-count by one ``eval-set-gen`` call when the live path
        # regenerates.
        cached = _load_cached_eval_set(eval_set_path)
        if cached is not None:
            n_queries = len(cached)
            gen_eval_set_calls = 0
            cache_status = f"usable ({n_queries} queries)"
        else:
            n_queries = 20  # default eval-set-gen target
            gen_eval_set_calls = 1
            if os.path.exists(eval_set_path):
                cache_status = "present but unusable — will regenerate"
            else:
                cache_status = "missing — will generate"
        gen_variants_calls = 1
        score_calls = (1 + args.variants) * n_queries
        total = gen_eval_set_calls + gen_variants_calls + score_calls
        print("Cost estimate:")
        print(f"  variants                : {args.variants}")
        print(f"  trigger queries         : {n_queries}")
        print(f"  cached eval set         : {cache_status}")
        print(f"  generate eval-set calls : {gen_eval_set_calls}")
        print(f"  generate variants calls : {gen_variants_calls}")
        print(f"  score calls             : (1 + {args.variants}) × {n_queries} = {score_calls}")
        print(f"  estimated total calls   : {total}")
        if cfg.budget_usd is not None:
            print(f"  upper-bound spend       : <= ${total * cfg.budget_usd:.2f}  "
                  f"(per-call cap × calls)")
        print("\n--estimate-only: not running optimizer.")
        return

    print("Loading eval set ...")
    eval_set = load_or_generate_eval_set(skill_md, eval_set_path, cfg)
    print(f"  estimated remaining calls: ~{(1 + args.variants) * len(eval_set) + 1} "
          f"(score current + generate variants + score variants)")
    print()

    print("Scoring current description ...")
    current_score = score_description(current, eval_set, cfg)
    failures = len(current_score.get("judge_failures", []))
    failure_note = f", {failures} judge failure(s) excluded" if failures else ""
    print(
        f"  accuracy: {current_score['accuracy']:.2f}  "
        f"(FP={len(current_score['false_positives'])}, "
        f"FN={len(current_score['false_negatives'])}"
        f"{failure_note})\n"
    )

    print(f"Generating {args.variants} variant(s) ...")
    error_summary = _summarize_errors(current_score)
    try:
        variants = generate_variants(skill_md, args.variants, error_summary, cfg)
    except SystemExit:
        print("[error] variant generation failed — aborting")
        raise
    print(f"  generated {len(variants)} variant(s)\n")

    history = [current_score]
    print("Scoring variants ...")
    for i, v in enumerate(variants, 1):
        print(f"  [{i}/{len(variants)}] {v[:80]}{'...' if len(v) > 80 else ''}")
        s = score_description(v, eval_set, cfg)
        failures_v = len(s.get("judge_failures", []))
        failure_note_v = f" ({failures_v} failures excluded)" if failures_v else ""
        print(f"    accuracy: {s['accuracy']:.2f}{failure_note_v}")
        history.append(s)

    # Pick best: max accuracy; tie-break in favor of `current` (stay-the-same wins ties)
    best = max(
        history,
        key=lambda h: (h["accuracy"], h is current_score),
    )

    result = {
        "current": current_score,
        "best": best,
        "n_variants_tried": len(variants),
        "all_history": history,
    }

    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {output_path}")
    print(f"Best accuracy: {best['accuracy']:.2f}")
    print(f"Best description:\n  {best['description']}")
    print(f"Actual claude calls: {get_call_count()}")

    if args.apply:
        if best is current_score:
            print("\n(best == current; nothing to apply)")
        else:
            new_md = replace_description(skill_md, best["description"])
            with open(skill_path, "w", encoding="utf-8") as f:
                f.write(new_md)
            print(f"\nApplied best description to {skill_path}")
            print("Review the diff before committing.")


if __name__ == "__main__":
    main()
