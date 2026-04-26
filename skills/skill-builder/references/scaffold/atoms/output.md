# atom: output

The `## Output` section — what the user receives after the skill finishes.

## Always include

Every SKILL.md needs this atom. Without it, the skill's deliverable is undefined and evals can't score `output_clarity`.

## Template

```markdown
## Output

<Concrete description of the deliverable. Name files, commit hashes, report sections — be specific.>

### <Optional: variant 1>

```
<Sample output, formatted as the user will see it>
```

### <Optional: variant 2>

<Different shape — e.g., "phase-only invocations">
```

## Rules

- **Concrete, not abstract.** "Generates `skills/<name>/SKILL.md` and appends a row to `AGENTS.md`" beats "creates a skill."
- **Show the format.** A code block of the actual output the user will see is worth more than prose describing it.
- **Variants belong here, not in Workflow.** If the skill produces different outputs for different invocations, list each.
- **No future tense.** "Output: X" not "The skill will output X."

## Common mistakes

- Output sections that paraphrase the Workflow (the work, not the deliverable)
- Outputs described as "a report" or "a summary" with no shape
- Forgetting to mention side effects (commits, file moves, log appends) — they are part of the output
