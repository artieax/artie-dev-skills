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
