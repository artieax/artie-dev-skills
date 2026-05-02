"""
delegate.py — stdout-delegate helper for skill scripts (Mode D, copyable)

Scripts call llm_invoke() to emit __LLM_DELEGATE__ directives.
The host agent (Claude Code, or any Mode-D-aware provider) reads the script's
stdout and executes each directive: calls the LLM, writes the result to `out`.

Copy this file into your skill's scripts/ directory, or inline the single
print statement — no external dependencies needed.

Design note: this file is a lightweight copy-and-paste helper. The canonical
implementation and full read-back utilities (read_result, read_json, state
helpers) live in scripts/agent.py, which is the SSOT for the wire format.
If the __LLM_DELEGATE__ format ever changes, update agent.py::call_emit()
first, then mirror the change here.

Usage:
    from delegate import llm_invoke

    llm_invoke(
        "Summarise this diff in one sentence: " + diff_text,
        out="tmp/summary.txt",
    )

    llm_invoke(
        "Classify as feat/fix/chore. Reply with JSON: {label: ...}",
        json_mode=True,
        out="tmp/label.json",
    )
"""

from __future__ import annotations
import json
import sys
from typing import Optional


def llm_invoke(
    prompt: str,
    *,
    out: Optional[str] = None,
    system: Optional[str] = None,
    json_mode: bool = False,
    id: Optional[str] = None,
) -> None:
    """
    Emit a single __LLM_DELEGATE__ directive to stdout.

    The host agent reads this after the script exits and:
      1. Calls the LLM with `prompt` (prepending `system` if given).
      2. If `json_mode=True`, requests JSON output.
      3. Writes the response to `out` (creating parent dirs as needed).

    Parameters
    ----------
    prompt    : Instruction for the LLM.
    out       : File path to write the LLM response into.
    system    : System prompt to prepend.
    json_mode : Request JSON output from the LLM.
    id        : Label so the workflow step can reference this result by name.
    """
    d: dict = {"prompt": prompt}
    if out is not None:
        d["out"] = out
    if system is not None:
        d["system"] = system
    if json_mode:
        d["json"] = True
    if id is not None:
        d["id"] = id
    print(f"__LLM_DELEGATE__: {json.dumps(d, ensure_ascii=False)}", flush=True)
