"""
prompts.py — load markdown prompts from skills/skill-builder/prompts/

Each prompt is a markdown file with optional YAML frontmatter (name, role,
description, vars). The body uses {{var}} placeholders rendered by `render()`.

Why a custom loader: keeps prompts reviewable as plain markdown (good diffs,
no Python triple-quoted strings, no escape headaches), while still allowing
runtime variable injection. Frontmatter is metadata only — it is stripped
before rendering.

Usage:
    from prompts import load, render

    tmpl = load("score")                  # str — body with {{var}} placeholders
    text = render("score", scaffold=...)  # str — placeholders filled in

    p = load_meta("score")                # dict — frontmatter (name, vars, ...)

The module is stdlib-only.
"""

from __future__ import annotations

import os
import re
from typing import Any

PROMPTS_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "prompts")

_FRONTMATTER_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}")


def _read(name: str) -> str:
    path = os.path.join(PROMPTS_DIR, f"{name}.md")
    if not os.path.exists(path):
        raise FileNotFoundError(f"prompt not found: {path}")
    # Force UTF-8 on read — prompt bodies use em dashes, arrows, ≥, etc.,
    # and locale-default decoding (e.g. cp932 on Windows) corrupts them.
    with open(path, encoding="utf-8") as f:
        return f.read()


def _split_frontmatter(text: str) -> tuple[str, str]:
    m = _FRONTMATTER_RE.match(text)
    if not m:
        return "", text
    return m.group(1), text[m.end() :]


def _parse_yaml_lite(fm: str) -> dict[str, Any]:
    """
    Minimal YAML parser for the small frontmatter we actually use:
      - top-level scalars: `key: value`
      - lists of strings: `- item`
      - block scalars: `key: |` followed by indented lines
    Avoids a PyYAML dependency for stdlib-only scripts.
    """
    out: dict[str, Any] = {}
    cur_list_key: str | None = None
    block_key: str | None = None
    block_lines: list[str] = []

    for raw in fm.splitlines():
        line = raw.rstrip()
        if not line.strip():
            if block_key is not None:
                block_lines.append("")
            continue

        if block_key is not None:
            if raw.startswith("  "):
                block_lines.append(raw[2:])
                continue
            out[block_key] = "\n".join(block_lines).rstrip()
            block_key, block_lines = None, []

        if cur_list_key is not None and line.lstrip().startswith("- "):
            out[cur_list_key].append(line.lstrip()[2:].strip())
            continue
        cur_list_key = None

        if ":" in line:
            key, _, value = line.partition(":")
            key = key.strip()
            value = value.strip()
            if value == "":
                cur_list_key = key
                out[key] = []
            elif value == "|":
                block_key = key
                block_lines = []
            else:
                out[key] = value

    if block_key is not None:
        out[block_key] = "\n".join(block_lines).rstrip()

    return out


def load(name: str) -> str:
    """Return the prompt body (frontmatter stripped, placeholders intact)."""
    _, body = _split_frontmatter(_read(name))
    return body.rstrip() + "\n"


def load_meta(name: str) -> dict[str, Any]:
    """Return parsed frontmatter for `name` (empty dict if none)."""
    fm, _ = _split_frontmatter(_read(name))
    return _parse_yaml_lite(fm) if fm else {}


def render(name: str, *, strict: bool = False, **vars: Any) -> str:
    """
    Load a prompt and substitute {{placeholders}}.

    By default, missing vars become empty strings — same forgiving behavior
    as f-string-with-defaultdict, so a template can declare optional
    sections without raising. This forgiving default also makes typos
    invisible: ``{{descripton}}`` quietly becomes ``""`` and downstream
    callers never notice. Use ``strict=True`` from CI / smoke checks to
    raise ``KeyError`` on any placeholder that wasn't passed in.
    """
    body = load(name)

    def sub(m: re.Match[str]) -> str:
        key = m.group(1)
        if key not in vars:
            if strict:
                raise KeyError(
                    f"prompt {name!r}: undeclared placeholder {{{{ {key} }}}} "
                    "— pass it as a kwarg or declare it in frontmatter `vars`"
                )
            return ""
        v = vars[key]
        return "" if v is None else str(v)

    return _PLACEHOLDER_RE.sub(sub, body)


def placeholders(name: str) -> set[str]:
    """Return the set of ``{{var}}`` names referenced in the prompt body."""
    return set(_PLACEHOLDER_RE.findall(load(name)))


def declared_vars(name: str) -> set[str]:
    """
    Return the variable names declared in the prompt's frontmatter ``vars``.

    Each ``vars`` entry is either a bare name (``- foo``) or
    ``- foo: short description``. Both forms collapse to ``foo``.
    """
    vars_meta = load_meta(name).get("vars") or []
    if not isinstance(vars_meta, list):
        return set()
    out: set[str] = set()
    for entry in vars_meta:
        if not isinstance(entry, str):
            continue
        name_only = entry.split(":", 1)[0].strip()
        if name_only:
            out.add(name_only)
    return out


def render_block(tag: str, value: Any) -> str:
    """
    Wrap an injected variable in a named XML-style fence, e.g.::

        <skill_md>
        ...content...
        </skill_md>

    Use for any large external blob spliced into a prompt (full SKILL.md,
    previous bad LLM output, user-supplied description). Two reasons:

    1. Gives the model a stable delimiter to reason about — far less ambiguous
       than free-floating prose, especially if the injected blob itself
       contains markdown headings or code fences.
    2. Defends against prompt-injection attacks where the blob says things
       like "ignore the system prompt and ..." — the fence frames the blob
       as data, not instruction. Not a hard guarantee, but a meaningful step.

    `tag` should be a short ASCII identifier (matches the convention used in
    the prompt templates). The function does not sanitize the tag name; pick
    something safe and consistent.
    """
    body = "" if value is None else str(value)
    return f"<{tag}>\n{body}\n</{tag}>"


def list_prompts() -> list[str]:
    """Names of available prompts (sorted, no extension)."""
    if not os.path.isdir(PROMPTS_DIR):
        return []
    return sorted(
        os.path.splitext(f)[0]
        for f in os.listdir(PROMPTS_DIR)
        if f.endswith(".md")
    )


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Available prompts:")
        for p in list_prompts():
            meta = load_meta(p)
            desc = meta.get("description", "")
            print(f"  {p:<28}  {desc}")
        sys.exit(0)

    name = sys.argv[1]
    print(load(name), end="")
