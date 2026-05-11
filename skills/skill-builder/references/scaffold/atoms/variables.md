# atom: variables

Adds a `## Variables` section to a SKILL.md so repeated values, user-supplied
inputs, derived names, template placeholders, and file paths are declared once
before the workflow uses them.

Use this atom when a skill needs to turn loose user language into named values
that are reused across prompts, scripts, generated files, or acceptance checks.
The goal is to remove hidden state from the conversation: every important input
gets a stable `snake_case` name, source, default, and usage site.

## When to include

- The skill asks the user for 3 or more inputs
- The workflow reuses the same value in multiple steps
- The skill renders prompts, templates, paths, config files, or generated code
- Scripts expose CLI flags that mirror user input
- Outputs need deterministic names derived from user wording
- The skill creates other skills and needs to map `skill_name`, `skill_goal`,
  trigger phrases, constraints, atom picks, and output paths consistently

Do not include this atom for a short, single-action skill where all inputs are
obvious from the user's request and never reused.

## Section template

```markdown
## Variables

Resolve these before writing files or running scripts.

| Variable | Source | Required | Default | Used by |
|---|---|---:|---|---|
| `skill_name` | user input | yes | - | frontmatter, output path |
| `skill_slug` | derived from `skill_name` | yes | kebab-case `skill_name` | `skills/<skill_slug>/` |
| `skill_goal` | user input | yes | - | description, Workflow |
| `trigger_phrases` | user input or inferred | yes | - | `## When to use` |
| `constraints` | user input | no | empty list | Requirements, Red flags |

Rules:

- Ask for any missing required variable before the first file write.
- Infer optional variables only when the source is clear from the request.
- Keep variable names `snake_case`.
- Use `{{variable_name}}` placeholders in prompts and templates.
- Pass the same names to scripts as `--variable-name` flags when possible.
```

## Skill-builder variable set

When building a skill-creation skill or a skill that scaffolds SKILL.md files,
start from this variable set and delete fields that do not apply:

| Variable | Source | Required | Default | Used by |
|---|---|---:|---|---|
| `target_repo` | user input or cwd | yes | current repo | duplicate check, output path |
| `skill_name` | user input | yes | - | frontmatter, directory |
| `skill_slug` | derived | yes | kebab-case `skill_name` | `skills/<skill_slug>/` |
| `skill_goal` | user input | yes | - | description, overview |
| `target_user` | user input or inferred | no | "agent user" | trigger wording, Output |
| `user_inputs` | user input | yes | - | `## Variables`, Workflow |
| `atom_preset` | user input or PICK step | no | `minimal` | scaffold composition |
| `selected_atoms` | PICK step | yes | required content atoms | scaffold composition |
| `trigger_phrases` | user input or inferred | yes | - | `## When to use` |
| `do_not_trigger` | inferred from adjacent skills | yes | - | boundary section |
| `output_paths` | derived | yes | `skills/<skill_slug>/...` | Output, Requirements |
| `acceptance_requirements` | user input or inferred | yes | one `MUST` minimum | Requirements |

## Workflow integration

Add variable resolution as the first Workflow step:

```markdown
### 1. Resolve variables

Read `## Variables`. Fill values from the user's request first, then derive
the dependent values in table order. Ask the user only for missing required
variables that cannot be safely inferred.
```

For script-backed skills, mirror the table in the script interface:

```bash
node scripts/build.mjs \
  --skill-name "{{skill_name}}" \
  --skill-goal "{{skill_goal}}" \
  --atom-preset "{{atom_preset}}"
```

For prompt-backed skills, declare the same placeholders in prompt frontmatter:

```markdown
---
vars:
  - skill_name
  - skill_goal
  - selected_atoms
---

Build `{{skill_name}}` for:
{{skill_goal}}
```

## Rules

- Variables describe runtime inputs and derived values, not implementation
  preferences. Keep coding style and process rules in Red Flags or Requirements.
- Derived variables must name their source variable.
- Required variables must be checked before irreversible actions.
- Optional variables need defaults that are concrete enough to execute.
- Secrets are never stored as variables in SKILL.md. Reference environment
  variable names instead, for example `API_TOKEN_ENV=GITHUB_TOKEN`.
- If a variable affects file paths, show the resulting path in Output.

## Common mistakes

- Asking the user the same thing in multiple workflow steps instead of resolving
  one variable up front
- Using different names for the same concept, such as `name`, `skill`, and
  `slug`
- Leaving placeholders like `{{topic}}` in prompts without declaring them in
  `## Variables` or prompt frontmatter
- Treating inferred values as facts without recording the inference source
