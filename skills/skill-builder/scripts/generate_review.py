"""
generate_review.py — generate a self-contained HTML eval viewer

Reads:
  - data/evals.jsonl            (required if you want any data shown; written by collect_evals.py)
                                — optimizer cache, gitignored, regenerable
                                — for the committed human-readable ledger see
                                  references/eval-log.jsonl (read directly with `cat`/PR diff)
  - sandbox/runs/*              (optional — surfaces actual.md per run)
  - SKILL.md                    (used to read the skill name from frontmatter)

Writes:
  - review/review.html — single self-contained file (HTML + CSS + JS inlined)

Usage:
    # Form A — canonical, runnable from the repo root:
    python skills/skill-builder/scripts/generate_review.py --skill-root skills/<name>

    # Form B — from the target skill's root (matches collect_evals.py docs):
    cd skills/<name>/
    python ../skill-builder/scripts/generate_review.py
    python ../skill-builder/scripts/generate_review.py --output review/v3.html

Tabs:
  - Outputs:   one expandable card per eval run, with feedback textarea
               (saved to localStorage — no backend needed)
  - Benchmark: per-version score table + per-version delta + regression flags

Inspired by Anthropic's official skill-creator eval-viewer.

Stdlib only. No claude / network access required.
"""

from __future__ import annotations

import argparse
import html as html_lib
import json
import re
from pathlib import Path


METRICS = [
    "trigger_precision",
    "workflow_coverage",
    "output_clarity",
    "red_flag_completeness",
    "dep_accuracy",
]

# Fields the review HTML's JS actually reads from each eval entry.
# data/evals.jsonl additionally carries large optimizer-only payloads
# (skill_md snapshot, change_notes) that the viewer does not display —
# embedding them inline would bloat review.html by an order of magnitude
# and widen the inline-script JSON surface unnecessarily. Keep this list
# in sync with the JS template (search for `entry.<field>`).
_ALLOWED_EVAL_FIELDS: frozenset[str] = frozenset({
    "id",
    "skill_name",
    "version",
    "date",
    "pipeline",
    "scores",
    "total",
    "notes",
    "top_improvement",
    "sandbox_run_id",
})


# ---------------------------------------------------------------------------
# Loaders
# ---------------------------------------------------------------------------

def load_eval_log(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out: list[dict] = []
    # Force UTF-8: eval log entries embed em dashes / arrows / non-ASCII
    # notes that cp1252 / cp932 cannot decode, so locale defaults break
    # the viewer on Windows.
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def load_sandbox_runs(sandbox_dir: Path) -> dict[str, dict]:
    """Return {run_id: {actual, expected, score}} for sandbox/runs/*."""
    runs: dict[str, dict] = {}
    if not sandbox_dir.exists():
        return runs
    for run_dir in sorted(sandbox_dir.iterdir()):
        if not run_dir.is_dir():
            continue
        actual_p = run_dir / "actual.md"
        expected_p = run_dir / "expected.md"
        score_p = run_dir / "score.json"
        score: dict = {}
        if score_p.exists():
            try:
                score = json.loads(score_p.read_text(encoding="utf-8"))
            except json.JSONDecodeError:
                score = {}
        runs[run_dir.name] = {
            "actual": actual_p.read_text(encoding="utf-8") if actual_p.exists() else "",
            "expected": expected_p.read_text(encoding="utf-8") if expected_p.exists() else "",
            "score": score,
        }
    return runs


def parse_skill_name(skill_md_path: Path, default: str) -> str:
    if not skill_md_path.exists():
        return default
    text = skill_md_path.read_text(encoding="utf-8")
    for line in text.splitlines()[:30]:
        m = re.match(r"^\s*name:\s*(.+?)\s*$", line)
        if m:
            return m.group(1).strip("'\"")
    return default


# ---------------------------------------------------------------------------
# Renderer
# ---------------------------------------------------------------------------

def _safe_script_json(obj) -> str:
    """Serialize to JSON safe for inline <script> embedding."""
    return (
        json.dumps(obj, ensure_ascii=False)
        .replace("</", "<\\/")
        .replace("<!--", "<\\!--")
    )


def _coerce_number(value, lo: float, hi: float):
    """
    Coerce ``value`` to a finite float clamped to [lo, hi], or None.

    Used to neutralise the only innerHTML XSS surface left in the renderer:
    score / total fields in eval.json are interpolated as numbers in the
    benchmark table and per-run cards. If a malformed eval.json or sandbox
    score.json drops a string like ``"</span><img src=x onerror=alert(1)>"``
    into ``scores[m]`` or ``total``, returning None here causes the JS to
    render ``"-"`` instead of injecting raw HTML. Defence-in-depth: the JS
    side has a matching ``safeNumber()`` helper.
    """
    if isinstance(value, bool):  # bool is a subclass of int; reject explicitly
        return None
    if isinstance(value, (int, float)):
        n = float(value)
    elif isinstance(value, str):
        try:
            n = float(value.strip())
        except ValueError:
            return None
    else:
        return None
    if n != n or n in (float("inf"), float("-inf")):  # NaN / inf
        return None
    if n < lo:
        return lo
    if n > hi:
        return hi
    return n


def _normalize_eval_log(eval_log: list[dict]) -> list[dict]:
    """
    Return a sanitised copy of ``eval_log`` for embedding into review.html.

    Two responsibilities, both deliberately overlapping with the JS-side
    defenses:

    1. **Whitelist** the fields that flow into the inline ``<script>`` —
       ``data/evals.jsonl`` carries optimizer-only payloads (full
       ``skill_md`` snapshot, ``change_notes``) that the viewer never
       displays. Embedding them inline bloats ``review.html`` by ~10×
       and widens the inline-JSON attack surface unnecessarily. Anything
       outside ``_ALLOWED_EVAL_FIELDS`` is dropped.
    2. **Numerically coerce** ``scores`` and ``total`` so that strings,
       HTML, and other non-numeric content become ``None`` (rendered as
       ``"-"`` by the JS template). Same defence-in-depth rationale as
       ``escapeHtml``: the renderer concatenates these into ``innerHTML``.
    """
    out: list[dict] = []
    for entry in eval_log:
        if not isinstance(entry, dict):
            continue
        clean: dict = {
            k: entry[k] for k in _ALLOWED_EVAL_FIELDS if k in entry
        }
        scores = entry.get("scores")
        if isinstance(scores, dict):
            clean["scores"] = {
                k: _coerce_number(v, 0, 10) for k, v in scores.items()
            }
        else:
            clean["scores"] = {}
        clean["total"] = _coerce_number(entry.get("total"), 0, 50)
        out.append(clean)
    return out


def _normalize_sandbox_runs(runs: dict[str, dict]) -> dict[str, dict]:
    """
    Strip score.json content from sandbox runs (it is not used by the
    renderer) and keep only the string fields actually displayed via
    escapeHtml. Same defence-in-depth rationale as ``_normalize_eval_log``.
    """
    out: dict[str, dict] = {}
    for run_id, payload in runs.items():
        if not isinstance(payload, dict):
            continue
        out[str(run_id)] = {
            "actual": str(payload.get("actual", "")),
            "expected": str(payload.get("expected", "")),
        }
    return out


def render_html(
    skill_name: str,
    eval_log: list[dict],
    sandbox_runs: dict[str, dict],
) -> str:
    safe_log = _normalize_eval_log(eval_log)
    safe_runs = _normalize_sandbox_runs(sandbox_runs)
    eval_data = _safe_script_json(safe_log)
    runs_data = _safe_script_json(safe_runs)
    # __SKILL_NAME_HTML__ — safe for HTML attribute/text contexts
    safe_name_html = html_lib.escape(skill_name)
    # __SKILL_NAME_JSON__ — JSON-encoded string literal (includes quotes),
    # safe for inline <script> JS assignment (no HTML-escaping artifacts)
    safe_name_json = _safe_script_json(skill_name)
    return (
        _HTML_TEMPLATE
        .replace("__SKILL_NAME_HTML__", safe_name_html)
        .replace("__SKILL_NAME_JSON__", safe_name_json)
        .replace("__EVAL_DATA__", eval_data)
        .replace("__RUNS_DATA__", runs_data)
    )


# Placeholders:
#   __SKILL_NAME_HTML__ — HTML-escaped name (title, h1)
#   __SKILL_NAME_JSON__ — JSON string literal (JS const assignment, includes quotes)
#   __EVAL_DATA__ / __RUNS_DATA__ — inline script JSON
_HTML_TEMPLATE = r"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__SKILL_NAME_HTML__ — Eval Review</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
         margin: 0; background: #fafafa; color: #222; }
  header { padding: 1rem 2rem; background: #fff; border-bottom: 1px solid #e0e0e0; }
  h1 { margin: 0; font-size: 1.25rem; }
  h3 { margin: 1rem 0 0.5rem; }
  h4 { margin: 0.75rem 0 0.25rem; font-size: 0.9rem; color: #555; }
  nav { display: flex; gap: 0.5rem; padding: 0 2rem; background: #fff;
        border-bottom: 1px solid #e0e0e0; }
  nav button { padding: 0.6rem 1rem; background: none; border: none;
               border-bottom: 2px solid transparent; cursor: pointer;
               font-size: 0.95rem; color: #444; }
  nav button.active { border-bottom-color: #555; font-weight: 600; color: #111; }
  main { padding: 1.5rem 2rem; max-width: 1100px; }
  section { display: none; }
  section.active { display: block; }
  .run-card { background: #fff; border: 1px solid #e0e0e0; border-radius: 8px;
              padding: 1rem; margin-bottom: 1rem; }
  .run-card summary { cursor: pointer; font-weight: 600; }
  .run-card .meta { color: #666; font-size: 0.85rem; margin-top: 0.25rem; }
  .scores { display: grid; grid-template-columns: repeat(5, 1fr);
            gap: 0.5rem; margin: 0.75rem 0; }
  .score { background: #f3f3f3; border-radius: 6px; padding: 0.5rem;
           text-align: center; font-size: 0.78rem; line-height: 1.2; }
  .score .num { font-size: 1.25rem; font-weight: 700; display: block; }
  .score.low { background: #fde7e7; }
  .score.mid { background: #fff5d6; }
  .score.high { background: #e1f5e8; }
  pre { background: #f6f8fa; padding: 0.75rem; border-radius: 6px;
        overflow-x: auto; font-size: 0.8rem; white-space: pre-wrap;
        word-break: break-word; max-height: 360px; overflow-y: auto; }
  textarea.feedback { width: 100%; min-height: 5rem; margin-top: 0.5rem;
                      padding: 0.5rem; border: 1px solid #d0d0d0;
                      border-radius: 6px; font-family: inherit; font-size: 0.9rem; }
  .saved { color: #2a9d4a; font-size: 0.8rem; margin-left: 0.5rem; }
  table.bench { width: 100%; border-collapse: collapse; margin-bottom: 0.5rem; }
  table.bench th, table.bench td { padding: 0.45rem 0.5rem;
                                   border-bottom: 1px solid #eee;
                                   text-align: left; font-size: 0.9rem; }
  .bar { display: inline-block; height: 0.85rem; background: #6aa9ff;
         vertical-align: middle; border-radius: 2px; margin-right: 0.4rem; }
  .delta-pos { color: #2a9d4a; font-weight: 600; }
  .delta-neg { color: #c43838; font-weight: 600; }
  .delta-zero { color: #888; }
  .empty { color: #888; font-style: italic; padding: 2rem 0; }
</style>
</head>
<body>
<header>
  <h1>__SKILL_NAME_HTML__ — Eval Review</h1>
</header>
<nav>
  <button class="tab-btn active" data-tab="outputs">Outputs</button>
  <button class="tab-btn" data-tab="benchmark">Benchmark</button>
</nav>
<main>
  <section id="outputs" class="active"></section>
  <section id="benchmark"></section>
</main>
<script>
const EVAL_LOG = __EVAL_DATA__;
const SANDBOX_RUNS = __RUNS_DATA__;
const SKILL_NAME = __SKILL_NAME_JSON__;
const METRICS = ["trigger_precision","workflow_coverage","output_clarity","red_flag_completeness","dep_accuracy"];
const FEEDBACK_KEY = "skill-builder-feedback:" + SKILL_NAME;

function loadFeedback() {
  try { return JSON.parse(localStorage.getItem(FEEDBACK_KEY) || "{}"); }
  catch { return {}; }
}
function saveFeedback(map) {
  localStorage.setItem(FEEDBACK_KEY, JSON.stringify(map));
}

// Defence-in-depth: even though render_html() coerces score / total on the
// Python side, anything that ends up in innerHTML must be either escaped
// (escapeHtml) or proven numeric (safeNumber). Returns null when the value
// is not a finite number; clamps into [min, max] otherwise.
function safeNumber(value, min, max) {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.max(min, Math.min(max, n));
}

function fmtNum(n) {
  return n == null ? "-" : String(n);
}

function scoreClass(s) {
  if (s == null) return "";
  if (s < 5) return "low";
  if (s < 8) return "mid";
  return "high";
}

// Escapes for BOTH HTML text and attribute contexts. The renderer concatenates
// fields like entryId and version directly into HTML attributes (data-id, id),
// so we MUST also escape `"` and `'` — otherwise an entry whose `id` contains
// a quote (e.g. coming from a hand-edited eval.json or an LLM-generated
// pipeline name) can break out of the attribute and inject markup.
// See smoke_test.check_review_attribute_xss for the regression guard.
function escapeHtml(text) {
  return String(text == null ? "" : text)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

function renderOutputs() {
  const root = document.getElementById("outputs");
  if (!EVAL_LOG.length) {
    root.innerHTML = '<p class="empty">No <code>data/evals.jsonl</code> entries found. ' +
      'Run <code>python scripts/collect_evals.py</code> to rebuild it from <code>projects/*/v*/eval.json</code>. ' +
      'For the committed human-readable ledger see <code>references/eval-log.jsonl</code>.</p>';
    return;
  }
  const fb = loadFeedback();
  const cards = EVAL_LOG.map((entry, i) => {
    const syntheticId = (entry.version || "v?") + "-" + (entry.pipeline || "?") + "-" + i;
    // Use entry.id (stable) as the feedback key; fall back to synthetic for old records.
    const entryId = entry.id || syntheticId;
    // Use entry.sandbox_run_id to locate the sandbox run directory, with entryId as fallback.
    const runId = entry.sandbox_run_id || entryId;
    const scores = entry.scores || {};
    const scoreCells = METRICS.map(m => {
      const v = safeNumber(scores[m], 0, 10);
      return '<div class="score ' + scoreClass(v) + '"><span class="num">' +
        fmtNum(v) + '</span>' + escapeHtml(m.replace(/_/g, " ")) + '</div>';
    }).join("");
    const sandbox = SANDBOX_RUNS[runId] || null;
    const detail = sandbox ? (
      '<h4>Actual</h4><pre>' + escapeHtml(sandbox.actual || "(empty)") + '</pre>' +
      '<h4>Expected</h4><pre>' + escapeHtml(sandbox.expected || "(empty)") + '</pre>'
    ) : "";
    const fbVal = fb[entryId] || "";
    const total = safeNumber(entry.total, 0, 50);
    const summaryLine = (entry.pipeline || "?") + " · " + (entry.version || "v?") +
      " · " + (entry.date || "") + " · total=" +
      fmtNum(total) + "/50";
    return (
      '<details class="run-card">' +
      '<summary>' + escapeHtml(summaryLine) + '</summary>' +
      '<div class="meta">' + escapeHtml(entry.notes || entry.top_improvement || "") + '</div>' +
      '<div class="scores">' + scoreCells + '</div>' +
      detail +
      '<label>Feedback (saved locally to your browser):</label>' +
      '<textarea class="feedback" data-id="' + escapeHtml(entryId) + '">' +
        escapeHtml(fbVal) + '</textarea>' +
      '<span class="saved" id="saved-' + escapeHtml(entryId) + '"></span>' +
      '</details>'
    );
  }).join("");
  root.innerHTML = cards;

  document.querySelectorAll("textarea.feedback").forEach(t => {
    t.addEventListener("input", () => {
      const id = t.dataset.id;
      const all = loadFeedback();
      all[id] = t.value;
      saveFeedback(all);
      const span = document.getElementById("saved-" + id);
      if (span) {
        span.textContent = "saved";
        clearTimeout(span._t);
        span._t = setTimeout(() => span.textContent = "", 1500);
      }
    });
  });
}

function renderBenchmark() {
  const root = document.getElementById("benchmark");
  if (!EVAL_LOG.length) {
    root.innerHTML = '<p class="empty">No <code>data/evals.jsonl</code> entries found. ' +
      'Run <code>python scripts/collect_evals.py</code> first.</p>';
    return;
  }
  // Per version: take the entry with the most score data (prefer entries with `scores`)
  const byVersion = {};
  EVAL_LOG.forEach(e => {
    const v = e.version || "v?";
    const cur = byVersion[v];
    const eHasScores = e.scores && Object.keys(e.scores).length > 0;
    const curHasScores = cur && cur.scores && Object.keys(cur.scores).length > 0;
    if (!cur || (eHasScores && !curHasScores)) {
      byVersion[v] = e;
    }
  });
  const versions = Object.keys(byVersion).sort((a, b) => {
    const an = parseInt(String(a).replace(/[^0-9]/g, ""), 10) || 0;
    const bn = parseInt(String(b).replace(/[^0-9]/g, ""), 10) || 0;
    return an - bn;
  });

  let out = '<h3>Score by version</h3><table class="bench"><thead><tr><th>Version</th>';
  METRICS.forEach(m => out += '<th>' + escapeHtml(m.replace(/_/g, " ")) + '</th>');
  out += '<th>Total</th></tr></thead><tbody>';
  versions.forEach(v => {
    const e = byVersion[v];
    out += '<tr><td>' + escapeHtml(v) + '</td>';
    METRICS.forEach(m => {
      const s = safeNumber((e.scores || {})[m], 0, 10);
      const w = s != null ? Math.round(s * 10) : 0;
      out += '<td><span class="bar" style="width:' + w + 'px"></span>' +
             fmtNum(s) + '</td>';
    });
    const total = safeNumber(e.total, 0, 50);
    out += '<td><b>' + fmtNum(total) + '/50</b></td></tr>';
  });
  out += '</tbody></table>';

  if (versions.length >= 2) {
    out += '<h3>Per-version delta</h3><table class="bench"><thead><tr>' +
      '<th>From → To</th><th>Total Δ</th><th>Regressions (≥ 2pt)</th></tr></thead><tbody>';
    for (let i = 1; i < versions.length; i++) {
      const a = byVersion[versions[i-1]], b = byVersion[versions[i]];
      const at = safeNumber(a.total, 0, 50) || 0;
      const bt = safeNumber(b.total, 0, 50) || 0;
      const dt = bt - at;
      const regressions = METRICS.filter(m => {
        const av = safeNumber((a.scores||{})[m], 0, 10) || 0;
        const bv = safeNumber((b.scores||{})[m], 0, 10) || 0;
        return (bv - av) <= -2;
      });
      const cls = dt > 0 ? "delta-pos" : dt < 0 ? "delta-neg" : "delta-zero";
      out += '<tr><td>' + escapeHtml(versions[i-1] + " → " + versions[i]) +
        '</td><td class="' + cls + '">' + (dt > 0 ? "+" : "") + dt + '</td>' +
        '<td>' + escapeHtml(regressions.length ? regressions.join(", ") : "(none)") +
        '</td></tr>';
    }
    out += '</tbody></table>';
  }
  root.innerHTML = out;
}

document.querySelectorAll(".tab-btn").forEach(btn => {
  btn.addEventListener("click", () => {
    document.querySelectorAll(".tab-btn").forEach(b => b.classList.remove("active"));
    document.querySelectorAll("section").forEach(s => s.classList.remove("active"));
    btn.classList.add("active");
    document.getElementById(btn.dataset.tab).classList.add("active");
  });
});

renderOutputs();
renderBenchmark();
</script>
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate self-contained HTML eval viewer for a skill"
    )
    parser.add_argument("--skill-root", default=".", help="Skill root dir (default: .)")
    parser.add_argument(
        "--output", default=None,
        help="Output HTML path (default: <skill-root>/review/review.html)",
    )
    args = parser.parse_args()

    skill_root = Path(args.skill_root).resolve()
    eval_log_path = skill_root / "data" / "evals.jsonl"
    sandbox_dir = skill_root / "sandbox" / "runs"
    out_path = (
        Path(args.output).resolve() if args.output
        else skill_root / "review" / "review.html"
    )
    skill_name = parse_skill_name(skill_root / "SKILL.md", default=skill_root.name)

    print(f"Skill:      {skill_name}")
    print(f"Eval log:   {eval_log_path}")
    print(f"Sandbox:    {sandbox_dir} {'(found)' if sandbox_dir.exists() else '(not found)'}")
    print()

    eval_log = load_eval_log(eval_log_path)
    print(f"Loaded {len(eval_log)} eval log entries")
    sandbox_runs = load_sandbox_runs(sandbox_dir)
    print(f"Loaded {len(sandbox_runs)} sandbox runs")

    html_doc = render_html(skill_name, eval_log, sandbox_runs)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(html_doc, encoding="utf-8")
    print(f"\nWrote {out_path}")
    print(f"Open with: open '{out_path}'")


if __name__ == "__main__":
    main()
