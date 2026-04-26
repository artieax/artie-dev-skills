# atom: trigger

The `## When to use` + `**Do not trigger** when:` block. Defines the boundary between this skill and adjacent skills.

## Always include

Every SKILL.md needs this atom. Skipping `Do not trigger` is the most common cause of trigger collisions.

## Template

```markdown
## When to use

- "<trigger phrase 1>"
- "<trigger phrase 2>"
- "<trigger phrase 3>"

**Do not trigger** when:

- <case where another skill is the right choice — name the other skill>
- <case that belongs to an adjacent skill>
- <ambiguous phrasing that *sounds* like a match but isn't>
```

## Rules

- **Trigger phrases are what the user types**, not internal jargon. `"commit this"` not `"invoke bommit pipeline"`.
- **Aim for 3 phrases.** One is too narrow, five+ tends to overlap with neighbors.
- **`Do not trigger` always names the alternative.** "Use `bommit` for commits" is better than "not for commits."
- **Boundary cases first.** If two skills share a domain, list the boundary explicitly.

## Common mistakes

- Listing trigger phrases that no real user would type
- Omitting `Do not trigger` ("we'll figure it out at runtime") — boundary collisions need to be encoded statically
- Trigger phrases that match a generic word like `"create"` or `"fix"` — too broad
