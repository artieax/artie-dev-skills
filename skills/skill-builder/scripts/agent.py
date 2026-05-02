"""
agent.py — Mode D stdout-delegate backend for skill scripts

Scripts import call_emit / read_result / read_json and use a two-phase
pattern instead of the old Mode A subprocess approach:

  Phase 1 (emit)  — script calls call_emit() to emit __LLM_DELEGATE__
                    directives, writes a state file, then exits.
  Phase 2 (read)  — host has processed the directives; script re-runs,
                    calls read_result() / read_json() to consume outputs.

No claude CLI, no API key, no subprocess needed. The host agent (Claude
Code, or any Mode-D-aware provider) handles the LLM calls.

Compatibility note: this file replaces the old Mode A subprocess wrapper.
Code that previously did `result = call(prompt, system=sys)` must be
restructured into the emit → re-run → read pattern described in
references/scaffold/atoms/stdout-delegate.md.

Stdlib only.
"""

from __future__ import annotations

import json
import os
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Emit
# ---------------------------------------------------------------------------

def call_emit(
    prompt: str,
    out: str,
    *,
    system: Optional[str] = None,
    json_mode: bool = False,
    id: Optional[str] = None,
) -> str:
    """
    Emit a single __LLM_DELEGATE__ directive and return `out`.

    The host processes the directive after the script exits:
      1. Calls the LLM with `prompt` (prepending `system` if given).
      2. If `json_mode=True`, requests JSON output.
      3. Writes the response to `out` (creating parent dirs as needed).

    Returns `out` so callers can chain:
        handle = call_emit(prompt, out="tmp/foo.md")
        # ...script exits, host processes, script re-runs...
        text = read_result(handle)
    """
    d: dict = {"prompt": prompt, "out": out}
    if system is not None:
        d["system"] = system
    if json_mode:
        d["json"] = True
    if id is not None:
        d["id"] = id
    print(f"__LLM_DELEGATE__: {json.dumps(d, ensure_ascii=False)}", flush=True)
    return out


# ---------------------------------------------------------------------------
# Read
# ---------------------------------------------------------------------------

def result_exists(out: str) -> bool:
    """Return True if the host has already processed the directive for `out`."""
    return os.path.exists(out)


def read_result(out: str) -> str:
    """Read and return the LLM response written by the host to `out`."""
    with open(out, encoding="utf-8") as f:
        return f.read().strip()


def read_json(out: str) -> dict[str, Any]:
    """Read and parse the JSON LLM response written by the host to `out`.

    Extracts the first balanced `{...}` object from the file, so it works
    even if the host wraps the JSON in prose.
    """
    text = read_result(out)
    obj = _extract_json_object(text)
    if obj is None:
        raise ValueError(f"No JSON object found in {out!r}: {text[:200]}")
    return obj


def _extract_json_object(text: str) -> Optional[dict]:
    start = text.find("{")
    if start == -1:
        return None
    depth = 0
    in_str = False
    esc = False
    for i in range(start, len(text)):
        ch = text[i]
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    return None
    return None


# ---------------------------------------------------------------------------
# State helpers (for phased scripts)
# ---------------------------------------------------------------------------

def save_state(path: str, state: dict) -> None:
    """Atomically write state dict to `path` as JSON."""
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    tmp = path + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


def load_state(path: str) -> Optional[dict]:
    """Load state from `path`, or None if the file doesn't exist."""
    if not os.path.exists(path):
        return None
    with open(path, encoding="utf-8") as f:
        return json.load(f)
