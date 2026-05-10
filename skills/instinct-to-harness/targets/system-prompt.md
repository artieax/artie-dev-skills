---
id: system-prompt
kind: harness-target
provider: any            # vendor-agnostic API system prompt fragment
reads: instinct + atom (rendering recipe)
writes: instincts/<slug>/variants/system-prompt.txt
deploys_to: stdout (or --out <file>)
default_method: copy
---

# system-prompt — short fragment for API system prompts

Generate a ≤ 50-token plain-text fragment usable inside an API system prompt.

## Variant template

```
<one imperative sentence in present tense>
```

No markdown, no headers, no code blocks.

## Constraints

- **≤ 50 tokens** (hard limit — anything longer wastes the budget)
- Imperative present tense
- One rule per fragment

## DEPLOY behaviour

- No canonical project path — system prompts are assembled at API call time
- Default: print to stdout
- `--out <path>`: write to a file the caller will read at runtime

## Best paired with

- Rendering atom: `kata` or `invariant-guard`
- Instincts that compress well — story-arc / decision-table won't fit
