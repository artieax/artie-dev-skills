# atom: meilisearch-index

Adds a local Meilisearch search surface for records owned by the skill, so the agent can query a small result set instead of reading every JSONL or Markdown record.

This atom is a structural add-on. Pair it with `scripts-dir` and `references-dir`; the scripts own index/query behavior, and the reference file records the schema and search policy.

## When to include

- The skill owns a growing corpus of records: JSONL rows, Markdown notes, assets, prompts, cases, examples, or run reports
- The corpus is expected to exceed about 50 records, or individual records are too large to load into context every run
- Users need fuzzy lookup, typo tolerance, prefix search, tag search, faceted filtering, or cross-file search
- Workflow steps repeatedly say "search existing records before creating a new one"
- The skill has append-only data and needs an explicit reindex command after bulk edits

## When not to include

- The skill has only a tiny static list; use `list-registry` or inline Markdown instead
- Exact key lookup is enough; use direct JSON/JSONL parsing
- The data is remote-only and should be queried through an external API every time
- Search is only for discovering which skill to invoke; that belongs to the host skill-discovery layer, not the generated skill

## Layout

```
skills/<name>/
├── SKILL.md
├── projects/
│   └── <records>.jsonl
├── references/
│   └── meilisearch-index.md
└── scripts/
    ├── index.mjs
    └── search.mjs
```

## Reference template

Create `references/meilisearch-index.md`:

```markdown
# Meilisearch index

| Index | Primary key | Source | Searchable fields | Filterable fields |
|---|---|---|---|---|
| `<skill>_<records>` | `id` | `projects/<records>.jsonl` | `title`, `description`, `tags` | `type`, `status`, `tags`, `updated_at` |

## Policy

- JSONL is the source of truth; Meilisearch is a derived index.
- Query Meilisearch before reading the full corpus.
- Rebuild the index after bulk edits, migrations, or schema changes.
- If Meilisearch is unreachable, keep writes in the source file and report that the index is stale.
```

## Script templates

Use Node ES modules and the built-in `fetch`. Keep the scripts small and skill-local; do not require an SDK unless the skill already has one.

`scripts/index.mjs`:

```js
#!/usr/bin/env node
// Usage: node scripts/index.mjs [--source=projects/records.jsonl] [--index=<skill_records>] [--pk=id] [--searchable=title,description,tags] [--filterable=status,tags]
// Output: rebuilds the Meilisearch index from the source JSONL file.
import { readFile } from 'node:fs/promises';

function readFlags(args) {
  return Object.fromEntries(args.filter((arg) => arg.startsWith('--')).map((arg) => {
    const eq = arg.indexOf('=');
    if (eq === -1) return [arg.slice(2), 'true'];
    return [arg.slice(2, eq), arg.slice(eq + 1)];
  }));
}

const flags = readFlags(process.argv.slice(2));

const source = flags.source || 'projects/records.jsonl';
const index = flags.index || '<skill_records>';
const pk = flags.pk || 'id';
const searchable = (flags.searchable || '').split(',').filter(Boolean);
const filterable = (flags.filterable || '').split(',').filter(Boolean);
const meiliUrl = process.env.MEILISEARCH_URL || 'http://localhost:7700';
const meiliKey = process.env.MEILISEARCH_KEY || 'searchlab-key';
const headers = { 'Content-Type': 'application/json', Authorization: `Bearer ${meiliKey}` };

async function meili(path, init = {}) {
  const res = await fetch(`${meiliUrl}${path}`, { ...init, headers: { ...headers, ...(init.headers || {}) } });
  if (!res.ok) throw new Error(`Meilisearch ${init.method || 'GET'} ${path} failed: ${await res.text()}`);
  return res.json();
}

async function waitTask(taskUid) {
  for (let i = 0; i < 40; i += 1) {
    const task = await meili(`/tasks/${taskUid}`);
    if (task.status === 'succeeded') return;
    if (task.status === 'failed') throw new Error(`Meilisearch task failed: ${JSON.stringify(task.error || {})}`);
    await new Promise((resolve) => setTimeout(resolve, 250));
  }
  throw new Error(`Timed out waiting for Meilisearch task ${taskUid}`);
}

async function ensureIndex() {
  const found = await fetch(`${meiliUrl}/indexes/${index}`, { headers });
  if (found.ok) return;
  if (found.status !== 404) throw new Error(`Meilisearch index lookup failed: ${await found.text()}`);
  const created = await meili('/indexes', {
    method: 'POST',
    body: JSON.stringify({ uid: index, primaryKey: pk }),
  });
  await waitTask(created.taskUid);
}

const docs = (await readFile(source, 'utf8'))
  .split('\n')
  .map((line) => line.trim())
  .filter(Boolean)
  .map((line) => JSON.parse(line));

await ensureIndex();

if (searchable.length) {
  const settings = await meili(`/indexes/${index}/settings/searchable-attributes`, {
    method: 'PUT',
    body: JSON.stringify(searchable),
  });
  await waitTask(settings.taskUid);
}

if (filterable.length) {
  const settings = await meili(`/indexes/${index}/settings/filterable-attributes`, {
    method: 'PUT',
    body: JSON.stringify(filterable),
  });
  await waitTask(settings.taskUid);
}

const indexed = await meili(`/indexes/${index}/documents`, {
  method: 'POST',
  body: JSON.stringify(docs),
});
await waitTask(indexed.taskUid);
console.log(`indexed ${docs.length} docs into ${index}`);
```

`scripts/search.mjs`:

```js
#!/usr/bin/env node
// Usage: node scripts/search.mjs "<query>" [--index=<skill_records>] [--limit=5] [--filter='status = active']
// Output: prints compact JSON search hits for LLM context.
const args = process.argv.slice(2);
function readFlags(args) {
  return Object.fromEntries(args.filter((arg) => arg.startsWith('--')).map((arg) => {
    const eq = arg.indexOf('=');
    if (eq === -1) return [arg.slice(2), 'true'];
    return [arg.slice(2, eq), arg.slice(eq + 1)];
  }));
}

const flags = readFlags(args);
const query = args.find((arg) => !arg.startsWith('--')) || '';

const index = flags.index || '<skill_records>';
const limit = Number.isFinite(Number(flags.limit)) ? Number(flags.limit) : 5;
const meiliUrl = process.env.MEILISEARCH_URL || 'http://localhost:7700';
const meiliKey = process.env.MEILISEARCH_KEY || 'searchlab-key';
const body = { q: query, limit };
if (flags.filter) body.filter = flags.filter;

const res = await fetch(`${meiliUrl}/indexes/${index}/search`, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${meiliKey}` },
  body: JSON.stringify(body),
});

if (!res.ok) throw new Error(`Meilisearch search failed: ${await res.text()}`);
const data = await res.json();
console.log(JSON.stringify(data.hits, null, 2));
```

Replace `<skill_records>` with a namespaced index uid such as `virtual_trader_hypotheses` or `prompt_forge_templates`.

## SKILL.md integration

Add a short search policy to the workflow:

````markdown
### Search existing records

Before creating a new record, query the local index:

```bash
node scripts/search.mjs "<query>" --limit=5
```

If results are relevant, reuse or update the existing record. If no result matches, append to the JSONL source and rebuild:

```bash
node scripts/index.mjs --source=projects/<records>.jsonl --index=<skill_records> \
  --searchable=title,description,tags --filterable=status,tags
```
````

Add requirements:

```markdown
- JSONL/Markdown source files are the source of truth; Meilisearch is derived `MUST`
- New or bulk-edited records are indexed before the final response `SHOULD`
- Meilisearch index uids are namespaced to the skill to avoid collisions `MUST`
```

## Environment

| Variable | Default | Purpose |
|---|---|---|
| `MEILISEARCH_URL` | `http://localhost:7700` | Local Meilisearch endpoint |
| `MEILISEARCH_KEY` | `searchlab-key` | Local master/search key |

Do not hardcode production secrets in generated skills. If the skill needs a non-local Meilisearch instance, read the URL and key from environment variables and document the required variables.

## Red flags

**Always:**
- Keep the source file append-only or migration-controlled; the index can always be rebuilt.
- Store enough fields in each document for search results to be actionable without opening the whole source record.
- Define filterable attributes explicitly before relying on filters in workflow commands.

**Never:**
- Treat Meilisearch as the source of truth. It is a derived cache.
- Read the entire corpus into LLM context when a targeted search can answer the question.
- Share one generic index uid across unrelated skills; collisions make search results untrustworthy.
