# atom: stdout-delegate

Lets a script emit LLM instructions via stdout. The host agent reads the output, executes each directive, and writes results back — no API key, no `claude` CLI, no SDK import needed inside the script.

## When to include

- A script needs LLM help for part of its work (summarising, classifying, generating text)
- The script environment may not have an Anthropic API key or `claude` on PATH
- You want to keep the script dependency-free while still using the host's LLM capability

Do not use when the script already uses `agent.py` (Mode A) — they are alternatives, not complements.

## Protocol

Any line printed to **stdout** matching the format below is treated as an LLM directive:

```
__LLM_DELEGATE__: <json>
```

JSON fields:

| Field | Type | Required | Description |
|---|---|---|---|
| `prompt` | string | yes | Instruction for the LLM |
| `out` | string | no | File path to write the LLM response into |
| `id` | string | no | Label so the workflow step can reference the result by name |
| `system` | string | no | System prompt to prepend |
| `json` | boolean | no | `true` → ask the LLM for JSON output |

All other stdout lines are treated as normal script output and are not processed.

### Minimal example

```
__LLM_DELEGATE__: {"prompt":"Summarise this diff in one sentence: ...","out":"tmp/summary.txt"}
```

### JSON output example

```
__LLM_DELEGATE__: {"prompt":"Classify this commit as feat/fix/chore.","json":true,"out":"tmp/label.json"}
```

## Helper utilities

Copy the helper that matches your script language — or paste the single `print` call inline.

**Python** (`scripts/delegate.py` in your skill):

```python
import json, sys

def llm_invoke(prompt, *, out=None, system=None, json_mode=False, id=None):
    d = {"prompt": prompt}
    if out:      d["out"]    = out
    if system:   d["system"] = system
    if json_mode: d["json"]  = True
    if id:       d["id"]     = id
    print(f"__LLM_DELEGATE__: {json.dumps(d, ensure_ascii=False)}", flush=True)
```

**Node** (`scripts/delegate.mjs` in your skill):

```js
export function llmInvoke({ prompt, out, system, json = false, id } = {}) {
  const d = { prompt };
  if (out)    d.out    = out;
  if (system) d.system = system;
  if (json)   d.json   = true;
  if (id)     d.id     = id;
  process.stdout.write(`__LLM_DELEGATE__: ${JSON.stringify(d)}\n`);
}
```

## SKILL.md Workflow integration

Write the step so that **you** (the provider — Claude Code, Cursor, Codex, or any agent reading this SKILL.md) process the directives after the script exits. The instruction is addressed to whoever is executing the skill.

````markdown
### 3. Classify items

```bash
node scripts/classify.mjs --input references/items.json
```

For each `__LLM_DELEGATE__:` line the script printed:
- Parse the JSON payload
- Call your LLM with `prompt` (prepend `system` as the system prompt if present)
- If `json: true`, request JSON output
- Write the response to `out`, creating parent directories as needed
````

## Execution model

Directives are processed **after the script exits** — they are not streamed in real time. If a later directive needs the result of an earlier one in the same run, route that dependency through a file or split it into two workflow steps.

## Relationship to other execution modes

| Mode | Who calls the LLM | Needs API key / CLI |
|---|---|---|
| A. subprocess (`agent.py`) | `claude -p` inside the script | yes (`claude` on PATH) |
| B. Task subagent | Host spawns a background Task | Claude Code only |
| C. inline | Host answers directly | no — universal default |
| **D. stdout-delegate (this atom)** | **Script signals; host executes** | **no — universal** |

Mode D is the right pick when Mode A isn't available and Mode C would require inlining too much logic into the SKILL.md prose.
