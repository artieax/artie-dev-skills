# Scaffold execution modes (A / B / C)

The same scaffold prompts (`prompts/scaffold-system.md`, `prompts/scaffold-user.md`, optionally `prompts/scaffold-fewshot-item.md`) drive three interchangeable ways to run **BUILD**. Pick the one your host supports — the **prompt files are the SSOT**; only the call layer changes.

Eval pipelines that invoke an LLM (`independent-evaluator`, `static-score`, `adversarial`, `hold-out`) reuse the same three modes; for eval-specific “best for” notes see [`../evals/atomic-builder.md`](../evals/atomic-builder.md#execution-modes).

---

## Summary table

| Mode | How it runs | Best for | Available on |
|---|---|---|---|
| **C. inline** (default) | The host LLM reads `prompts/scaffold-system.md` + renders `prompts/scaffold-user.md`, then answers itself. No script, no CLI, no subprocess. | one-shot scaffold; portable across hosts | every agent (Claude Code, Codex, Cursor, Gemini, OpenCode) |
| **B. Task subagent** | Host LLM spawns a context-free subagent via its Task / subagent primitive with `run_in_background=true`. The subagent gets the same rendered prompts; result returns to parent on completion. | long pipelines (BootstrapFewShot, evals); want non-blocking; want fresh executor semantics for free | Claude Code (Task tool), Anthropic Agent SDK |
| **A. subprocess** | `python scripts/optimize.py` calls `claude -p` via `scripts/agent.py`. Hermetic, scriptable, parallelisable with `&`. | CI / cron / batch optimization with > 1 trial | wherever `claude` CLI is installed |

Mode C is the default because it works on every host and needs zero infrastructure. Modes B and A are optimisations: B adds non-blocking + independent-evaluator parallelism on Claude Code; A adds repeatability + headless batch.

The artifact `data/optimized_prompt.json` is consumed identically across all three modes — it is just JSON loaded into the prompt template, so optimisation can be produced on one host and consumed on any other.

`data/*.json` is gitignored on purpose: the file embeds whole SKILL.md snapshots that drift fast (a stale checked-in copy teaches the optimizer to reproduce yesterday's mistakes), and the schema has expanded over time so old copies are silently incompatible with the current loader. Producers regenerate it; if you need to share it across machines, copy it out-of-band rather than committing it.

---

## Host environment matrix

When in doubt, detect what the host supports and pick the highest-capability mode. Mode C always works.

| Host | Subagent (Mode B) | `claude` CLI (Mode A) | Recommended |
|---|:---:|:---:|---|
| Claude Code | ✅ (Task tool) | ✅ | **B** for non-blocking, **A** for batch |
| Anthropic Agent SDK | ✅ | ✅ | **B** |
| Claude.ai (web) | ✗ | ✗ | **C** |
| Codex CLI | ✗ | ✅ if installed | **C**, or **A** when `claude` is on PATH |
| Cursor | ✗ | ✗ | **C** |
| Gemini extension | ✗ | ✗ | **C** |
| OpenCode | ✗ | depends | **C** |

Where the host has neither subagent nor `claude` CLI, all atoms still produce *output* — only the *runner* changes. `independent-evaluator` semantics on Mode-C-only hosts are achieved by opening a fresh chat and pasting the prompt manually.

---

## Mode C — inline (universal default)

Render and answer in the current conversation:

```
1. Read prompts/scaffold-system.md  → use as your system frame
2. Render prompts/scaffold-user.md with:
     description    = "<what this skill does>"
     requirements   = "<key constraints>"
     few_shot_block = ""   (or, if data/optimized_prompt.json exists,
                            inject the few_shot_examples per scaffold-fewshot-item.md)
3. Produce the SKILL.md draft as your answer.
```

---

## Mode B — Task subagent (Claude Code, non-blocking)

Same rendered prompts, but executed in a fresh background agent so the main conversation keeps moving:

```
host LLM:
  spawn Task(
    subagent_type="general-purpose",
    prompt=<rendered scaffold-user.md prompt>,
    run_in_background=true,
  )
  → continue with other work
  → on notification, write the returned SKILL.md to disk
```

Mode B is also the natural backend for the eval pipeline's `independent-evaluator` atom (`references/evals/atoms/independent-evaluator.md`) — both need an independent (context-free) agent (the IV&V principle).

---

## Mode A — subprocess (CI / cron / batch)

```bash
python scripts/optimize.py --generate \
  --description "What this skill does" \
  --requirements "Key constraints"
```

Uses `claude -p` via `scripts/agent.py` — no API key needed if Claude Code is signed in (set `bare=True` in `AgentConfig` only when running headless with `ANTHROPIC_API_KEY`). The LLM call layer (JSON parsing, repair retry, multi-turn chains) lives in `scripts/agent.py`; prompts come from the same `prompts/*.md`.

---

## Building the optimized prompt artifact

Run `collect_evals.py` + `optimize.py` after **≥ 8 evals** to generate `data/optimized_prompt.json` — fewer examples produce a high-variance demo selection that easily over-fits to one or two atypical SKILL.md instances. The producer step needs Mode A (or Mode B with manual orchestration); consumers only need to read the JSON file. The `optimize.py --generate` invocation is in **Mode A** above.
