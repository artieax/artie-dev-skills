# atom: prompts-dir

Adds a `prompts/` directory for reusable LLM prompts loaded by scripts in `scripts/`. Each prompt is a markdown file with `{{var}}` placeholders, kept separate from Python code so it diff-reviews cleanly and can be edited without touching call-site logic.

## When to include

- The skill drives one or more `claude -p` (or similar) calls from a script
- Two or more call sites share the same prompt body
- The prompt is large enough that embedding it as a Python string would obscure the surrounding code
- You want non-Python contributors to be able to tune prompts

If the only LLM call is a single one-liner, inline it instead.

## Layout

```
skills/<name>/
├── SKILL.md
├── prompts/
│   ├── <role>-system.md      # system prompts, role: system
│   ├── <action>.md           # user prompts with {{var}} placeholders
│   └── repair-json.md        # shared utilities (JSON repair, retry, etc.)
└── scripts/
    ├── prompts.py            # loader: load(), render(name, **vars)
    └── <pipeline>.py         # call sites
```

## File conventions

- One file per logical prompt — `score.md`, `critique.md`, `refine.md`, not `all.md`
- Optional YAML frontmatter for metadata (`name`, `role`, `used_by`, `vars`, `description`) — strip before sending to the model
- `{{snake_case}}` placeholders only; missing vars render as empty string
- Keep prompts ≤ ~80 lines — if a prompt grows past that, split it into a system + user pair
- Lowercase, dash-separated names ending in `.md`

## Prompt template

```markdown
---
name: score
role: user
used_by: scripts/optimize.py (score_scaffold)
description: Scores a SKILL.md on 5 metrics, returns JSON.
vars:
  - scaffold: full SKILL.md to score
---

Score the following SKILL.md on 5 metrics, each 0-10.

SKILL.md:
{{scaffold}}

Output JSON only:
{"trigger_precision": N, ...}
```

## scripts/prompts.py loader

A minimal stdlib-only loader keeps the dependency footprint flat:

```python
from prompts import load, render
tmpl = load("score")                  # body with {{var}} placeholders
text = render("score", scaffold=md)   # placeholders filled in
```

## SKILL.md integration

Reference the prompts directory in the script that uses it:

```markdown
### 3. Score scaffold

```bash
python scripts/optimize.py --generate --description "..." --requirements "..."
```

Prompts loaded from `prompts/scaffold-system.md`, `prompts/scaffold-user.md`, `prompts/score.md`.
```

## When NOT to use

- Single ad-hoc LLM call → inline the string in the script
- Prompts that must stay in lockstep with code (e.g. JSON schema generated from a dataclass) → keep in code so they can't drift
