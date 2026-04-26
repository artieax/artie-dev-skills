"""
agent.py — Mode A (subprocess) backend for the skill-builder pipeline

A small layer on top of the `claude` CLI that gives scripts an agent feel
without pulling in the SDK or an API key. Supports:

  - JSON output mode with parse + auto-repair retry
  - System prompts loaded from prompts/*.md
  - Optional tool allowlist + extra working directories
  - Multi-turn chains where each turn's reply is available to the next
  - Cost cap (--max-budget-usd) and model override

This module is one of three interchangeable backends for the same set of
prompts in `../prompts/`:

  Mode A (this file)   — claude -p subprocess. CI / cron / batch.
  Mode B (host LLM)    — Task subagent in background (Claude Code only).
  Mode C (host LLM)    — inline rendering by the host LLM. Universal default.

You only need this file when the host shell can run `claude` (Claude Code,
or an environment with the CLI installed). Codex / Cursor / Gemini /
OpenCode users default to Mode C and don't import this module at all —
the prompts in `../prompts/` are the SSOT and can be rendered by any agent.

Why a wrapper: `subprocess.run(["claude", "-p", ...])` works for one shot
but starts to leak (shell-quoting, ad-hoc JSON parsing, no retry) once you
have a SCAFFOLD → SCORE → CRITIQUE → REFINE pipeline. This collects that
machinery in one place.

Stdlib only. Requires `claude` CLI on PATH.

Quick usage:

    from agent import call, call_json, chain
    import prompts

    # one-shot text
    out = call(
        prompts.render("scaffold-user", description="...", requirements="..."),
        system=prompts.load("scaffold-system"),
    )

    # one-shot JSON with auto-repair
    scores = call_json(
        prompts.render("score", scaffold=skill_md),
        schema_hint='{"trigger_precision": N, ...}',
    )

    # multi-turn chain (each turn sees prior turn outputs in `ctx`)
    result = chain([
        ("scaffold", lambda ctx: prompts.render("scaffold-user", ...)),
        ("score",    lambda ctx: prompts.render("score", scaffold=ctx["scaffold"])),
    ], system=prompts.load("scaffold-system"))

CLI: also runs as a script for ad-hoc smoke tests.

    python scripts/agent.py --prompt-name score --var scaffold='...' --json
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import shutil
import subprocess
import sys
from typing import Any, Callable, Optional

# Make `prompts` importable when running as `python scripts/agent.py`
sys.path.insert(0, os.path.dirname(__file__))
import prompts  # noqa: E402


# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

@dataclasses.dataclass
class AgentConfig:
    """
    Settings shared across calls. Construct once, pass into call() / chain()
    via cfg=, or rely on the module-level DEFAULT.

    Tool gating uses two fields, not one, so an empty-string default never
    accidentally degrades into "pass --tools '' and hope the CLI keeps
    interpreting that as 'no tools'":

      - tools: str = ""              → only sent on the CLI when truthy
      - disable_tools: bool = True   → when True, sends `--tools ""` explicitly

    Default is `tools="", disable_tools=True` — same effective behaviour as
    before (no tools), but the intent is now declared rather than inferred.
    Set `disable_tools=False, tools="Read,Bash(git *)"` to allow specific
    tools; set `disable_tools=False, tools=""` to defer to whatever the CLI
    treats as default.
    """

    model: Optional[str] = None              # e.g. "sonnet", "opus", or full model id
    tools: str = ""                          # allow-list, e.g. "Read,Bash(git *)"; ignored when empty (see disable_tools)
    disable_tools: bool = True               # True = explicitly send `--tools ""` (no tools); False = defer to CLI default unless tools is non-empty
    allow_dirs: tuple[str, ...] = ()         # extra dirs to grant tool access to
    bare: bool = False                       # opt-in: hermetic mode requires ANTHROPIC_API_KEY (OAuth/keychain are bypassed)
    budget_usd: Optional[float] = None       # hard cap per call (USD)
    permission_mode: Optional[str] = None    # explicit opt-in only (e.g. "auto"); None = cli default
    extra_args: tuple[str, ...] = ()         # escape hatch for flags we don't model
    autonomous: bool = True                  # True = batch/cron (never-ask); False = structured-failure on missing info
    timeout_s: int = 180                     # subprocess.run timeout per call; raise AgentError on TimeoutExpired


DEFAULT = AgentConfig()


# Process-wide soft cap on `claude -p` invocations. Set via set_call_budget()
# or the SKILL_BUILDER_MAX_CALLS env var. None means unlimited.
_MAX_CALLS: Optional[int] = None
_CALL_COUNT: int = 0


def set_call_budget(max_calls: Optional[int]) -> None:
    """Cap total claude calls in this process. None = unlimited; resets counter."""
    global _MAX_CALLS, _CALL_COUNT
    _MAX_CALLS = max_calls
    _CALL_COUNT = 0


def get_call_count() -> int:
    """Number of claude calls made so far in this process."""
    return _CALL_COUNT


def _env_max_calls() -> Optional[int]:
    raw = os.environ.get("SKILL_BUILDER_MAX_CALLS", "").strip()
    if not raw:
        return None
    try:
        return max(0, int(raw))
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------

class AgentError(RuntimeError):
    """Raised when `claude -p` exits non-zero or returns unparseable output."""


# ---------------------------------------------------------------------------
# Core call
# ---------------------------------------------------------------------------

_NEVER_ASK_PREFIX = (
    "You are running in fully automated batch mode. "
    "Never ask the user any clarifying questions. "
    "Make all decisions autonomously based on the information provided.\n\n"
)

# Used when autonomous=False: surface gaps rather than invent or block silently.
_STRUCTURED_FAILURE_PREFIX = (
    "If critical information is missing, do not invent it. "
    'Return JSON with: {"blocked": true, "open_questions": [...], "safe_defaults": {...}}\n\n'
)


def _build_argv(
    cfg: AgentConfig,
    system: Optional[str],
    json_mode: bool,
) -> list[str]:
    argv: list[str] = ["claude", "-p"]
    if cfg.bare:
        argv.append("--bare")
    if cfg.model:
        argv += ["--model", cfg.model]
    # Two-step tool gating — see AgentConfig docstring.
    # 1) An explicit non-empty allow-list always wins.
    # 2) Otherwise honor disable_tools to send `--tools ""` only on intent.
    if cfg.tools:
        argv += ["--tools", cfg.tools]
    elif cfg.disable_tools:
        argv += ["--tools", ""]
    for d in cfg.allow_dirs:
        argv += ["--add-dir", d]
    if cfg.budget_usd is not None:
        argv += ["--max-budget-usd", str(cfg.budget_usd)]
    if cfg.permission_mode is not None:
        argv += ["--permission-mode", cfg.permission_mode]
    if json_mode:
        argv += ["--output-format", "json"]
    prefix = _NEVER_ASK_PREFIX if cfg.autonomous else _STRUCTURED_FAILURE_PREFIX
    merged_system = prefix + (system or "")
    argv += ["--append-system-prompt", merged_system]
    argv += list(cfg.extra_args)
    return argv


def call(
    prompt: str,
    *,
    system: Optional[str] = None,
    cfg: Optional[AgentConfig] = None,
    json_mode: bool = False,
) -> str:
    """
    Single-turn call to `claude -p`. Returns the raw text response.

    With json_mode=True, returns the value of the `result` field from
    claude's JSON envelope (still as a string — JSON parsing is the
    caller's responsibility, or use call_json()).

    Per-call timeout is `cfg.timeout_s` (default 180s). On TimeoutExpired the
    underlying process is killed and an AgentError is raised — that's why
    we don't fall through to the "non-zero exit" branch on timeout.
    Process-wide soft cap on calls is enforced before each call (see
    `set_call_budget`); when exceeded, an AgentError is raised before
    `claude` is even invoked.
    """
    global _CALL_COUNT

    cfg = cfg or DEFAULT
    if shutil.which("claude") is None:
        raise AgentError("`claude` CLI not found on PATH")

    cap = _MAX_CALLS if _MAX_CALLS is not None else _env_max_calls()
    if cap is not None and _CALL_COUNT >= cap:
        raise AgentError(
            f"call budget exceeded ({_CALL_COUNT} >= {cap}); raise via "
            f"set_call_budget() or SKILL_BUILDER_MAX_CALLS"
        )
    _CALL_COUNT += 1

    argv = _build_argv(cfg, system, json_mode=json_mode)
    try:
        # Force UTF-8 across the subprocess boundary. `text=True` alone
        # delegates to `locale.getpreferredencoding(False)`, which is
        # cp1252 on Windows and cp932 on Japanese Windows — both of which
        # raise UnicodeDecodeError on the em dashes / arrows / ≥ glyphs
        # used throughout the prompt templates.
        proc = subprocess.run(
            argv,
            input=prompt,
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=cfg.timeout_s,
        )
    except subprocess.TimeoutExpired as e:
        raise AgentError(
            f"claude timed out after {cfg.timeout_s}s\n"
            f"argv: {argv[:6]}...\n"
            f"partial stderr: {(e.stderr or '')[-500:] if isinstance(e.stderr, str) else ''}"
        ) from e
    if proc.returncode != 0:
        raise AgentError(
            f"claude exited {proc.returncode}\n"
            f"argv: {argv[:6]}...\n"
            f"stderr: {proc.stderr.strip()[:500]}"
        )

    out = proc.stdout.strip()
    if not json_mode:
        return out

    try:
        envelope = json.loads(out)
    except json.JSONDecodeError as e:
        raise AgentError(f"could not parse claude JSON envelope: {e}\n{out[:500]}")
    return str(envelope.get("result", "")).strip()


# ---------------------------------------------------------------------------
# JSON convenience with auto-repair
# ---------------------------------------------------------------------------

def _extract_json_object(text: str) -> Optional[dict]:
    """Pull the first balanced {...} object out of a string, or None."""
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


def call_json(
    prompt: str,
    *,
    system: Optional[str] = None,
    cfg: Optional[AgentConfig] = None,
    schema_hint: str = "{...}",
    repair: bool = True,
) -> dict:
    """
    Single-turn JSON call with one repair attempt on parse failure.

    Tries `--output-format json` first (claude wraps the response in an
    envelope; we extract `.result` and JSON-parse it). If that fails, asks
    the model to re-emit valid JSON using the repair-json prompt.
    """
    raw = call(prompt, system=system, cfg=cfg, json_mode=True)
    obj = _extract_json_object(raw)
    if obj is not None:
        return obj
    if not repair:
        raise AgentError(f"response was not valid JSON: {raw[:300]}")

    repair_prompt = prompts.render(
        "repair-json", bad_output=raw, schema_hint=schema_hint
    )
    raw2 = call(repair_prompt, system=system, cfg=cfg, json_mode=True)
    obj = _extract_json_object(raw2)
    if obj is None:
        raise AgentError(
            f"repair attempt also failed.\nfirst: {raw[:200]}\nsecond: {raw2[:200]}"
        )
    return obj


# ---------------------------------------------------------------------------
# Multi-turn chain
# ---------------------------------------------------------------------------

Turn = tuple[str, Callable[[dict[str, Any]], str]]


def chain(
    turns: list[Turn],
    *,
    system: Optional[str] = None,
    cfg: Optional[AgentConfig] = None,
    json_turns: Optional[set[str]] = None,
    on_turn: Optional[Callable[[str, str], None]] = None,
) -> dict[str, Any]:
    """
    Run a sequence of named turns, passing accumulated outputs forward.

    Each turn is `(name, prompt_fn)`. `prompt_fn(ctx)` builds the prompt
    string from prior turn outputs (`ctx[turn_name] = output`).

    Turns whose name is in `json_turns` are parsed as JSON; their value in
    ctx is the parsed dict. Other turns store the raw string.

    Returns the full ctx dict so the caller can inspect every step.

    Note: this is *sequential*, not session-resumed. Each turn is its own
    `claude -p` call — claude does not see prior turns directly, only what
    you concatenate into the next prompt. That's the point: cheap, stateless,
    easy to debug. Use `--resume` machinery if you need true conversation
    continuity, but most pipelines here don't.
    """
    json_turns = json_turns or set()
    ctx: dict[str, Any] = {}
    for name, build in turns:
        prompt = build(ctx)
        if name in json_turns:
            value: Any = call_json(prompt, system=system, cfg=cfg)
        else:
            value = call(prompt, system=system, cfg=cfg)
        ctx[name] = value
        if on_turn:
            on_turn(name, value if isinstance(value, str) else json.dumps(value))
    return ctx


# ---------------------------------------------------------------------------
# CLI smoke test
# ---------------------------------------------------------------------------

def _parse_var(spec: str) -> tuple[str, str]:
    if "=" not in spec:
        raise SystemExit(f"--var expects key=value, got: {spec}")
    k, _, v = spec.partition("=")
    return k.strip(), v


def main() -> None:
    parser = argparse.ArgumentParser(description="Smoke test agent.py via claude -p")
    parser.add_argument("--prompt", help="Inline prompt text. Mutually exclusive with --prompt-name.")
    parser.add_argument("--prompt-name", help="Name of a prompt under prompts/.")
    parser.add_argument("--system-name", help="Name of a system prompt under prompts/.")
    parser.add_argument("--var", action="append", default=[], help="key=value (repeatable) for --prompt-name rendering.")
    parser.add_argument("--json", action="store_true", help="Parse response as JSON via call_json().")
    parser.add_argument("--model", help="Model override (e.g. sonnet, opus).")
    parser.add_argument("--budget", type=float, help="Max USD per call.")
    parser.add_argument("--timeout", type=int, default=180,
                        help="Per-call timeout in seconds (default: 180).")
    parser.add_argument("--max-calls", type=int, default=None,
                        help="Process-wide cap on claude calls "
                             "(also reads SKILL_BUILDER_MAX_CALLS).")
    args = parser.parse_args()

    if (args.prompt is None) == (args.prompt_name is None):
        parser.error("provide exactly one of --prompt or --prompt-name")

    if args.max_calls is not None:
        set_call_budget(args.max_calls)

    vars_ = dict(_parse_var(s) for s in args.var)
    body = args.prompt if args.prompt is not None else prompts.render(args.prompt_name, **vars_)
    system = prompts.load(args.system_name) if args.system_name else None

    cfg = AgentConfig(model=args.model, budget_usd=args.budget, timeout_s=args.timeout)

    if args.json:
        result = call_json(body, system=system, cfg=cfg)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    else:
        print(call(body, system=system, cfg=cfg))


if __name__ == "__main__":
    main()
