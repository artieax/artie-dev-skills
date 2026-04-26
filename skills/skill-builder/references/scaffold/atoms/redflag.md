# atom: redflag

The `## Red flags` section — `Always` (mandatory practices) and `Never` (prohibitions).

## Always include

Every SKILL.md needs this atom. Red flags are the difference between a skill that works once and one that's safe to invoke.

## Template

```markdown
## Red flags

### Always

- <mandatory practice 1> — <one-line reason>
- <mandatory practice 2> — <one-line reason>

### Never

- <prohibition 1> — <one-line reason>
- <prohibition 2> — <one-line reason>
```

## Pattern source

Pick reusable patterns from `references/red-flags.md` rather than inventing per-skill rules. Skill-specific rules go alongside the cataloged ones.

## Rules

- **Each rule has a reason.** "Never push without instruction — destructive remote action" is actionable; "Never push" is dogma.
- **Always vs Never is exhaustive.** If something doesn't fit either, it isn't a red flag — it's a workflow note.
- **No conditionals.** "Always X unless Y" hides decisions. Encode Y as a separate `Never` or move the logic into Workflow.
- **Lift, don't invent.** If a rule applies to most skills, it lives in `references/red-flags.md` — reference it.

## Common mistakes

- Red flags that duplicate the Workflow section (the workflow already says to do X)
- Vague rules ("be careful with...") that don't specify the action to avoid
- Skipping `Always` because "everything is in Workflow" — Always is for cross-cutting practices, not workflow steps
