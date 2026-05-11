# Output templates — reporting shape

Use these ASCII blocks when reporting progress to the user. Adjust paths and scores to match the run.

---

## Full flow

```
📋 DESIGN
  ✅ Trigger: "create a new skill" / "scaffold a skill for X"
  ✅ Output: SKILL.md + references/*.md
  ✅ Boundary: bommit handles commits only; skill-builder handles design → improvement

🌿 WORKTREE: ../artie-dev-skills-<name>  [branch: feature/<name>]

📦 SCAFFOLD: skills/<name>/ created
  └── SKILL.md
  └── references/ (N files)

📊 EVAL — pipeline: quick
  trigger_precision:     6/10
  workflow_coverage:     7/10
  output_clarity:        6/10
  red_flag_completeness: 7/10
  dep_accuracy:          7/10
  total: 33/50
  top_improvement: "..."
  → saved to skills/<name>/references/eval-log.jsonl

🔗 DEPS: new-skill -.-> bommit added to dependency-graph.md

🚫 PUSH: waiting — will not push until explicitly told to
```

---

## Eval only

```
📊 EVAL — pipeline: <name>
  [scores or executor report]
  → saved to references/eval-log.jsonl
```

---

## Split only

```
✂️ SPLIT PROPOSAL
  Current: skills/<name>/  (N lines)
  Proposed: skills/<name>-a/ + skills/<name>-b/
  Confirm split? [Y/n]
```

---

## Deps only

```
🔗 DEPS SCAN
  Detected: new-skill -.-> bommit  (line 45)
  Add to dependency-graph.md? [Y/n]
```

---

## PR description

Use a normal product-engineering summary. Describe the change and validation,
not which model, agent, or delegation route produced it.

Title:

```
Add variables scaffold atom
```

Title rules:

- Use a plain product title.
- Do not prefix titles with tool or agent labels such as `[codex]`, `[claude]`,
  `[chatgpt]`, or `[bot]`.
- Keep automation provenance out of the title unless the PR changes that
  automation directly.

```markdown
## Summary

- <what changed>
- <what changed>

## Why

<why the change is useful>

## Validation

- `<command>`
- `<command>`
```

Rules:

- Do not mention reviewer/model/tool provenance such as ChatGPT, Claude, Codex,
  token-shield, or browser delegation unless the tool itself is the subject of
  the PR.
- If an external review route was unavailable, report that to the user in the
  final response, not in the PR description.
- Keep failed validation in the PR only when it materially affects merge risk.

---

## PR review comment

Use findings-first review language. If there are no findings, say so directly
and keep the comment about the diff.

```markdown
## Review

No findings.

Checked:

- <area 1>
- <area 2>
- <area 3>

Validation:

- `<command>`
```

Rules:

- Do not describe the review as "ChatGPT review", "Codex review", or any other
  tool-branded review in the PR comment.
- Put tool limitations, fallback routes, clipboard prompts, and manual handoff
  notes in the user-facing final response only.
- Prefer `Summary`, `Review`, `Checked`, `Validation`, and `Residual risk`
  headings over process narration.
