"""
smoke_test.py — minimal CI smoke test for the skill-builder pipeline

Designed to be runnable without network, without `claude`, without API keys,
in under a few seconds. Catches the regressions that broke past iterations:

  1. py_compile of every script — catches syntax / import errors
  2. prompts.list_prompts() returns at least the known prompts
  3. prompts.render() works end-to-end on every prompt with placeholder vars
     (including the new render_block helper). Also enforces a contract that
     guards against silent typos in body templates:
       - every {{var}} used in the body MUST appear in frontmatter `vars`
         (so a typo'd `{{descripton}}` cannot hide as an empty string)
       - every {{var}} used in the body MUST have a default in
         `_DEFAULT_VARS` (so adding a new placeholder forces a smoke
         fixture update before merge)
       - render(..., strict=True) raises on any undeclared placeholder
     (including the new render_block helper)
  4. generate_review.py renders an HTML page from an in-memory fixture
     (no real eval log required) and includes the fixture's skill name
  5. generate_review.render_html() neutralises HTML in score / total fields
     (XSS regression guard — the JS template concatenates these into
     innerHTML, so anything stringy must be coerced to a number on the
     Python side)
  5b. generate_review.render_html() escapes attribute-context characters
     in fields that flow into HTML attributes (entry id, version,
     pipeline). Regression guard for entry.id strings like
     `x" autofocus onfocus="alert(1)` breaking out of `data-id="..."`.
  6. agent.call_emit() emits a correctly-formatted __LLM_DELEGATE__ line
     (Mode D stdout-delegate — no subprocess, no API key needed).
  7. optimize_description.load_skill_md() parses the live SKILL.md and the
     description is a single-line scalar (the parser does not yet handle
     folded / block YAML scalars — see references/scaffold/atoms/orchestrator.md).
     Also verifies that replace_description() collapses multi-line input to
     a single-line scalar (--apply must never write a half-quoted multi-line
     description that load_skill_md would then refuse).
  8. references/dependency-graph.md only references skills that actually
     exist as skills/<name>/SKILL.md on disk — catches stale edges after a
     rename (e.g. "pluginize → skill-creator" when the dir is skill-builder)
  9. collect_evals.collect() against a synthetic temp skill root: stages
     SKILL.md + projects/<name>/v1/{eval.json, input.md, skill.md} and
     asserts data/evals.jsonl has exactly one record with skill_md /
     change_notes / total populated. Locks the producer-side schema that
     optimize.py / generate_review.py / tune_thresholds.py read from.
 10. collect_evals.main(): pointing --skill-root at a directory without
     SKILL.md raises SystemExit (footgun guard for "Form A from repo
     root"); --allow-missing-skill-md downgrades it to a warning.
 11. optimize_description._load_cached_eval_set is the single cache
     validator shared by both --emit-eval-set and the live path, so a
     corrupt / under-sized cache cannot trigger an unnecessary regeneration.
 12. tune_thresholds.simulate() must NOT plateau on a regressing
     sequence (improvement < 0) or on a per-metric regression even
     when the weighted average improved — the previous gate fired on
     both, freezing strictly worse skills as "done".
 13. optimize._coerce_metric and _score_from_dict handle non-numeric
     inputs correctly.

Exit non-zero on any failure with a clear marker message. Stdlib only.

Usage:
    python skills/skill-builder/scripts/smoke_test.py
    python skills/skill-builder/scripts/smoke_test.py --skill-root skills/skill-builder
"""

from __future__ import annotations

import argparse
import io
import json
import os
import py_compile
import re
import sys
import tempfile
import textwrap
import traceback
from pathlib import Path


def _scripts_dir(skill_root: Path) -> Path:
    return skill_root / "scripts"


def check_py_compile(skill_root: Path) -> list[str]:
    failures: list[str] = []
    for script in sorted(_scripts_dir(skill_root).glob("*.py")):
        try:
            py_compile.compile(str(script), doraise=True)
        except py_compile.PyCompileError as e:
            failures.append(f"py_compile failed: {script.name}: {e.msg}")
    return failures


def check_prompts(skill_root: Path) -> list[str]:
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import prompts  # noqa: WPS433 — by design at runtime
    except Exception as e:  # noqa: BLE001
        return [f"failed to import prompts module: {e}"]

    names = prompts.list_prompts()
    expected = {
        "score",
        "scaffold-system",
        "scaffold-user",
        "repair-json",
        "scaffold-fewshot-item",
        "trigger-judge",
        "description-variant",
        "eval-set-gen",
        "critique",
        "refine",
        "assertion-grader",
    }
    missing = expected - set(names)
    if missing:
        failures.append(f"prompts.list_prompts() missing: {sorted(missing)}")

    default_var_names = set(_DEFAULT_VARS)
    for name in names:
        try:
            used = prompts.placeholders(name)
        except Exception as e:  # noqa: BLE001
            failures.append(f"prompts.placeholders({name!r}) raised: {e}")
            continue
        try:
            declared = prompts.declared_vars(name)
        except Exception as e:  # noqa: BLE001
            failures.append(f"prompts.declared_vars({name!r}) raised: {e}")
            continue

        # Every {{var}} used in the body must be declared in frontmatter
        # `vars`. This is the typo guard: `{{descripton}}` would otherwise
        # silently render as "" (rendering's forgiving default) and the
        # tail check below would happily pass.
        missing_from_meta = used - declared
        if missing_from_meta:
            failures.append(
                f"prompts/{name}.md: placeholders not declared in "
                f"frontmatter `vars`: {sorted(missing_from_meta)} "
                "— add them to `vars:` (or fix the typo in the body)"
            )

        # Every {{var}} used in the body must also have a default value in
        # _DEFAULT_VARS so the smoke render below has something to
        # substitute. Forces fixture maintenance whenever a new
        # placeholder lands.
        missing_defaults = used - default_var_names
        if missing_defaults:
            failures.append(
                f"prompts/{name}.md: placeholders missing from smoke "
                f"_DEFAULT_VARS: {sorted(missing_defaults)} "
                "— add a fixture value at the bottom of smoke_test.py"
            )

        # Forgiving render: must succeed and must leave no `{{`/`}}` behind.
        try:
            body = prompts.render(name, **_DEFAULT_VARS)
        except Exception as e:  # noqa: BLE001
            failures.append(f"prompts.render({name!r}) raised: {e}")
            continue
        if "{{" in body or "}}" in body:
            failures.append(f"prompts.render({name!r}) left placeholder: see {body[:160]!r}")

        # Strict render: must succeed when every placeholder is supplied,
        # and must raise KeyError when one is missing. Locks the
        # CI-friendly behaviour of render(strict=True) so a future
        # refactor can't silently drop the typo guard.
        supplied = {k: _DEFAULT_VARS[k] for k in used if k in _DEFAULT_VARS}
        try:
            prompts.render(name, strict=True, **supplied)
        except Exception as e:  # noqa: BLE001
            failures.append(
                f"prompts.render({name!r}, strict=True) raised even with "
                f"all declared vars supplied: {e}"
            )
        if used:
            sample = next(iter(used))
            partial = {k: v for k, v in supplied.items() if k != sample}
            try:
                prompts.render(name, strict=True, **partial)
            except KeyError:
                pass
            except Exception as e:  # noqa: BLE001
                failures.append(
                    f"prompts.render({name!r}, strict=True) raised "
                    f"{type(e).__name__} instead of KeyError on missing "
                    f"placeholder {sample!r}: {e}"
                )
            else:
                failures.append(
                    f"prompts.render({name!r}, strict=True) did NOT raise "
                    f"on missing placeholder {sample!r} — strict mode is "
                    "broken (typo guard would no longer fire in CI)"
                )

    block = prompts.render_block("smoke", "hello\nworld")
    if "<smoke>" not in block or "</smoke>" not in block or "hello\nworld" not in block:
        failures.append(f"prompts.render_block did not produce a fenced block: {block!r}")

    return failures


def check_generate_review(skill_root: Path) -> list[str]:
    """Render review HTML from an in-memory fixture; require non-empty + tag presence."""
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import generate_review  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import generate_review module: {e}"]

    fake_log = [
        {
            "id": "smoke/v1",
            "skill_name": "smoke",
            "version": "v1",
            "date": "2026-04-26",
            "pipeline": "quick",
            "scores": {
                "trigger_precision": 7,
                "workflow_coverage": 8,
                "output_clarity": 7,
                "red_flag_completeness": 7,
                "dep_accuracy": 7,
            },
            "total": 36,
            "notes": "smoke fixture",
        }
    ]
    html = generate_review.render_html("smoke-skill", fake_log, {})
    must_contain = [
        "smoke-skill",  # title
        "Eval Review",
        "trigger_precision",
        "EVAL_LOG",
    ]
    for needle in must_contain:
        if needle not in html:
            failures.append(f"render_html: missing {needle!r} in output (len={len(html)})")
    return failures


def check_review_whitelist(skill_root: Path) -> list[str]:
    """
    `data/evals.jsonl` records carry optimizer-only payloads (full
    ``skill_md`` snapshot, ``change_notes``) that the review viewer never
    reads. Lock the whitelist in ``_normalize_eval_log`` so those fields
    never end up inlined into ``review.html`` — both for size (~10× bloat
    otherwise) and to keep the inline ``<script>`` JSON surface tight.
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import generate_review  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import generate_review module: {e}"]

    huge_skill_md = "<!--SKILL_MD_SENTINEL-->\n" + ("padding\n" * 200)
    huge_change_notes = "<!--CHANGE_NOTES_SENTINEL-->\n" + ("note\n" * 200)
    fake_log = [
        {
            "id": "wl/v1",
            "skill_name": "wl",
            "version": "v1",
            "date": "2026-04-26",
            "pipeline": "quick",
            "scores": {"trigger_precision": 7},
            "total": 35,
            "notes": "whitelist fixture",
            "skill_md": huge_skill_md,
            "change_notes": huge_change_notes,
            "open_questions": ["nothing"],
            "secret_field": "should-not-leak",
        }
    ]

    cleaned = generate_review._normalize_eval_log(fake_log)
    if len(cleaned) != 1:
        return [f"_normalize_eval_log returned {len(cleaned)} entries, expected 1"]
    entry = cleaned[0]
    for forbidden in ("skill_md", "change_notes", "open_questions", "secret_field"):
        if forbidden in entry:
            failures.append(
                f"_normalize_eval_log leaked non-whitelisted field "
                f"{forbidden!r} into the review payload — keys: "
                f"{sorted(entry.keys())}"
            )

    html = generate_review.render_html("wl", fake_log, {})
    forbidden_in_html = (
        "SKILL_MD_SENTINEL",
        "CHANGE_NOTES_SENTINEL",
        "should-not-leak",
    )
    for needle in forbidden_in_html:
        if needle in html:
            failures.append(
                f"render_html embedded non-whitelisted field content "
                f"{needle!r} into review.html (whitelist regression — "
                "see _ALLOWED_EVAL_FIELDS in generate_review.py)"
            )

    # Size sanity: render.html should NOT explode in size when entries
    # carry large skill_md snapshots. Keep the budget loose so this only
    # trips when the whitelist is genuinely broken.
    if len(html) > 200_000:
        failures.append(
            f"render_html output is {len(html)} bytes for a single fixture "
            "entry — whitelist likely broken (skill_md / change_notes "
            "leaked back into the inline script)"
        )
    return failures


def check_review_xss(skill_root: Path) -> list[str]:
    """Malicious score / total values must not survive into the rendered HTML."""
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import generate_review  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import generate_review module: {e}"]

    payload = "</span><img src=x onerror=alert(1)>"
    fake_log = [
        {
            "id": "x/v1",
            "skill_name": "x",
            "version": "v1",
            "scores": {
                "trigger_precision": payload,
                "workflow_coverage": "<script>alert(1)</script>",
            },
            "total": payload,
            # notes / change_notes etc. go through escapeHtml at runtime, so
            # we don't assert on those here — only score / total are the
            # innerHTML-concat surface that demanded the fix.
            "notes": "smoke",
        }
    ]
    # Sandbox `score` field is not used by the renderer; the normaliser
    # should drop it entirely so it cannot reach innerHTML by accident.
    fake_runs = {
        "x/v1": {
            "actual": "(legit run output)",
            "expected": "(legit expected)",
            "score": {"total": payload},
        }
    }
    html = generate_review.render_html("x", fake_log, fake_runs)

    forbidden = ("<img", "onerror", "<script>alert(1)")
    for needle in forbidden:
        if needle in html:
            failures.append(
                f"render_html: payload {needle!r} survived into output "
                f"(XSS regression — see _normalize_eval_log / _normalize_sandbox_runs)"
            )

    return failures


def check_review_attribute_xss(skill_root: Path) -> list[str]:
    """
    Fields like entry.id / version / pipeline are concatenated into HTML
    attributes (e.g. ``<textarea data-id="..."``). The browser-side
    escapeHtml() must escape `"` and `'`, otherwise an attacker-controlled
    id can break out of the attribute and inject markup.

    The dangerous concatenation happens in the *browser*, so a pure-Python
    smoke test cannot observe the unsafe payload directly — the rendered
    HTML embeds the fixture as JSON inside ``<script>`` and as a literal
    string inside escapeHtml's source. Instead we lock the JS source of
    escapeHtml to ensure it always escapes ``"`` and ``'``. Regression
    guard for the day someone trims escapeHtml back down to ``&<>``.
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import generate_review  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import generate_review module: {e}"]

    template = generate_review._HTML_TEMPLATE
    # Locate the function body. We look for the literal source so a future
    # refactor that renames it raises a loud failure here rather than
    # silently making the check vacuous.
    if "function escapeHtml(" not in template:
        return ["escapeHtml() not found in HTML template — the smoke check "
                "needs updating alongside the renderer"]

    required_replacements = (
        ('&', "&amp;"),
        ('<', "&lt;"),
        ('>', "&gt;"),
        ('"', "&quot;"),
        ("'", "&#39;"),  # &apos; is also valid in HTML5 but not HTML4
    )
    for raw, escaped in required_replacements:
        # Each pair must appear inside the template source; the JS regex
        # form .replace(/<char>/g, "<escaped>") is what we look for.
        marker = f'"{escaped}"'
        if marker not in template:
            failures.append(
                f"escapeHtml() in HTML template is missing the {raw!r} → "
                f"{escaped!r} replacement (attribute-context XSS regression — "
                "see scripts/generate_review.py::escapeHtml)"
            )

    # Sanity check: render a fixture whose id contains a `"`. Even though
    # the template-level check above is the real guard, we also confirm
    # render_html does not crash on attacker-controlled ids and that the
    # JSON-encoded form (which is what JS will actually parse) is present.
    fake_log = [
        {
            "id": 'x" autofocus onfocus="alert(1)',
            "version": "v1",
            "pipeline": "quick",
            "scores": {},
            "total": 1,
            "notes": "attr xss fixture",
        }
    ]
    try:
        html = generate_review.render_html("attr-xss", fake_log, {})
    except Exception as e:  # noqa: BLE001
        return failures + [f"render_html crashed on attacker-controlled id: {e}"]

    # The id flows into the inline JSON literal inside <script>, where the
    # `"` is JSON-escaped to `\"`. Confirm that survived (i.e. _safe_script_json
    # didn't mangle it) so the JS-level escapeHtml actually has something
    # to work on at runtime.
    if r'\"' not in html:
        failures.append(
            "embedded EVAL_LOG JSON does not contain an escaped quote — "
            "_safe_script_json may have dropped the attacker-controlled id"
        )

    return failures


def check_skill_md_description(skill_root: Path) -> list[str]:
    """
    The frontmatter parser in optimize_description.py only handles a
    single-line scalar `description: '...'` (or "..."). Catch the day
    someone introduces `description: >` or a block scalar before it
    silently breaks the description-tuning loop.
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import optimize_description  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import optimize_description module: {e}"]

    skill_md_path = skill_root / "SKILL.md"
    if not skill_md_path.exists():
        return [f"SKILL.md not found at {skill_md_path}"]

    try:
        text, current = optimize_description.load_skill_md(str(skill_md_path))
    except SystemExit as e:
        return [f"load_skill_md raised SystemExit: {e}"]
    except Exception as e:  # noqa: BLE001
        return [f"load_skill_md raised: {e}"]

    if not current.strip():
        failures.append("SKILL.md description is empty after parsing")

    # Reject folded / block scalar markers in the description line — these
    # would parse as a literal "|" or ">" rather than the intended text.
    fm_match = optimize_description._FRONTMATTER_RE.match(text)
    if fm_match:
        for line in fm_match.group(1).splitlines():
            stripped = line.strip()
            if stripped.startswith("description:"):
                value = stripped[len("description:") :].strip()
                if value in ("|", ">", "|-", ">-", "|+", ">+"):
                    failures.append(
                        "SKILL.md description uses a YAML folded/block scalar "
                        f"({value!r}); the optimizer parser only handles "
                        "single-line scalars. Either rewrite as one line or "
                        "extend optimize_description._DESC_LINE_RE."
                    )
                if "\\n" in value or "\n" in value:
                    failures.append(
                        "SKILL.md description appears to span multiple lines; "
                        "keep it as a single-line scalar so the description "
                        "optimizer can substitute it back in."
                    )
                break

    # Round-trip: substituting the same description should not corrupt the file.
    rebuilt = optimize_description.replace_description(text, current)
    if rebuilt != text and current not in rebuilt:
        failures.append(
            "replace_description round-trip lost the original description"
        )

    # Multi-line safety: an LLM-generated variant containing a newline must
    # be normalised to a single-line scalar before it lands in SKILL.md.
    # Otherwise the next read via load_skill_md() would refuse the file
    # (folded/block scalar guard) and --apply would have written a half-
    # quoted multi-line scalar like `description: 'foo\nbar'`. Round-trip
    # through replace_description -> load_skill_md to lock the contract.
    multiline_desc = "Build skills\nfor agents\twith\ttabs"
    expected_collapsed = "Build skills for agents with tabs"
    with tempfile.TemporaryDirectory() as td:
        tmp_skill = Path(td) / "SKILL.md"
        tmp_skill.write_text(
            "---\nname: smoke\ndescription: 'placeholder'\n---\n# body\n",
            encoding="utf-8",
        )
        new_text = optimize_description.replace_description(
            tmp_skill.read_text(encoding="utf-8"), multiline_desc
        )
        tmp_skill.write_text(new_text, encoding="utf-8")
        try:
            _, parsed = optimize_description.load_skill_md(str(tmp_skill))
        except SystemExit as e:
            failures.append(
                f"replace_description wrote a description that load_skill_md "
                f"refuses: {e} (multi-line input must be collapsed)"
            )
        else:
            if parsed != expected_collapsed:
                failures.append(
                    f"multi-line description not collapsed: "
                    f"expected {expected_collapsed!r}, got {parsed!r}"
                )

    # Apostrophe round-trip via load_skill_md: replace_description() escapes
    # `'` to YAML's doubled `''` form on write. Until load_skill_md() learned
    # to undo that, descriptions like `don't` came back as `don''t` after one
    # cycle and the optimizer's prompt rendered the corrupted form. Lock the
    # symmetric pair.
    apostrophe_cases = [
        "don't worry — it's fine",
        "no apostrophe here",
        "multiple ''quotes'' inside",
        "leading 'quote and trailing quote'",
    ]
    for original in apostrophe_cases:
        with tempfile.TemporaryDirectory() as td:
            tmp_skill = Path(td) / "SKILL.md"
            tmp_skill.write_text(
                "---\nname: smoke\ndescription: 'placeholder'\n---\n# body\n",
                encoding="utf-8",
            )
            new_text = optimize_description.replace_description(
                tmp_skill.read_text(encoding="utf-8"), original
            )
            tmp_skill.write_text(new_text, encoding="utf-8")
            try:
                _, parsed = optimize_description.load_skill_md(str(tmp_skill))
            except SystemExit as e:
                failures.append(
                    f"load_skill_md raised SystemExit on apostrophe round-trip "
                    f"for {original!r}: {e}"
                )
                continue
            if parsed != original:
                failures.append(
                    f"load_skill_md did not unescape YAML doubled-single-quote: "
                    f"in={original!r} out={parsed!r}"
                )

    # Backslash safety: re.sub replacement strings interpret `\1`, `\g<...>`,
    # etc. If replace_description ever passes the new description as a
    # replacement *string* instead of a function, descriptions containing
    # a literal backslash will either be silently corrupted or raise
    # `re.error: invalid group reference`. Use synthetic frontmatter so
    # this stays orthogonal to whatever the live SKILL.md says.
    synthetic = "---\nname: smoke\ndescription: 'placeholder'\n---\n# body\n"
    tricky_descriptions = [
        r"Create skills for C:\tmp\foo",
        r"Match \1 in regex demos",
        r"Backref \g<name> shouldn't blow up",
    ]
    for tricky in tricky_descriptions:
        try:
            new_text = optimize_description.replace_description(synthetic, tricky)
        # re.error covers `\1` etc.; IndexError covers `\g<name>` (unknown
        # group name) — both are produced by re.sub interpreting the new
        # description as a replacement *string* with backref tokens.
        except (re.error, IndexError) as e:
            failures.append(
                f"replace_description raised {type(e).__name__} on {tricky!r}: {e} "
                "(treat the new description as a replacement *function*, "
                "not a replacement *string* — backslashes get reinterpreted)"
            )
            continue

        # Parse the substituted text back through the same regex
        # optimize_description uses, so we exercise the real round-trip.
        fm = optimize_description._FRONTMATTER_RE.match(new_text)
        m = optimize_description._DESC_LINE_RE.search(fm.group(1)) if fm else None
        if not m:
            failures.append(
                f"could not re-parse description after substituting {tricky!r}"
            )
            continue
        parsed_back = m.group("val").strip()
        if m.group("quote") == "'":
            parsed_back = parsed_back.replace("''", "'")
        if parsed_back != tricky:
            failures.append(
                f"replace_description corrupted backslash-bearing description: "
                f"in={tricky!r} out={parsed_back!r}"
            )

    return failures


def check_optimize_extract_requirements(skill_root: Path) -> list[str]:
    """
    `_extract_requirements()` previously dropped only lines that started
    with `<!--`, so the *body* of a multi-line HTML comment leaked into
    the requirements list (the live SKILL.md has exactly such a comment
    under `## Requirements`). Lock the fix: HTML comments must be
    stripped wholesale before the line scan, and only real bullets
    survive.
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import optimize  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import optimize module: {e}"]

    fixture = textwrap.dedent(
        """\
        ---
        name: smoke
        description: 'smoke fixture'
        ---

        # smoke

        ## Requirements

        <!-- Used by Pipeline executor's acceptance-gate element.
             RFC 2119 priorities; at least one item must be MUST. -->

        - Real requirement A `MUST`
        - Real requirement B `SHOULD`

        ## Output

        Real output description.
        """
    )

    extracted = optimize._extract_requirements(fixture, "")
    forbidden_substrings = (
        "RFC 2119",
        "acceptance-gate",
        "Pipeline executor",
        "<!--",
        "-->",
    )
    for needle in forbidden_substrings:
        if needle in extracted:
            failures.append(
                f"_extract_requirements leaked HTML-comment text {needle!r} "
                f"into the requirements: {extracted!r}"
            )
    if "Real requirement A" not in extracted:
        failures.append(
            f"_extract_requirements dropped a real requirement bullet: "
            f"{extracted!r}"
        )
    return failures


def check_tune_thresholds_regression_guard(skill_root: Path) -> list[str]:
    """
    `tune_thresholds.simulate()` previously declared a sequence "plateaued"
    whenever ``improvement < improvement_threshold and weighted >= min_quality``,
    which silently fired on regressions: a v3 weighted=7.1 after v2=8.5
    (improvement = -16.4%) satisfied both clauses and the optimizer happily
    locked in a strictly worse skill as "done".

    Lock the contract:
      1. A clearly regressing sequence (v2 high → v3 lower, both above
         min_quality) must NOT plateau at the regressing version. That
         was the original semantic bug.
      2. A genuine plateau (small *positive* gain above min_quality, no
         per-metric regression) still fires the plateau gate.
      3. Per-metric regressions block the plateau gate even when the
         weighted average improves (weight-reshuffling guard).

    Skips gracefully when ``optuna`` is not installed locally — the CI
    job runs ``uv run --help`` separately for tune_thresholds, but
    smoke_test.py itself runs in a vanilla stdlib env.
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import tune_thresholds  # noqa: WPS433
    except ImportError as e:
        # optuna missing — fine for stdlib-only smoke. The CI workflow
        # exercises the import path via `uv run --help` separately.
        if "optuna" in str(e):
            print(f"  [skip] tune_thresholds_regression_guard: optuna not installed ({e})")
            return failures
        return [f"failed to import tune_thresholds module: {e}"]
    except Exception as e:  # noqa: BLE001
        return [f"failed to import tune_thresholds module: {e}"]

    METRICS = tune_thresholds.METRICS
    weights = {m: 1.0 for m in METRICS}

    def _seq(*per_version_scores: dict) -> list[dict]:
        return [
            {"skill_name": "regress-fixture", "version": f"v{i + 1}",
             "scores": s, "total": sum(s.values())}
            for i, s in enumerate(per_version_scores)
        ]

    # Case 1: regression after a high v2. Plateau gate must NOT fire on
    # v3 even though `improvement < improvement_threshold` and
    # `weighted >= min_quality`. With max_iters = 2 (sequence length 3),
    # we should run all the way to v3 — i.e. stop_index == 2.
    regressing = _seq(
        {m: 7.0 for m in METRICS},                          # v1: weighted 7.0
        {m: 8.5 for m in METRICS},                          # v2: weighted 8.5
        {m: 7.1 for m in METRICS},                          # v3: weighted 7.1 (regression)
    )
    stop_idx, quality = tune_thresholds.simulate(
        regressing,
        convergence_threshold=9.5,   # high so the pass gate never fires
        improvement_threshold=15.0,
        weights=weights,
        min_quality=7.0,
    )
    if stop_idx != 2:
        failures.append(
            f"simulate() plateaued on a regressing sequence: "
            f"stop_index={stop_idx} quality={quality:.2f} "
            "(expected 2 — regressions must never trigger the plateau gate)"
        )

    # Case 2: genuine plateau. v2 lands a >=15% jump (so v2 itself doesn't
    # plateau), then v3 nudges up by a small positive amount above
    # min_quality with no per-metric regression — this is the case the
    # gate SHOULD fire on.
    plateauing = _seq(
        {m: 6.0 for m in METRICS},                          # v1: 6.0 (below min_quality)
        {m: 8.0 for m in METRICS},                          # v2: 8.0 (+33%, well above 15% — no plateau)
        {m: 8.05 for m in METRICS},                         # v3: 8.05 (+0.6%, true plateau)
    )
    stop_idx, _ = tune_thresholds.simulate(
        plateauing,
        convergence_threshold=9.5,
        improvement_threshold=15.0,
        weights=weights,
        min_quality=7.0,
    )
    if stop_idx != 2:
        failures.append(
            f"simulate() failed to plateau on a real plateau: "
            f"stop_index={stop_idx} (expected 2 — small positive gain "
            "above min_quality with no per-metric regression must fire "
            "the plateau gate)"
        )

    # Case 3: weighted average improves while one metric regresses.
    # Plateau gate must NOT fire — we treat per-metric regressions as
    # "not actually plateaued; keep iterating".
    sneaky_regress = _seq(
        {"trigger_precision": 8.0, "workflow_coverage": 7.0,
         "output_clarity": 7.0, "red_flag_completeness": 7.0,
         "dep_accuracy": 7.0},                              # v1: 7.2
        {"trigger_precision": 6.5, "workflow_coverage": 7.6,
         "output_clarity": 7.6, "red_flag_completeness": 7.6,
         "dep_accuracy": 7.6},                              # v2: 7.38 (+2.5%); trigger_precision dropped
    )
    stop_idx, _ = tune_thresholds.simulate(
        sneaky_regress,
        convergence_threshold=9.5,
        improvement_threshold=15.0,
        weights=weights,
        min_quality=7.0,
    )
    if stop_idx != 1:
        failures.append(
            f"simulate() plateaued despite a per-metric regression: "
            f"stop_index={stop_idx} (expected 1 — trigger_precision "
            "dropped 8.0 → 6.5, the plateau gate must not fire)"
        )

    return failures


def check_optimize_coerce_metric(skill_root: Path) -> list[str]:
    """
    optimize._coerce_metric and _score_from_dict correctly handle non-numeric
    inputs so a hand-edited data/evals.jsonl carrying "7" (string) or True
    (bool) does not corrupt the optimizer's pick.
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import optimize  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import optimize module: {e}"]

    if not hasattr(optimize, "_coerce_metric"):
        failures.append("optimize._coerce_metric not exposed at module scope")
        return failures

    # Legitimate numeric → expected value
    if optimize._coerce_metric(8) != 8.0:
        failures.append("_coerce_metric(8) should return 8.0")
    # Clamping
    if optimize._coerce_metric(15) != 10.0:
        failures.append("_coerce_metric(15) should clamp to 10.0")
    if optimize._coerce_metric(-3) != 0.0:
        failures.append("_coerce_metric(-3) should clamp to 0.0")
    # Non-numeric → None
    if optimize._coerce_metric("7") is not None:
        failures.append("_coerce_metric('7') should return None (string rejected)")
    if optimize._coerce_metric(True) is not None:
        failures.append("_coerce_metric(True) should return None (bool rejected)")
    if optimize._coerce_metric(None) is not None:
        failures.append("_coerce_metric(None) should return None")
    if optimize._coerce_metric(float("nan")) is not None:
        failures.append("_coerce_metric(nan) should return None")

    if not hasattr(optimize, "_score_from_dict"):
        failures.append("optimize._score_from_dict not exposed at module scope")
        return failures

    legit = {m: 8 for m in optimize.METRICS}
    score = optimize._score_from_dict(legit)
    expected = 40.0 / 50.0
    if abs(score - expected) > 1e-9:
        failures.append(f"_score_from_dict(all 8s) expected {expected:.4f}, got {score:.4f}")

    bad = {m: 8 for m in optimize.METRICS}
    bad["trigger_precision"] = "high"  # type: ignore[assignment]
    if optimize._score_from_dict(bad) != 0.0:
        failures.append("_score_from_dict with a string metric should return 0.0")

    return failures


def check_optimize_description_estimate_cache(skill_root: Path) -> list[str]:
    """
    `optimize_description.py --estimate-only` previously decided whether
    to count an ``eval-set-gen`` call by checking ``os.path.exists``,
    while the live path also validated the cache shape and regenerated
    on corrupt / short caches. The estimator therefore under-counted by
    one call whenever the cache file existed but was unusable.

    Lock the contract: the estimator and the live path share a single
    cache validator (``_load_cached_eval_set``), so a usable cache
    returns the queries and an unusable cache returns None — the
    estimator can no longer disagree with the live path on what counts
    as "free".
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import optimize_description  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import optimize_description module: {e}"]

    if not hasattr(optimize_description, "_load_cached_eval_set"):
        return failures + [
            "optimize_description._load_cached_eval_set not found — the "
            "estimator and live path must share a cache validator so "
            "--estimate-only cannot under-count regenerations"
        ]

    loader = optimize_description._load_cached_eval_set
    min_queries = optimize_description._MIN_USABLE_QUERIES

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        good = td_path / "good.json"
        good.write_text(
            json.dumps({"queries": [
                {"query": f"q{i}", "should_trigger": True, "rationale": "r"}
                for i in range(min_queries)
            ]}),
            encoding="utf-8",
        )
        loaded = loader(str(good))
        if loaded is None or len(loaded) != min_queries:
            failures.append(
                f"_load_cached_eval_set rejected a usable cache "
                f"({min_queries} queries): got {loaded!r}"
            )

        short = td_path / "short.json"
        short.write_text(
            json.dumps({"queries": [
                {"query": "only one", "should_trigger": False, "rationale": "r"}
            ]}),
            encoding="utf-8",
        )
        if loader(str(short)) is not None:
            failures.append(
                "_load_cached_eval_set treated a short cache as usable — "
                "estimator would under-count by one eval-set-gen call"
            )

        broken = td_path / "broken.json"
        broken.write_text("{not json", encoding="utf-8")
        if loader(str(broken)) is not None:
            failures.append(
                "_load_cached_eval_set treated unparseable JSON as usable"
            )

        missing = td_path / "missing.json"
        if loader(str(missing)) is not None:
            failures.append(
                "_load_cached_eval_set treated a missing file as usable"
            )

    return failures


def check_optimize_build_candidates(skill_root: Path) -> list[str]:
    """
    optimize._build_candidates is deterministic under a fixed seed.
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import optimize  # noqa: WPS433
        import random as _random  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import optimize module: {e}"]

    if not hasattr(optimize, "_build_candidates"):
        return ["optimize._build_candidates not exposed at module scope"]

    trainset = [{"id": f"ex/{i}"} for i in range(6)]
    rng_a = _random.Random(1234)
    rng_b = _random.Random(1234)
    cands_a = optimize._build_candidates(trainset, max_demos=2, trials=4, rng=rng_a)
    cands_b = optimize._build_candidates(trainset, max_demos=2, trials=4, rng=rng_b)
    if cands_a != cands_b:
        failures.append(
            f"_build_candidates is non-deterministic under fixed seed: "
            f"{cands_a!r} vs {cands_b!r}"
        )
    if not cands_a:
        failures.append("_build_candidates returned empty list for 6-example trainset")

    return failures


def check_agent_delegate(skill_root: Path) -> list[str]:
    """
    agent.call_emit() emits a correctly-formatted __LLM_DELEGATE__ line
    to stdout (Mode D — no subprocess, no API key, no claude CLI).
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import agent  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import agent module: {e}"]

    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        out_path = agent.call_emit(
            "hello world",
            out="tmp/smoke/result.txt",
            system="be terse",
            json_mode=True,
            id="smoke_test",
        )
    finally:
        sys.stdout = old_stdout

    if out_path != "tmp/smoke/result.txt":
        failures.append(f"call_emit() should return the out path, got {out_path!r}")

    output = buf.getvalue().strip()
    if not output.startswith("__LLM_DELEGATE__: "):
        failures.append(f"call_emit() did not emit __LLM_DELEGATE__ prefix: {output[:120]!r}")
        return failures

    try:
        payload = json.loads(output[len("__LLM_DELEGATE__: "):])
    except json.JSONDecodeError as e:
        failures.append(f"call_emit() emitted invalid JSON: {e} — {output[:200]!r}")
        return failures

    for field, expected in [
        ("prompt", "hello world"),
        ("out", "tmp/smoke/result.txt"),
        ("system", "be terse"),
        ("id", "smoke_test"),
    ]:
        if payload.get(field) != expected:
            failures.append(f"payload[{field!r}] expected {expected!r}, got {payload.get(field)!r}")
    if payload.get("json") is not True:
        failures.append(f"payload['json'] should be True, got {payload.get('json')!r}")

    # _extract_json_object round-trip — basic
    sample = '{"ok": true, "score": 42}'
    parsed = agent._extract_json_object(sample)
    if parsed != {"ok": True, "score": 42}:
        failures.append(f"_extract_json_object({sample!r}) returned {parsed!r}")
    if agent._extract_json_object("no json here") is not None:
        failures.append("_extract_json_object should return None when no JSON found")

    # Edge case: JSON wrapped in markdown code fences (common host prose wrapper)
    fenced = '```json\n{"label": "feat"}\n```'
    parsed_fenced = agent._extract_json_object(fenced)
    if parsed_fenced != {"label": "feat"}:
        failures.append(
            f"_extract_json_object should extract JSON from markdown fence, "
            f"got {parsed_fenced!r}"
        )

    # Edge case: nested array inside object
    nested = '{"items": [1, 2, 3], "count": 3}'
    parsed_nested = agent._extract_json_object(nested)
    if parsed_nested != {"items": [1, 2, 3], "count": 3}:
        failures.append(
            f"_extract_json_object failed on nested array: got {parsed_nested!r}"
        )

    # Edge case: escaped double-quote inside string value
    escaped = r'{"key": "value with \"quotes\" inside"}'
    parsed_escaped = agent._extract_json_object(escaped)
    if parsed_escaped != {"key": 'value with "quotes" inside'}:
        failures.append(
            f"_extract_json_object failed on escaped quote in string: "
            f"got {parsed_escaped!r}"
        )

    # Edge case: prose before and after the JSON object
    prose = 'Here is the result: {"status": "ok"} — done.'
    parsed_prose = agent._extract_json_object(prose)
    if parsed_prose != {"status": "ok"}:
        failures.append(
            f"_extract_json_object failed to extract JSON from surrounding prose: "
            f"got {parsed_prose!r}"
        )

    # result_exists / load_state / save_state round-trip (no filesystem side-effects
    # beyond a single tempdir)
    with tempfile.TemporaryDirectory() as td:
        state_path = os.path.join(td, "state.json")
        if agent.result_exists(state_path):
            failures.append("result_exists() returned True for nonexistent file")
        agent.save_state(state_path, {"phase": "test", "n": 3})
        if not agent.result_exists(state_path):
            failures.append("result_exists() returned False after save_state()")
        loaded = agent.load_state(state_path)
        if loaded != {"phase": "test", "n": 3}:
            failures.append(f"load_state() round-trip failed: got {loaded!r}")
        if agent.load_state(os.path.join(td, "missing.json")) is not None:
            failures.append("load_state() should return None for missing file")

    return failures


def _repo_root_from(skill_root: Path) -> Path:
    """skills/<name>/ → repo root (two levels up). Best-effort, no git call."""
    return skill_root.parent.parent


# Backtick-quoted skill names inside dependency-graph.md sections we trust:
#   - the Mermaid block (graph LR ... edges)
#   - the "Skill table" rows (`| skill | ... |`)
# Restrict to a-z0-9- to avoid grabbing every backtick ident in prose.
_SKILL_TOKEN_RE = re.compile(r"`([a-z0-9][a-z0-9-]*)`")
_MERMAID_NODE_RE = re.compile(r"^\s*([a-z0-9][a-z0-9-]*)\b")


def check_dependency_graph(skill_root: Path) -> list[str]:
    """
    `references/dependency-graph.md` is the SSOT for inter-skill edges (until
    sklock is adopted). Every skill name it references must exist on disk as
    `skills/<name>/SKILL.md`. Catches the "renamed pluginize → skill-creator
    edge but forgot to rename the dir" class of bug before merge.
    """
    failures: list[str] = []
    repo_root = _repo_root_from(skill_root)
    graph_path = repo_root / "references" / "dependency-graph.md"
    skills_dir = repo_root / "skills"

    if not graph_path.exists():
        return [f"dependency-graph.md not found at {graph_path}"]
    if not skills_dir.exists():
        return [f"skills/ dir not found at {skills_dir}"]

    text = graph_path.read_text(encoding="utf-8")

    # Collect candidate skill names from two trusted regions:
    #   1. inside the ```mermaid ... ``` block — node lines + edges
    #   2. inside the "## Skill table" markdown table
    candidates: set[str] = set()

    in_mermaid = False
    in_skill_table = False
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith("```mermaid"):
            in_mermaid = True
            continue
        if in_mermaid and stripped.startswith("```"):
            in_mermaid = False
            continue
        if in_mermaid:
            # Mermaid edges look like:  pluginize -.-> skill-builder
            # Mermaid nodes look like:  bommit
            for match in re.finditer(r"\b([a-z][a-z0-9-]*)\b", line):
                tok = match.group(1)
                # Filter out Mermaid keywords / structural words.
                if tok in {
                    "graph", "lr", "td", "subgraph", "end", "skills",
                    "click", "style", "classdef",
                }:
                    continue
                candidates.add(tok)
            continue

        if stripped.startswith("## Skill table"):
            in_skill_table = True
            continue
        if in_skill_table:
            if stripped.startswith("## "):
                in_skill_table = False
                continue
            # First column is the skill name in backticks: `| `name` | ... |`.
            cells = [c.strip() for c in stripped.strip("|").split("|")]
            if cells:
                m = _SKILL_TOKEN_RE.match(cells[0])
                if m:
                    candidates.add(m.group(1))

    # Drop tokens that are obviously not skills (single chars, pure version
    # markers, etc.). Anything left is required to exist on disk.
    candidates = {c for c in candidates if len(c) >= 4 and "-" in c or c.isalpha() and len(c) > 3}

    # Be specific: only the skills that *actually* live in skills/ should be
    # checked. Anything else in the graph (e.g. external tool names) would
    # be a false positive — but currently the graph only lists in-repo skills.
    on_disk = {
        p.name for p in skills_dir.iterdir()
        if p.is_dir() and (p / "SKILL.md").exists()
    }

    referenced_existing = candidates & on_disk
    referenced_missing = candidates - on_disk

    # We must reference *something* — empty intersection means the parser
    # broke or the graph was emptied without anyone noticing.
    if not referenced_existing:
        failures.append(
            "dependency-graph.md references no on-disk skills "
            f"(candidates={sorted(candidates)}, on_disk={sorted(on_disk)})"
        )

    # Hard fail when the graph names a skill that no longer exists.
    # We only flag candidates that look like real skill names (contain a dash
    # or are clearly multi-char tokens that match nothing on disk) to keep
    # false positives down on prose tokens accidentally captured.
    suspicious = {
        c for c in referenced_missing
        if "-" in c or len(c) > 6  # heuristic; matches "skill-creator" etc.
    }
    if suspicious:
        failures.append(
            "dependency-graph.md references skill(s) without a matching "
            f"skills/<name>/SKILL.md: {sorted(suspicious)} "
            f"(on disk: {sorted(on_disk)})"
        )

    return failures


def check_collect_evals_fixture(skill_root: Path) -> list[str]:
    """
    Stage a tiny synthetic skill root (SKILL.md + one v<N>/eval.json with
    sibling input.md / skill.md snapshot) and run collect_evals.collect()
    against it. Locks the producer-side schema of data/evals.jsonl so a
    drift in field names (e.g. skill_md → snapshot, change_notes → input_md)
    breaks CI before it breaks optimize.py / generate_review.py /
    tune_thresholds.py downstream.
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import collect_evals  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import collect_evals module: {e}"]

    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        # Minimal SKILL.md so the footgun guard is satisfied.
        (td_path / "SKILL.md").write_text(
            "---\nname: smoke\ndescription: 'smoke fixture'\n---\n# smoke\n",
            encoding="utf-8",
        )
        v1 = td_path / "projects" / "smoke" / "v1"
        v1.mkdir(parents=True)
        (v1 / "eval.json").write_text(json.dumps({
            "version": "v1",
            "date": "2026-04-26",
            "pipeline": "quick",
            "scores": {
                "trigger_precision": 7,
                "workflow_coverage": 7,
                "output_clarity": 7,
                "red_flag_completeness": 7,
                "dep_accuracy": 7,
            },
            "total": 35,
            "open_questions": ["nothing"],
            "notes": "smoke fixture eval",
        }), encoding="utf-8")
        (v1 / "input.md").write_text(
            "# v1 — input\n\nsmoke change notes\n", encoding="utf-8"
        )
        # Explicit snapshot — short-circuits the git-history fallback so the
        # test is hermetic (the temp dir is not a git repo).
        (v1 / "skill.md").write_text(
            "---\nname: smoke\ndescription: 'smoke fixture v1'\n---\n# smoke v1 body\n",
            encoding="utf-8",
        )

        output = td_path / "data" / "evals.jsonl"
        try:
            added, replaced, skipped = collect_evals.collect(
                str(td_path), str(output), rebuild=True
            )
        except Exception as e:  # noqa: BLE001
            return [f"collect_evals.collect() raised: {e}"]

        if added != 1 or replaced != 0:
            failures.append(
                f"collect_evals.collect() rebuild: expected added=1 replaced=0, "
                f"got added={added} replaced={replaced} skipped={skipped}"
            )

        if not output.exists():
            return failures + [f"data/evals.jsonl was not created at {output}"]

        lines = [l for l in output.read_text(encoding="utf-8").splitlines() if l.strip()]
        if len(lines) != 1:
            return failures + [
                f"data/evals.jsonl should have exactly 1 record, got {len(lines)}"
            ]

        try:
            rec = json.loads(lines[0])
        except json.JSONDecodeError as e:
            return failures + [f"data/evals.jsonl line is not valid JSON: {e}"]

        # Lock the producer-side schema — these are the fields downstream
        # readers (optimize.py / generate_review.py / tune_thresholds.py)
        # depend on. Renaming any of them is a breaking change.
        required = {
            "id": "smoke/v1",
            "skill_name": "smoke",
            "version": "v1",
            "total": 35,
        }
        for key, expected in required.items():
            actual = rec.get(key)
            if actual != expected:
                failures.append(
                    f"data/evals.jsonl record[{key!r}]: expected {expected!r}, "
                    f"got {actual!r}"
                )

        if "smoke v1 body" not in (rec.get("skill_md") or ""):
            failures.append(
                f"record.skill_md missing snapshot body: "
                f"{(rec.get('skill_md') or '')[:120]!r}"
            )
        if "smoke change notes" not in (rec.get("change_notes") or ""):
            failures.append(
                f"record.change_notes missing input.md body: "
                f"{(rec.get('change_notes') or '')[:120]!r}"
            )
        scores = rec.get("scores") or {}
        if scores.get("trigger_precision") != 7:
            failures.append(
                f"record.scores not propagated: {scores!r}"
            )

        # Append-only second pass: re-running without --rebuild should be a no-op.
        added2, replaced2, skipped2 = collect_evals.collect(
            str(td_path), str(output), rebuild=False, force=False
        )
        if added2 or replaced2:
            failures.append(
                f"second-pass collect() should be idempotent, "
                f"got added={added2} replaced={replaced2} skipped={skipped2}"
            )

    return failures


def check_collect_evals_footgun(skill_root: Path) -> list[str]:
    """
    Pointing --skill-root at a parent dir with no SKILL.md must raise
    SystemExit by default (footgun guard for 'Form A run from repo root');
    --allow-missing-skill-md downgrades it to a warning. Regression guard
    for the day someone re-relaxes the check back into a print() and
    silently re-introduces the empty-cache footgun.
    """
    failures: list[str] = []
    sys.path.insert(0, str(_scripts_dir(skill_root)))
    try:
        import collect_evals  # noqa: WPS433
    except Exception as e:  # noqa: BLE001
        return [f"failed to import collect_evals module: {e}"]

    with tempfile.TemporaryDirectory() as td:
        # Deliberately no SKILL.md.
        old_argv = sys.argv
        sys.argv = ["collect_evals.py", "--skill-root", td, "--rebuild"]
        try:
            try:
                collect_evals.main()
            except SystemExit as e:
                # Default: hard fail. argparse uses SystemExit with int code,
                # the footgun guard uses SystemExit with a str message.
                if isinstance(e.code, int) and e.code == 0:
                    failures.append(
                        "collect_evals.main() with --skill-root pointing at "
                        "a dir without SKILL.md should fail, but exited 0"
                    )
            else:
                failures.append(
                    "collect_evals.main() should raise SystemExit when "
                    "--skill-root has no SKILL.md, but returned normally"
                )

            # With the explicit opt-out, the script should NOT raise the
            # footgun guard (it may still exit 0 with no records — that's
            # fine).
            sys.argv = [
                "collect_evals.py", "--skill-root", td, "--rebuild",
                "--allow-missing-skill-md",
            ]
            try:
                collect_evals.main()
            except SystemExit as e:
                if isinstance(e.code, str) or (
                    isinstance(e.code, int) and e.code != 0
                ):
                    failures.append(
                        "collect_evals.main() with --allow-missing-skill-md "
                        f"should not raise the footgun guard, but exited "
                        f"with code={e.code!r}"
                    )
        finally:
            sys.argv = old_argv

    return failures


_DEFAULT_VARS = {
    "scaffold": "---\nname: smoke\n---\n# smoke",
    "skill_md": "---\nname: smoke\n---\n# smoke",
    "description": "Smoke skill",
    "requirements": "MUST be smoke-tested",
    "few_shot_block": "",
    "i": 1,
    "scores": '{"trigger_precision": 7}',
    "top_improvement": "tighten triggers",
    "section": "When to use",
    "assertion": "must contain a frontmatter block",
    "actual_output": "---\nname: x\n---",
    "context": "smoke",
    "query": "create a skill",
    "n": 3,
    "eval_summary": "no errors",
    "schema_hint": "{\"variants\": [\"...\"]}",
    "bad_output": "{not json",
}


def main() -> int:
    parser = argparse.ArgumentParser(description="skill-builder smoke test")
    parser.add_argument(
        "--skill-root",
        default=str(Path(__file__).resolve().parent.parent),
        help="Path to skills/skill-builder (default: this script's parent dir).",
    )
    args = parser.parse_args()

    skill_root = Path(args.skill_root).resolve()
    print(f"Smoke-testing skill-builder at: {skill_root}")

    all_failures: list[str] = []
    for name, fn in (
        ("py_compile", check_py_compile),
        ("prompts", check_prompts),
        ("generate_review", check_generate_review),
        ("review_whitelist", check_review_whitelist),
        ("review_xss", check_review_xss),
        ("review_attribute_xss", check_review_attribute_xss),
        ("agent_delegate", check_agent_delegate),
        ("skill_md_description", check_skill_md_description),
        ("optimize_extract_requirements", check_optimize_extract_requirements),
        ("optimize_coerce_metric", check_optimize_coerce_metric),
        ("optimize_build_candidates", check_optimize_build_candidates),
        ("optimize_description_estimate_cache", check_optimize_description_estimate_cache),
        ("tune_thresholds_regression_guard", check_tune_thresholds_regression_guard),
        ("dependency_graph", check_dependency_graph),
        ("collect_evals_fixture", check_collect_evals_fixture),
        ("collect_evals_footgun", check_collect_evals_footgun),
    ):
        print(f"  [run]  {name}")
        try:
            failures = fn(skill_root)
        except Exception:  # noqa: BLE001
            failures = [f"{name}: unexpected exception\n{traceback.format_exc()}"]
        if failures:
            for f in failures:
                print(f"  [fail] {name}: {f}")
            all_failures.extend(failures)
        else:
            print(f"  [pass] {name}")

    if all_failures:
        print(f"\nFAIL — {len(all_failures)} smoke check(s) failed")
        return 1
    print("\nOK — all smoke checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
