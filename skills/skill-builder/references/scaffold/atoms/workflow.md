# atom: workflow

The `## Workflow` section — ordered steps the skill executes.

## Always include

Every SKILL.md needs this atom. The workflow is what the skill *does*.

## Template (inline)

Use when the full procedure fits in ≲40 lines.

```markdown
## Workflow

### 1. <First step — verb-first>

<What the AI does. Concrete commands or file edits. No "think about" steps.>

### 2. <Next step>

<Explanation>

### 3. <Final step>

<Explanation, including what makes the workflow "done">
```

## Template (delegated to references/)

Use when the procedure exceeds ~40 lines or has its own protocol.

```markdown
## Workflow

Full protocol → `references/<topic>.md`

### 1. <Step name>

<2–4 line summary — enough to act without opening the reference>

### 2. <Step name>

<Summary>
```

## Rules

- **Steps are imperative, not descriptive.** "Run `git status`" not "the workflow checks status."
- **Each step is independently inspectable.** The reader should be able to skip to step 3 and know what to do.
- **No "decide if..." steps without a decision table.** Embed the table or link to one.
- **Exit criteria belong in the last step.** What does "done" look like?

## Common mistakes

- Workflows that mix prose and commands inconsistently — pick a style
- Steps that depend on hidden state from earlier in the conversation
- Workflows over 40 lines that should have been delegated to `references/`
