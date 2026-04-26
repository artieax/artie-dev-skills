# atom: match-router

A dispatch mechanism inside an orchestrator's Workflow that auto-selects a sub-skill when intent is clear, and asks the user to choose when it is ambiguous.

## When to include

- The orchestrator has 2+ sub-skills and the right one depends on intent, not a fixed order
- Some triggers are unambiguous ("scaffold X" → always sub-skill A), others are not
- Silent wrong picks are worse than one occasional question

If all phases always run in sequence, use the plain `orchestrator` atom instead.  
If only one sub-skill ever applies, inline it — no router needed.

---

## Dispatch logic

Score each candidate against the user's request using these signal types:

| Signal type | Examples |
|---|---|
| **Named** | User says the sub-skill name or phase ("run eval", "just scaffold") |
| **State** | Prior output exists, current branch name, files present |
| **Scope** | "all", "just", "quickly", "from scratch" narrow or widen the match |
| **Negation** | "don't X" rules out candidates that would do X |

Decision rule:

```
one candidate matches clearly  →  auto-dispatch, no confirmation
two or more tie                →  ask the user (numbered list)
zero candidates score high     →  ask the user what they want
```

---

## SKILL.md pattern

```markdown
### 1. Match intent

Score each candidate against the request:

| Candidate | Match when |
|---|---|
| [`skill-a`](../skill-a/SKILL.md) | request mentions X, or file Y is present |
| [`skill-b`](../skill-b/SKILL.md) | request mentions Z, or skill-a output already exists |
| [`skill-c`](../skill-c/SKILL.md) | "start over", or no prior context found |

**One candidate clearly matches** → skip to step 2 with that candidate.

**Intent is ambiguous** → ask:

> Which would you like?
> 1. `skill-a` — [what it does in one clause]
> 2. `skill-b` — [what it does in one clause]
> 3. `skill-c` — [what it does in one clause]

Wait for the user's reply before continuing.

### 2. Run selected sub-skill

→ `skills/<selected>/SKILL.md`
```

---

## Ask format rules

- Numbered list, 1-indexed
- One-line description per option: describe the action, not the name
- One-sentence question — no preamble

**Bad:** "I'm not sure which approach to take. Could you tell me which of the following you'd prefer?"  
**Good:** "Which would you like?"

---

## Confidence signals checklist

When writing the match table, cover at least:

- Named intent (user said the phase name directly)
- State signals (does prior output exist? which branch/directory?)
- Scope qualifiers ("just", "all", "quickly")
- Negation ("not X", "skip X")

If none of these signals fire for any candidate, that is the zero-match case → ask.

---

## Dependency graph

Same as `orchestrator` — record router → candidate edges:

```
<router-skill> --> <candidate-a>
<router-skill> --> <candidate-b>
<router-skill> --> <candidate-c>
```
