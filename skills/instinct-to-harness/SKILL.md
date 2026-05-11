---
name: instinct-to-harness
description: 'Render instincts into AI harness files (claude-path, cursor-mdc, agents-md, …) using a catalog of pluggable rendering atoms × harness targets; presets bundle a target list with rendering choices.'
author: '@artieax'
---

# instinct-to-harness

Take instincts produced by `session-to-instinct` (markdown files at `../session-to-instinct/instincts/<slug>.md`) and render them as **harness files** — the config formats that AI coding assistants read to shape their behavior.

The skill follows the same **atom × preset pipeline** pattern as its sibling:

- **atoms/** — rendering-recipe catalog; each `atoms/<id>.md` describes one writing style (`invariant-guard`, `decision-table`, `kata`, …)
- **targets/** — harness destinations; each `targets/<id>.md` describes one output format (`claude-path`, `cursor-mdc`, `agents-md`, …)
- **presets/** — named bundles; each `presets/<id>.md` declares which targets to emit and which rendering atom each uses
- **instincts/** — generated outputs (canonical instinct + variants per target), all kept INSIDE this skill until DEPLOY

You pick a preset (or list targets manually), choose a rendering atom per target (auto from instinct's `best_preset` by default), and the pipeline runs `EXTRACT → PICK → BUILD → DEPLOY`.

## When to use

- "Convert this instinct into a Claude rule"
- "BROADCAST --slug git-sequential-commits"
- "EMIT all approved instincts to claude-path"
- "DEPLOY the standard preset"
- "What's covered for the git domain?"

**Do not trigger** when:
- The user wants to extract instincts from a session log (use `session-to-instinct`)
- The user wants to write a rule by hand without instincts as input
- The request is to search or view instincts only (use `session-to-instinct LIST` / `SHOW`)

---

## Catalog

### Atoms — rendering-recipe building blocks (`atoms/`)

Each atom is a small markdown file describing one writing style. The instinct's body and frontmatter are passed through the chosen atom to produce a variant.

| atom | shape | fits polarity | typical pairing |
|---|---|---|---|
| [`invariant-guard`](atoms/invariant-guard.md) | Hard DO/DON'T block | never, bad | failure-cluster instincts |
| [`decision-table`](atoms/decision-table.md) | Situation × action grid | any | 3+ branching corrective |
| [`symptom-cause-fix`](atoms/symptom-cause-fix.md) | Diagnostic runbook | never, bad | enforcement_mode: script |
| [`kata`](atoms/kata.md) | Minimal copy-paste recipe | good | success-pattern instincts |
| [`anti-pattern-gallery`](atoms/anti-pattern-gallery.md) | NG / OK code pair | never, bad | code-style instincts |
| [`escalation-ladder`](atoms/escalation-ladder.md) | Try X, then Y, then Z | any | ordered fallbacks |
| [`story-arc`](atoms/story-arc.md) | Narrative WHY | any | incident-driven instincts |
| [`when-dont-when`](atoms/when-dont-when.md) | Two-column use vs don't-use | any | tool/method selection |

Read the atom file directly for its template, anti-patterns, and what to pair it with.

### Targets — harness destinations (`targets/`)

Each target documents one harness format. The variant is rendered by combining `atom × target`. Targets are tagged with a **provider** (which AI vendor reads them) so you can filter by provider without listing every target.

| target | provider | renders to | deploys to | default method |
|---|---|---|---|---|
| [`claude-path`](targets/claude-path.md) | claude | `…/claude-path.md` | `.claude/rules/<slug>.md` | symlink |
| [`claude-global`](targets/claude-global.md) | claude | `…/claude-global.txt` | append to `CLAUDE.md` | append |
| [`cursor-mdc`](targets/cursor-mdc.md) | cursor | `…/cursor-mdc.mdc` | `.cursor/rules/<slug>.mdc` | symlink |
| [`agents-md`](targets/agents-md.md) | codex | `…/agents-md.md` | insert into `AGENTS.md` | append |
| [`gemini-md`](targets/gemini-md.md) | gemini | `…/gemini-md.md` | insert into `GEMINI.md` | append |
| [`copilot-md`](targets/copilot-md.md) | copilot | `…/copilot-md.md` | insert into `.github/copilot-instructions.md` | append |
| [`skill-constraint`](targets/skill-constraint.md) | any | `…/skill-constraint.md` | append to a sibling SKILL.md | append |
| [`system-prompt`](targets/system-prompt.md) | any | `…/system-prompt.txt` | stdout (or `--out`) | copy |

### Providers — filter targets by AI vendor

A **provider** is a group of targets read by the same AI vendor.

| provider | targets |
|---|---|
| `claude` | claude-path, claude-global, skill-constraint¹ |
| `cursor` | cursor-mdc |
| `codex` | agents-md |
| `gemini` | gemini-md |
| `copilot` | copilot-md |
| `any` | skill-constraint, system-prompt (vendor-agnostic) |

¹ skill-constraint is `provider: any` (read by whichever agent runs the skill), but Claude Code is the most common reader.

Use `--provider <id>` (or `--providers <id,id>`) to emit/deploy to a specific vendor only:

```
EMIT      --slug git-sequential-commits --provider claude
BROADCAST --slug X --providers claude,cursor
DEPLOY    --slug X --provider claude --all
```

When `--provider` is set, `any`-tagged targets are NOT included (use `--provider any` explicitly or pass it in the list).

### Presets — named target bundles (`presets/`)

| preset | targets bundled |
|---|---|
| [`minimal`](presets/minimal.md) | `claude-path` |
| [`standard`](presets/standard.md) | `claude-path` + `skill-constraint` |
| [`broadcast`](presets/broadcast.md) | claude-path + cursor-mdc + agents-md + gemini-md + copilot-md + skill-constraint |

Add new presets by dropping a file in `presets/`.

---

## Pipeline

```
session-to-instinct/instincts/<slug>.md   ← input (markdown with frontmatter)
      │
      ▼  Phase 1: EXTRACT
   selected instincts        ← --slug / --domain / --polarity / --approved / --promotion-target
      │
      ▼  Phase 2: PICK
   target × atom pairs       ← from --preset, --targets, --atom, or instinct's best_preset
      │
      ▼  Phase 3: BUILD  (writes ONLY inside this skill)
   instincts/<slug>/source.md
   instincts/<slug>/variants/<target>.<ext>
   instincts/<slug>/manifest.json
   emissions.jsonl (appended)
      │
      ▼  Phase 4: DEPLOY  (separate command; touches external project paths)
   .claude/rules/<slug>.md      ← copy / symlink / append
   .cursor/rules/<slug>.mdc
   AGENTS.md (insert)
   …
   deploys.jsonl (appended)
```

### Storage layout (everything inside the skill)

```
<skill-root>/instinct-to-harness/
├── SKILL.md
├── atoms/                          ← rendering-recipe catalog
├── targets/                        ← harness-target catalog
├── presets/                        ← named target bundles
├── instincts/                      ← canonical + variants per slug
│   └── <slug>/
│       ├── source.md               ← canonical master (target-agnostic prose)
│       ├── manifest.json           ← which atoms this came from + deploy state
│       └── variants/
│           ├── claude-path.md
│           ├── cursor-mdc.mdc
│           ├── agents-md.md
│           ├── skill-constraint.md
│           ├── skill-constraint.detail.md   ← companion detail file (see targets/skill-constraint.md)
│           └── system-prompt.txt
├── emissions.jsonl                 ← BUILD log (one record per variant write)
├── deploys.jsonl                   ← DEPLOY log (one record per external placement)
└── references/
```

`<skill-root>` resolves to wherever the skill instance is mounted — typically `.agent/skill/instinct-to-harness/` in the user's project. Source instincts are read from the sibling skill at `../session-to-instinct/instincts/<slug>.md`.

#### manifest.json schema

```json
{
  "slug": "git-sequential-commits",
  "instinct_ids": ["uuid1"],
  "created_at": "2026-05-09T10:00:00Z",
  "updated_at": "2026-05-09T10:30:00Z",
  "variants": {
    "claude-path": { "built_at": "2026-05-09T10:00:00Z", "atom": "invariant-guard" },
    "cursor-mdc":  { "built_at": "2026-05-09T10:00:00Z", "atom": "invariant-guard" },
    "skill-constraint": {
      "built_at": "2026-05-09T10:00:00Z",
      "atom": "invariant-guard",
      "companion_files": ["skill-constraint.detail.md"]
    }
  },
  "deployments": {
    "claude-path": {
      "deployed_to": ".claude/rules/git-sequential-commits.md",
      "method": "symlink",
      "last_synced": "2026-05-09T10:05:00Z",
      "detail_ref": null,
      "depends_on": []
    },
    "skill-constraint": {
      "deployed_to": ".agent/skill/<target-skill>/SKILL.md",
      "method": "append",
      "last_synced": "2026-05-09T10:06:00Z",
      "detail_ref": ".agent/skill/<target-skill>/details/git-sequential-commits.detail.md",
      "depends_on": []
    }
  }
}
```

**Field semantics:**

| field | type | required | meaning |
|---|---|---|---|
| `deployed_to` | string (path) | yes | External path where the variant was placed |
| `method` | enum: `copy` \| `symlink` \| `append` | yes | How the placement was performed |
| `last_synced` | ISO-8601 | yes | Timestamp of the most recent successful DEPLOY for this target |
| `detail_ref` | string (path) \| null | required when present | External path of a companion file this deployment writes alongside the main artifact (e.g. `skill-constraint`'s detail file). UNDEPLOY removes both `deployed_to` and `detail_ref`. |
| `depends_on` | array of target ids | required (default `[]`) | Other deployed targets whose external content this deployment cites or embeds. Drives UNDEPLOY cascade — see `targets/skill-constraint.md → UNDEPLOY: cascading repair`. |

When a target can reference another deployed target's external path (e.g. `skill-constraint`'s detail file links to `claude-path`'s rule file), the rendering atom MUST populate `depends_on` at BUILD time so the cascade algorithm has the dependency graph it needs.

**Legacy manifests (no `depends_on` / `detail_ref` field):** UNDEPLOY MUST treat absent `depends_on` as "unknown, possibly non-empty" — never as a confirmed empty list. The required fallback uses **tool-owned markers only** to avoid clobbering hand-edits:

1. For each remaining deployment on the slug, locate its tool-owned content on disk: the marker-bounded block (`<!-- instinct:<slug>:<target> START -->` … `END -->`) for append-style targets, or the entire file for `copy`/`symlink` targets.
2. If no marker block is found at the expected path on an append-style target, the file has been hand-edited or removed: **fail closed** with a clear error pointing at the slug+target. Do NOT diff a fresh render against arbitrary file contents — that risks classifying user edits as dependencies and silently overwriting them.
3. Append-style targets (`agents-md`, `gemini-md`, `copilot-md`, `skill-constraint`) are conservatively re-rendered as a group for the slug because their marker blocks frequently embed cross-target references. `copy`/`symlink` targets are only re-rendered if their tool-owned content (the file itself) no longer reflects the post-UNDEPLOY state byte-for-byte.
4. After the cascade completes, write `depends_on` (and `detail_ref` if applicable) back into `manifest.json` so the next UNDEPLOY has a deterministic graph.

---

## Phase 1 — EXTRACT (instinct selection)

Filter which instincts enter the pipeline.

| flag | effect |
|---|---|
| `--slug <slug>` | Single instinct by filename |
| `--id <uuid>` | Single instinct by frontmatter `id` |
| `--domain <name>` | All instincts matching `domain` |
| `--polarity never\|bad\|good` | Filter by polarity |
| `--source-atom <atom-id>` | Only instincts produced by a specific extraction atom |
| `--promotion-target rule\|skill\|doc\|security-rule` | Only instincts whose `promotion_targets` includes the value |
| `--approved` | Explicit form of the default — only `review_status: approved` (redundant with default; useful in scripts to assert intent) |
| `--include-pending` | Allow `review_status: pending` instincts (default: skipped) |
| `--include-deferred` | Allow `review_status: deferred` instincts (default: skipped) |
| `--unemitted` | Only instincts not yet built for the chosen target |

**Default selectable set is `review_status: approved` only.** `pending`, `deferred`, and `rejected` are skipped unless an explicit opt-in flag is passed (`--include-pending`, `--include-deferred`). `rejected` has no opt-in flag and is always skipped — retire instincts via `session-to-instinct REVIEW` instead of trying to emit them.

---

## Phase 2 — PICK (target × atom pairing)

Two independent selections define each variant.

### A. Target selection

Target resolution follows the **canonical precedence** documented in
[`../session-to-instinct/references/config-schema.md` → "Emit"](../session-to-instinct/references/config-schema.md). The exact ordered steps are:

1. **Source list** (highest priority wins): CLI `--targets <list>` > CLI `--preset <name>` > `emit.preset` in `.instinct.yml` > top-level `preset:` shorthand > instinct's `promotion_targets` mapped through `emit.routes`.
2. **Preset auto-enable**: when a preset is in effect, the preset's `providers:` and bundled targets are implicitly flipped to `enabled: true` for the run.
3. **Per-instinct route filter**: when the source list (step 1) came from a preset or `--targets`, intersect with `expand(instinct.promotion_targets) via emit.routes.<pt>.targets`. This prevents `preset: standard` from emitting `skill-constraint` for a `[rule]`-only instinct that has no `target_skill`. **Route-mismatch on explicit CLI**: if `--target`/`--targets` names a target this filter would drop, the run hard-errors unless `emit.allow_route_override: true`; under override, only the CLI-named target is unioned back in for that one instinct (presets are NOT unioned in by override).
4. **Provider gate**:
   - `--provider <list>` is set → keep only targets whose `provider:` matches; `provider: any` is NOT auto-included (pass `any` in the list to keep it).
   - Otherwise, drop targets where `emit.providers.<provider>.enabled: false`; `provider: any` targets follow `emit.providers.any.enabled` (default `true`).
5. **Per-target enablement**: drop targets where `emit.targets.<target>.enabled: false`.
6. CLI `--target` is a post-hoc override (allowed only when `emit.allow_route_override: true`); it still passes through gates 4–5.

This lets you keep a target enabled in `emit.targets` but temporarily disable a whole vendor via `emit.providers.cursor.enabled: false` or `--provider claude`.

Default mapping when only `promotion_targets` is set:

| promotion_target | suggested target |
|---|---|
| `rule` | `claude-path` |
| `skill` | `skill-constraint` |
| `doc` | `agents-md` or `gemini-md` |
| `security-rule` | `claude-global` |
| `consolidation` | no harness emission; runs `dream-assisted` instead |

### B. Rendering atom selection

Per-target. **Canonical precedence — must match `../session-to-instinct/references/config-schema.md → "Per-target rendering-atom resolution"` verbatim**:

1. CLI `--atom <id>`
2. `emit.targets.<target>.default_atom`
3. `emit.routes.<promotion-target>.default_atom`
4. instinct's `best_preset`
5. heuristic fallback (see below)

Presets do not introduce a separate precedence path: a preset's bundled targets are merged into `emit.targets` (with their `default_atom` fields) at preset auto-enable time, so any preset-supplied default surfaces through step 2.

Heuristic fallback:

```
source_atom = failure-cluster + polarity = never  →  invariant-guard
source_atom = success-pattern                     →  kata or escalation-ladder
source_atom = incident-driven                     →  invariant-guard (strict) or story-arc
polarity = never + corrective has NG/OK blocks    →  anti-pattern-gallery
corrective has 3+ branches                        →  decision-table
enforcement_mode = script                         →  symptom-cause-fix
two competing approaches in body                  →  when-dont-when
else                                              →  invariant-guard
```

---

## Phase 3 — BUILD (writes only inside the skill)

1. Create or update `instincts/<slug>/source.md` (canonical prose; target-agnostic).
2. Render the variant for the chosen target → `instincts/<slug>/variants/<target>.<ext>`.
   Some targets emit additional **companion files** during the same BUILD step (e.g. `skill-constraint` writes `skill-constraint.detail.md` so DEPLOY can place a real reference file under `<target-skill>/references/<slug>.md` when claude-path is not deployed). Companion files share the variant's lifecycle: regenerated on every BUILD for that target, deleted on UNBUILD.
3. Update `instincts/<slug>/manifest.json` (append `instinct_ids`; replace target entry under `variants`; companion files listed under `variants.<target>.companion_files`).
4. Append a record to `<skill-root>/emissions.jsonl` (one record per primary variant; companion files counted in the same record's `companion_files` array).
5. **Stamp the source instinct.** Update only the `harness` block of `../session-to-instinct/instincts/<slug>.md`:
   - add the target id to `harness.built`
   - set `harness.last_emitted_at` to now
   - leave the rest of the file untouched

This stamp is the source-of-truth marker for "this instinct has already been built". It lets `session-to-instinct LIST --unemitted` find work that still needs an EMIT pass without traversing this skill's manifests.

### Overwrite policy

| file | rule |
|---|---|
| `instincts/<slug>/source.md` | created on first BUILD; preserved unless `--regen-source` |
| `instincts/<slug>/variants/<target>.*` | overwritten on each BUILD for that target (variants are derived) |
| `manifest.json` | updated in place |

---

## Phase 4 — DEPLOY (external placement)

DEPLOY is a separate command. It is the only step that touches paths outside this skill.

### Deploy path sandboxing (security)

DEPLOY MUST refuse to write outside the **deploy root**. The deploy root is the
project root (`git rev-parse --show-toplevel`, falling back to the current working
directory). Every external path produced by DEPLOY — including those resolved from
`--target-skill`, `--out`, `target_skill` frontmatter, or `.instinct.yml` — passes
through these gates **before any filesystem write**:

1. **Canonicalize**: resolve to an absolute path (resolve symlinks, normalise `..` / `.`).
2. **Confine**: the canonical path MUST start with `<deploy-root>/`. Reject anything else.
3. **Reject traversal inputs**: any user-supplied path containing `..` segments or a literal absolute path (`/…`, `~/…`, `C:\…`) is rejected up front, before canonicalization, with a clear error.
4. **Allowlist for shared files**: append-style targets (e.g. `AGENTS.md`, sibling `SKILL.md`) MUST resolve to a file inside `<deploy-root>` and the file's parent directory MUST already exist; DEPLOY never creates parent directories outside `<deploy-root>`.
5. **Symlink targets**: if a deployed file is a symlink, the symlink's *target* must also satisfy gates 1–2; otherwise DEPLOY refuses to write through it.

`--deploy-root <path>` lets advanced users pin the root explicitly (still subject to
gates 1–5 against the supplied root). There is no flag to bypass the sandbox; an
out-of-root deploy is always a hard failure.

### Methods

| method | behaviour |
|---|---|
| `copy` | file copy from `instincts/<slug>/variants/X` to deploy target |
| `symlink` | symlink the deploy target to the variant (recommended for active iteration) |
| `append` | append/insert a marked block into an existing file (used for shared files like `AGENTS.md`) |

Each target's default method is documented in `targets/<id>.md`.

### Deploy record

```jsonl
{
  "slug": "<slug>",
  "target": "<target-id>",
  "deployed_to": "<external-path>",
  "method": "copy|symlink|append",
  "deployed_at": "<ISO-8601>"
}
```

### Stamp the source instinct (after each successful DEPLOY)

Update only the `harness` block of `../session-to-instinct/instincts/<slug>.md`:
- add the target id to `harness.deployed`
- set `harness.last_deployed_at` to now

`UNDEPLOY` removes the target id from `harness.deployed` and updates `last_deployed_at` to the previous deploy time (or `null` if this was the only one).

### Undo

`UNDEPLOY --slug <slug> --target <target>` removes the external file (copy or symlink) or the marked append block, and updates the source instinct's `harness.deployed` list. Never touches `instincts/<slug>/` or anything else in the source instinct file.

**Cascade**: dependent targets are re-rendered using the dependency graph in `manifest.json > deployments.<target>.depends_on`. A dependent is any deployment record whose `depends_on` list contains the just-removed target id. For each dependent:

1. Re-render its variant against the new `harness.deployed` snapshot (the removed target id is gone).
2. Rewrite the dependent's external file (copy/symlink) or its marker-bounded append block in place.
3. Update `manifest.json > deployments.<dependent>.last_synced`.
4. If the dependent owns a `detail_ref` companion file, regenerate that companion alongside the main artifact in the same atomic step.

See `targets/skill-constraint.md → UNDEPLOY: cascading repair` for the canonical algorithm. Dependents whose `depends_on` is empty (default) are not affected by another target's UNDEPLOY.

### Concurrency & atomicity

A single BUILD/DEPLOY/UNDEPLOY run touches three classes of files: per-slug state (`manifest.json`, `instincts/<slug>/variants/*`, `<slug>` companion files), the source instinct's `harness:` block (in the sibling skill's `instincts/<slug>.md`), and shared append targets (`AGENTS.md`, sibling `SKILL.md`, etc.). Concurrent runs MUST follow these rules:

1. **Per-slug lock** — acquire an exclusive lock at `instincts/<slug>/.lock` (or an OS file lock on `manifest.json`) for the entire BUILD/DEPLOY/UNDEPLOY of that slug. A second concurrent run for the same slug waits or fails fast with `EAGAIN`.
2. **Single-slug-at-a-time invariant** — `BROADCAST` and `DEPLOY --all` process slugs serially. A run NEVER holds more than one slug lock at a time: acquire slug lock → do all work for that slug (including all shared-file writes) → release slug lock → move to next slug. This eliminates slug-vs-slug deadlock.
3. **Per-shared-file lock** — every shared file (append-style external targets like `<deploy-root>/AGENTS.md`, plus the per-skill log files `emissions.jsonl` and `deploys.jsonl`) MUST acquire its own exclusive lock keyed on the absolute path (e.g. `<file>.lock`) before any read-modify-write. Within a single slug run, acquire shared-file locks in **lexicographic order** of absolute path, hold each only as long as needed for its read-modify-write, and release before acquiring the next. Combined with rule 2, the global lock-acquisition order is total: `slug-lock < shared-file-lock(path1) < shared-file-lock(path2) < …`.
4. **Atomic write** — every file written by this skill (variants, companions, manifest, deploy logs) is written via `temp file + rename` on the same filesystem. The visible state at any external observer is either pre-write or post-write, never half-written.
5. **Atomic append** — append-style targets read the file, splice the marker-bounded block in memory, and rewrite the whole file via temp+rename. There is no in-place append.
6. **JSONL log writes** — `emissions.jsonl` and `deploys.jsonl` are appended to under their per-file lock from rule 3. The standard pattern is: lock → read tail (optional dedup) → append the new line → fsync → release lock. Lockless `>>` redirection is forbidden because two slugs can interleave partial lines.
7. **Frontmatter compare-and-swap** — when stamping `harness:` in the source instinct, read the file and capture a CAS token of `(inode, size, mtime, sha256-of-bytes)` (sha256 is REQUIRED — mtime alone is insufficient on filesystems that preserve timestamps or have second-resolution mtime). Mutate only the `harness:` block in memory, then re-read the CAS token and compare to the captured one. If any field differs, retry the read-mutate-rewrite up to 3 times before failing the run. Rewrite via temp+rename.
8. **Rollback on partial failure** — `BROADCAST` and `DEPLOY --all` are not transactions across targets. Each target succeeds or fails independently. A per-target failure logs an entry and the run continues; the run's exit code is non-zero if any target failed. The rendering atom MUST NOT leave a half-written file behind — temp+rename guarantees this.
9. **Append-block markers** — every append-style write is wrapped in `<!-- instinct:<slug>:<target> START -->` … `<!-- instinct:<slug>:<target> END -->` markers. Re-runs replace the block by marker; UNDEPLOY removes by marker. Two concurrent runs writing the same `<slug>:<target>` block are serialized by the per-shared-file lock from rule 3.

---

## Config (`.instinct.yml`)

Both skills share the same config. The `emit:` section controls this skill. Full schema → [`../session-to-instinct/references/config-schema.md`](../session-to-instinct/references/config-schema.md).

```yaml
version: 1
preset: standard

emit:
  # Provider gate — disable a whole vendor in one switch
  providers:
    claude:   { enabled: true }
    cursor:   { enabled: false }
    codex:    { enabled: false }
    gemini:   { enabled: false }
    copilot:  { enabled: false }
    any:      { enabled: true }      # vendor-agnostic targets (skill-constraint, system-prompt)

  routes:
    rule:           { enabled: true,  targets: [claude-path],      default_atom: invariant-guard }
    skill:          { enabled: true,  targets: [skill-constraint], default_atom: kata }
    doc:            { enabled: false, targets: [agents-md] }
    security-rule:  { enabled: false, targets: [claude-global] }

  targets:
    claude-path:       { enabled: true, default_atom: auto }
    skill-constraint:  { enabled: true, default_atom: invariant-guard }
    cursor-mdc:        { enabled: false }

  broadcast_targets: [claude-path, skill-constraint]
  allow_route_override: false
  allow_overwrite: false
```

`default_atom: auto` means use the instinct's own `best_preset`.

Priority: **CLI flags → `.instinct.local.yml` → `.instinct.yml` → defaults**

---

## Commands

| Command | Description |
|---|---|
| `EMIT [--slug X] [--target Y] [--atom Z]` | EXTRACT → PICK → BUILD (writes inside this skill only) |
| `EMIT --dry-run` | Preview variant without writing |
| `BROADCAST [--slug X] [--targets ...]` | EMIT to all listed targets |
| `DEPLOY --slug X --target Y` | Place variant at the external project path |
| `DEPLOY --all` | Deploy every variant in `instincts/` to its enabled target |
| `UNDEPLOY --slug X --target Y` | Remove the external placement; keep `instincts/<slug>/` |
| `LIST` | List all instincts in `instincts/` and their build/deploy state |
| `MATRIX` | Coverage table: instincts × targets × (built / deployed) |
| `GAP --target Y` | Find instincts not yet built or built-but-not-deployed |
| `DIFF --slug X --targets A,B` | Compare an instinct's variant across two targets |
| `SYNC [--slug X]` | Re-BUILD variants whose source instinct was edited since last build |

---

## Output

```
instinct-to-harness — EMIT complete
slug: git-sequential-commits  (polarity: never)
target: claude-path  |  atom: invariant-guard
variant written: instincts/git-sequential-commits/variants/claude-path.md
NOT yet deployed — run DEPLOY --slug git-sequential-commits --target claude-path
```

```
MATRIX
slug                          | claude-path        | cursor-mdc       | agents-md          | skill-constraint
------------------------------+--------------------+------------------+--------------------+-----------------
git-sequential-commits        | built+deployed ✅  | built  -         | built+deployed ✅  | -
macos-bash-gotchas            | built+deployed ✅  | built+deployed ✅| -                  | -
chrome-mcp-localhost          | built  -           | -                | -                  | -
```

---

## Red flags

**Always:**
- `--dry-run` before the first EMIT to a production AGENTS.md or sibling SKILL.md
- Check `MATRIX` before `BROADCAST` — avoid duplicate inserts in append targets
- Verify the target file exists before `skill-constraint` deploy (this skill never creates SKILL.md)
- Respect `path_scope`: emit as path-scoped only when the instinct has one; global otherwise

**Never:**
- Hand-edit `instincts/<slug>/variants/*` and expect the edits to survive — BUILD regenerates derived variants
- Write a `system-prompt` fragment longer than 50 tokens
- Skip `emissions.jsonl` / `deploys.jsonl` — `MATRIX`, `GAP`, `SYNC` rely on these
- Modify instinct files in `session-to-instinct/instincts/` outside the `harness:` block — this skill may *only* update the `harness:` frontmatter block (built / deployed / timestamps); body and all other fields are read-only. Use `session-to-instinct REVIEW` to change `review_status`, edit body, etc.

---

## Requirements

- Reads instincts from `../session-to-instinct/instincts/*.md`; may update only the `harness:` frontmatter block (built / deployed / last_*_at). All other fields and the body are read-only `MUST`
- Each rendering atom under `atoms/` is documented in its own markdown file `MUST`
- Each harness target under `targets/` is documented in its own markdown file `MUST`
- Each preset under `presets/` is documented in its own markdown file `MUST`
- BUILD writes only inside `instincts/<slug>/` and never touches external harness files `MUST`
- DEPLOY is the only step that places files at external project paths `MUST`
- `emissions.jsonl` and `deploys.jsonl` are appended after each successful BUILD / DEPLOY `MUST`
- Never overwrites an external harness target unless `--force` or an explicit sync mode is passed `MUST`
- Auto-resolves rendering atom from `best_preset` when `--atom` is not specified `SHOULD`
- Supports `--dry-run` for both BUILD and DEPLOY flows `SHOULD`
- `BROADCAST` and `DEPLOY --all` process each target independently; one failure does not abort others `SHOULD`
- `MATRIX` shows build state and deploy state separately `MAY`
