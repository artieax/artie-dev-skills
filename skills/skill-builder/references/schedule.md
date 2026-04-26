# schedule — periodic skill improvement (Phase 7)

## Monthly skill review

Run the following checks once a month:

- eval total < 35 → propose executor pipeline iteration
- 2+ independent triggers detected → propose split
- unregistered dependencies detected → propose dependency-graph update

---

## Evals rotation {#evals-rotation}

`data/evals.jsonl` is append-only and can grow without bound. Keep it trim:

**Trigger:** `data/evals.jsonl` exceeds **200 lines**.

**Action:**

```bash
# Move all but the most recent 150 lines to the archive
lines=$(wc -l < data/evals.jsonl)
keep=150
excess=$((lines - keep))
head -n "$excess" data/evals.jsonl >> data/evals.archive.jsonl
tail -n "$keep" data/evals.jsonl > data/evals.jsonl.tmp && mv data/evals.jsonl.tmp data/evals.jsonl
```

`data/evals.archive.jsonl` is kept for audit but never read during normal EXTRACT — ignore it unless you explicitly need historical archaeology.

**Scheduling options** (same pattern as the monthly review above):

```jsonl
{"name":"evals-rotation","schedule":"0 9 * * 0","action":"if wc -l data/evals.jsonl > 200, rotate to archive keeping last 150 lines"}
```

```
/schedule weekly evals rotation: if data/evals.jsonl exceeds 200 lines, archive the oldest records keeping the last 150
```

## Scheduling options

Pick whichever fits your environment:

**Local cron** — append to your project's job log (e.g. `db/data/cron_jobs.jsonl`):

```jsonl
{"name":"skill-monthly-review","schedule":"0 9 1 * *","checks":["eval total < 35 → propose executor pipeline iteration","2+ independent triggers detected → propose split","unregistered dependencies detected → propose dependency-graph update"]}
```

**Claude Code `/schedule`** — one-time or recurring remote agent:

```
/schedule monthly skill-builder review: run Phase 7 checks and open a PR with proposals
```

**GitHub Actions** (if the repo is on GitHub) — add a `workflow_dispatch` + cron trigger to an existing workflow, or create a dedicated one:

```yaml
on:
  schedule:
    - cron: '0 9 1 * *'
  workflow_dispatch:
```

---

Structured periodic eval config and optimization script links → [`evals/index.md#periodic`](evals/index.md#periodic).
