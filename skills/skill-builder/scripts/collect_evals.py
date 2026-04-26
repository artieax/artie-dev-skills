"""
collect_evals.py — accumulate eval.json + SKILL.md pairs into data/evals.jsonl

`--skill-root` always points at a SINGLE skill — i.e. skills/<name>/ — and
NOT at the parent skills/ directory. The script reads
<skill-root>/projects/<name>/v*/eval.json and writes
<skill-root>/data/evals.jsonl. Pointing it at skills/ silently scans nothing
and produces an empty cache at skills/data/evals.jsonl, which is the
exact footgun the warning in SKILL.md ("Form A run from repo root")
calls out.

Scans all projects/<skill>/v*/eval.json, pairs each with:
  - skill_md:    the SKILL.md *snapshot* at that version (what was actually
                 scored). Resolution order:
                   1. projects/<name>/v<N>/skill.md  (explicit snapshot)
                   2. git show <commit>:skills/<name>/SKILL.md, where commit
                      is the one that introduced this v<N>/eval.json
                   3. (none) — record is still written; optimizer skips it
  - change_notes: the v<N>/input.md (what triggered this version — change log)

The previous schema stored input.md as `input_md`. That field is preserved as
`change_notes` for clarity; downstream readers should prefer `skill_md`.

Modes:
  - default   append-only. Skip records whose `id` is already in
              data/evals.jsonl. Cheap, idempotent, never deletes.
  - --force   re-collect records whose `id` already exists; new records
              for those ids replace the old ones. Use after editing an
              existing v<N>/eval.json or v<N>/skill.md snapshot.
  - --rebuild ignore the existing file entirely; rebuild the cache from
              scratch via an atomic .tmp + rename so a crashed mid-write
              never leaves a half-written cache. Use whenever the cache
              has drifted from projects/* (file was hand-edited, schema
              changed, or you just don't trust it).

Usage:
    python scripts/collect_evals.py [--skill-root .]
    python scripts/collect_evals.py --skill-root skills/skill-builder
    python scripts/collect_evals.py --rebuild        # safe full rebuild
    python scripts/collect_evals.py --force          # replace duplicate ids in place

Output (data/evals.jsonl):
    One JSON record per line:
    {
        "id": "skill-builder/v1",
        "skill_name": "skill-builder",
        "version": "v1",
        "date": "2026-04-25",
        "skill_md": "---\\nname: skill-builder\\n...",  # what was scored
        "change_notes": "# v1 — input\\n...",            # change log
        "scores": { "trigger_precision": 6, ... },
        "total": 33,
        "notes": "..."
    }
"""

import argparse
import glob
import json
import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional


def _read_if_exists(path: str) -> str:
    if not os.path.exists(path):
        return ""
    # Force UTF-8: SKILL.md / input.md routinely contain em dashes, arrows,
    # ≥, and other non-ASCII glyphs. Relying on locale defaults silently
    # corrupts them on Windows (cp1252 / cp932) and breaks the optimizer's
    # snapshot fidelity.
    with open(path, encoding="utf-8") as f:
        return f.read()


def _resolve_skill_snapshot(
    skill_root: str, skill_name: str, version_dir: str, eval_file: str
) -> str:
    """
    Resolve the SKILL.md content as it existed when this eval was scored.

    Order:
      1. <version_dir>/skill.md           (explicit snapshot — preferred)
      2. git show <commit>:<skill>/SKILL.md
         where <commit> is the commit that added v<N>/eval.json
      3. "" (caller emits a warning; record is still written)
    """
    # 1. explicit snapshot
    snap = _read_if_exists(os.path.join(version_dir, "skill.md"))
    if snap:
        return snap

    # 2. git history — find the commit that introduced this eval.json
    rel_eval = os.path.relpath(eval_file, skill_root)
    try:
        # Walk skill_root upward to find the git toplevel
        git_top = subprocess.check_output(
            ["git", "-C", skill_root, "rev-parse", "--show-toplevel"],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        rel_eval_repo = os.path.relpath(eval_file, git_top)
        rel_skill_repo = os.path.relpath(
            os.path.join(skill_root, "SKILL.md"), git_top
        )
        commit = subprocess.check_output(
            ["git", "-C", git_top, "log", "-n", "1", "--diff-filter=A",
             "--format=%H", "--", rel_eval_repo],
            stderr=subprocess.DEVNULL, text=True,
        ).strip()
        if not commit:
            return ""
        return subprocess.check_output(
            ["git", "-C", git_top, "show", f"{commit}:{rel_skill_repo}"],
            stderr=subprocess.DEVNULL, text=True,
        )
    except subprocess.CalledProcessError:
        return ""


def _build_record(skill_root: str, eval_file: str) -> Optional[dict]:
    """Read one eval.json + its SKILL.md snapshot + input.md and shape a record.

    Returns None when the file is incomplete (missing total) or doesn't sit
    under projects/<skill>/v<N>/.
    """
    with open(eval_file, encoding="utf-8") as f:
        eval_data = json.load(f)

    # Skip null-score entries (eval pending)
    if eval_data.get("total") is None:
        return None

    # Derive names from path: projects/<skill_name>/v<N>/eval.json
    # Use relative_to(skill_root) so a "projects" dir anywhere in the
    # absolute path above skill_root doesn't cause misdetection.
    try:
        rel_parts = Path(eval_file).relative_to(skill_root).parts
    except ValueError:
        return None
    if len(rel_parts) < 4 or rel_parts[0] != "projects":
        return None
    skill_name = rel_parts[1]
    version = rel_parts[2]
    record_id = f"{skill_name}/{version}"

    version_dir = os.path.dirname(eval_file)
    change_notes = _read_if_exists(os.path.join(version_dir, "input.md"))
    skill_md = _resolve_skill_snapshot(skill_root, skill_name, version_dir, eval_file)

    if not skill_md:
        print(f"  [warn] {record_id}: no SKILL.md snapshot found "
              f"(checked v<N>/skill.md and git history) — record kept "
              f"but will be skipped by optimize.py")

    return {
        "id": record_id,
        "skill_name": skill_name,
        "version": version,
        "date": eval_data.get("date", ""),
        "skill_md": skill_md,
        "change_notes": change_notes,
        "scores": eval_data.get("scores", {}),
        "total": eval_data.get("total"),
        "pipeline": eval_data.get("pipeline", ""),
        "open_questions": eval_data.get("open_questions", eval_data.get("unclear_points", [])),
        "notes": eval_data.get("notes", ""),
    }


def _atomic_write_jsonl(records: list[dict], output_path: str) -> None:
    """Write records to output_path atomically via a sibling .tmp + os.replace.

    The .tmp lives in the same directory so os.replace() is a same-FS rename
    (no cross-device copy), which is the only thing POSIX guarantees to be
    atomic. A crashed mid-write therefore never leaves a half-written cache.
    """
    out_dir = os.path.dirname(output_path) or "."
    os.makedirs(out_dir, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=".evals.", suffix=".jsonl.tmp", dir=out_dir
    )
    try:
        # ensure_ascii=False keeps non-ASCII glyphs intact in the cache;
        # combined with encoding="utf-8" on read, the round-trip is lossless
        # regardless of locale.
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            for rec in records:
                f.write(json.dumps(rec, ensure_ascii=False) + "\n")
        os.replace(tmp_path, output_path)
    except Exception:
        # Clean up the tmp on any failure; never leave it behind.
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def _load_existing_records(output_path: str) -> list[dict]:
    """Return existing records preserving order (or [] if file missing)."""
    if not os.path.exists(output_path):
        return []
    out: list[dict] = []
    with open(output_path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def collect(
    skill_root: str,
    output_path: str,
    *,
    rebuild: bool = False,
    force: bool = False,
) -> tuple[int, int, int]:
    """Scan skill_root for eval records.

    Returns (added, replaced, skipped):
      added    — records new to data/evals.jsonl
      replaced — existing records overwritten (--force / --rebuild)
      skipped  — records left untouched because their id was already present
                 (default mode only)
    """
    pattern = os.path.join(skill_root, "projects", "*", "v*", "eval.json")
    eval_files = sorted(glob.glob(pattern))

    if rebuild:
        records: list[dict] = []
        added = replaced = skipped = 0
        for eval_file in eval_files:
            rec = _build_record(skill_root, eval_file)
            if rec is None:
                continue
            records.append(rec)
            added += 1
            print(f"  + {rec['id']}  total={rec['total']}/50")
        _atomic_write_jsonl(records, output_path)
        return added, replaced, skipped

    # Append-only modes (default + --force) — keep existing records, layer new
    # ones on top. With --force, same-id records replace the existing entry
    # in place rather than being skipped.
    existing = _load_existing_records(output_path)
    by_id: dict[str, int] = {}
    for i, rec in enumerate(existing):
        rid = rec.get("id")
        if isinstance(rid, str):
            by_id[rid] = i

    added = replaced = skipped = 0
    for eval_file in eval_files:
        rec = _build_record(skill_root, eval_file)
        if rec is None:
            continue
        rid = rec["id"]
        if rid in by_id:
            if not force:
                skipped += 1
                continue
            existing[by_id[rid]] = rec
            replaced += 1
            print(f"  ~ {rid}  total={rec['total']}/50  (replaced)")
        else:
            by_id[rid] = len(existing)
            existing.append(rec)
            added += 1
            print(f"  + {rid}  total={rec['total']}/50")

    if added or replaced:
        _atomic_write_jsonl(existing, output_path)
    return added, replaced, skipped


def main():
    parser = argparse.ArgumentParser(description="Collect eval records into data/evals.jsonl")
    parser.add_argument(
        "--skill-root",
        default=".",
        help=(
            "Root directory of a SINGLE skill — i.e. skills/<name>/, the "
            "directory that contains SKILL.md, projects/<name>/v*/eval.json, "
            "and data/evals.jsonl. NOT the parent skills/ directory. "
            "Default: current dir."
        ),
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--rebuild",
        action="store_true",
        help="Rebuild data/evals.jsonl from scratch (atomic .tmp + rename). "
             "Use after editing eval.json / skill.md snapshots.",
    )
    mode.add_argument(
        "--force",
        action="store_true",
        help="Replace any record whose id already exists in data/evals.jsonl "
             "with a freshly-collected version, instead of skipping.",
    )
    parser.add_argument(
        "--allow-missing-skill-md",
        action="store_true",
        help="Permit --skill-root to point at a directory that does not "
             "contain SKILL.md. By default this is a hard error so that "
             "running against the parent skills/ dir does not silently "
             "produce skills/data/evals.jsonl. Use only when scanning a "
             "deliberately heterogeneous tree (rare).",
    )
    args = parser.parse_args()

    skill_root = os.path.abspath(args.skill_root)
    output_path = os.path.join(skill_root, "data", "evals.jsonl")

    # Footgun guard: --skill-root must point at a single skill, not the
    # parent skills/ dir. The latter has no SKILL.md and would silently
    # scan nothing and write skills/data/evals.jsonl — exactly the
    # "Form A run from repo root" footgun called out in SKILL.md. Fail
    # by default so the mistake is loud rather than a misleading
    # empty cache; --allow-missing-skill-md is the explicit opt-out.
    if not os.path.exists(os.path.join(skill_root, "SKILL.md")):
        msg = (
            f"{skill_root}/SKILL.md not found — `--skill-root` must point "
            "at a single skill root (e.g. skills/skill-builder), not the "
            "parent skills/ directory. Pass --allow-missing-skill-md to "
            "override (rare; typically a misuse)."
        )
        if not args.allow_missing_skill_md:
            raise SystemExit(msg)
        print(f"  [warn] {msg}")

    mode_label = "rebuild" if args.rebuild else "force-replace" if args.force else "append-only"
    print(f"Scanning: {skill_root}/projects/  (mode={mode_label})")
    print(f"Output:   {output_path}")
    print()

    added, replaced, skipped = collect(
        skill_root, output_path, rebuild=args.rebuild, force=args.force
    )

    if args.rebuild:
        if added == 0:
            print("No records collected — wrote an empty data/evals.jsonl.")
        else:
            print(f"\nRebuilt {added} record(s) in {output_path}")
    elif added == 0 and replaced == 0:
        msg = "No new records found."
        if skipped:
            msg += (
                f" {skipped} existing record(s) skipped — pass --force to "
                "re-collect them, or --rebuild for a full refresh."
            )
        print(msg)
    else:
        parts: list[str] = []
        if added:
            parts.append(f"added {added}")
        if replaced:
            parts.append(f"replaced {replaced}")
        if skipped:
            parts.append(f"skipped {skipped}")
        print(f"\n{', '.join(parts)} record(s) in {output_path}")


if __name__ == "__main__":
    main()
