---
name: pluginize
description: 'Turn a skills repo into a multi-platform plugin (Claude Code, Codex, Cursor, Gemini, OpenCode). Use when the user wants their skills installable via `/plugin install`, loadable as a Gemini extension, or discoverable via symlink on Codex/OpenCode. Also audits existing plugins for missing manifests or adapters.'
author: @artieax
---

# pluginize

Plain skills repos (just `AGENTS.md` + `skills/`) only work as a raw `git clone`. Making them a real plugin unlocks `/plugin install` on Claude Code, native skill discovery on Codex, extension loading on Gemini, and plugin surfaces on Cursor/OpenCode. The conversion is mostly boilerplate per platform — this skill does it correctly, once, across all of them.

## When to use

- "Turn this skills repo into a plugin."
- "Add `.claude-plugin/` to this repo."
- "Create a marketplace.json."
- "Make this work on Cursor / Codex / Gemini too."
- "Add multi-platform support to my plugin."
- "Audit my plugin — what's missing?"
- "Why won't `/plugin install` find my repo?"

**Do not trigger** when the user is writing a single SKILL.md — route them to their `skill-creator`. This skill is about the *repo-level plugin envelope*, not individual skill authoring.

## Platform matrix

| Platform | Required files | Install pattern |
|----------|----------------|-----------------|
| Claude Code | `.claude-plugin/plugin.json` (+ `marketplace.json` for `marketplace add`) | `/plugin marketplace add <owner/repo>` → `/plugin install <plugin>@<marketplace>` |
| Cursor | `.cursor-plugin/plugin.json` | Cursor plugin surface or marketplace search |
| Codex | none — just `skills/` | symlink `skills/` into `~/.agents/skills/<plugin>` |
| Gemini | `gemini-extension.json` + `GEMINI.md` | load as Gemini extension |
| OpenCode | none required (or `.opencode/plugins/*.js` for JS bits) | symlink `skills/` into `~/.opencode/skills/<plugin>` |

For every platform beyond Claude Code, provide a short `INSTALL.md` so users don't have to guess the symlink path.

## Required layout

Minimum Claude Code plugin:

```
<repo>/
├── .claude-plugin/
│   └── plugin.json          ← REQUIRED
└── skills/<name>/SKILL.md   ← at least one
```

Marketplace-installable Claude Code plugin:

```
<repo>/
├── .claude-plugin/
│   ├── plugin.json          ← REQUIRED
│   └── marketplace.json     ← REQUIRED for `marketplace add`
```

Full multi-platform layout:

```
<repo>/
├── .claude-plugin/
│   ├── plugin.json
│   └── marketplace.json
├── .cursor-plugin/plugin.json
├── .codex/INSTALL.md
├── .opencode/INSTALL.md          (+ plugins/*.js if JS runtime needed)
├── gemini-extension.json
├── AGENTS.md
├── CLAUDE.md                     (mirrors AGENTS.md)
├── GEMINI.md                     (mirrors AGENTS.md)
├── README.md
└── skills/<name>/SKILL.md
```

Optional add-ons (only if actually referenced):

```
├── hooks/
│   ├── hooks.json            ← hook registration
│   └── <hook-script>         ← use ${CLAUDE_PLUGIN_ROOT} for paths
├── agents/<agent>.md         ← subagent definitions
├── commands/<cmd>.md         ← slash commands
├── LICENSE
└── package.json              ← only for JS runtime bundles
```

## Workflow

### 1. Detect current state

From repo root:

- `.claude-plugin/plugin.json` exists? → **already a Claude Code plugin** → go to **Audit flow**.
- `AGENTS.md` or `skills/` exists? → **plain skills repo** → go to **Convert flow**.
- Neither? → not a skills repo. Ask the user what they want to pluginize.

### 2. Convert flow

**Ask which platforms to target.** Default: all five (Claude Code, Cursor, Codex, Gemini, OpenCode). If the user says "just Claude Code for now," only do step 2a.

**Gather metadata** (one question per missing field):

| Field | Source | Required |
|-------|--------|----------|
| `name` | usually the repo name in kebab-case | ✅ |
| `description` | 1-line summary | ✅ |
| `version` | start at `0.1.0` unless they have one | ✅ |
| `author.name` / `author.email` | git log / ask | ✅ |
| `homepage` / `repository` | GitHub URL | recommended |
| `license` | check `LICENSE`; **omit if the user doesn't want one specified** | optional |
| `keywords` | derived from skill names | optional |

#### 2a. Claude Code — `.claude-plugin/plugin.json`

```json
{
  "name": "<plugin-name>",
  "description": "<description>",
  "version": "0.1.0",
  "author": { "name": "<name>", "email": "<email>" },
  "homepage": "https://github.com/<owner>/<repo>",
  "repository": "https://github.com/<owner>/<repo>",
  "keywords": ["skills", "claude-code"]
}
```

Ask: publish as a marketplace? If yes, write `.claude-plugin/marketplace.json`:

```json
{
  "name": "<marketplace-name>",
  "description": "<marketplace description>",
  "owner": { "name": "<name>", "email": "<email>" },
  "plugins": [
    {
      "name": "<plugin-name — must match plugin.json>",
      "description": "<description>",
      "version": "0.1.0",
      "source": "./",
      "author": { "name": "<name>", "email": "<email>" }
    }
  ]
}
```

Notes:
- `source: "./"` — plugin is the repo root. For multi-plugin marketplaces use subdirectory paths.
- Marketplace `name` and plugin `name` can differ (useful when one marketplace hosts multiple plugins).

#### 2b. Cursor — `.cursor-plugin/plugin.json`

```json
{
  "name": "<plugin-name>",
  "displayName": "<Human Readable Name>",
  "description": "<description>",
  "version": "0.1.0",
  "author": { "name": "<name>", "email": "<email>" },
  "homepage": "https://github.com/<owner>/<repo>",
  "repository": "https://github.com/<owner>/<repo>",
  "keywords": ["skills"],
  "skills": "./skills/"
}
```

Only add `"agents": "./agents/"`, `"commands": "./commands/"`, or `"hooks": "./hooks/hooks-cursor.json"` if those directories/files actually exist.

#### 2c. Codex — `.codex/INSTALL.md`

Codex uses native skill discovery — no manifest. Write an INSTALL.md with:

```markdown
# Installing <plugin> for Codex

1. Clone:
   git clone https://github.com/<owner>/<repo>.git ~/.codex/<repo>
2. Symlink (macOS/Linux):
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/<repo>/skills ~/.agents/skills/<plugin-name>
   Windows (PowerShell):
   cmd /c mklink /J "$env:USERPROFILE\.agents\skills\<plugin-name>" "$env:USERPROFILE\.codex\<repo>\skills"
3. Restart Codex.
```

#### 2d. Gemini — `gemini-extension.json` + `GEMINI.md`

```json
{
  "name": "<plugin-name>",
  "description": "<description>",
  "version": "0.1.0",
  "contextFileName": "GEMINI.md"
}
```

Create `GEMINI.md` — mirror `AGENTS.md`. On Unix, symlink. On Windows without Developer Mode, duplicate (and remind the user to re-sync on edits).

#### 2e. OpenCode — `.opencode/INSTALL.md`

Write an INSTALL.md with the symlink pattern into `~/.opencode/skills/<plugin-name>`. Add `.opencode/plugins/<plugin>.js` **only** if the plugin actually ships JS runtime code.

#### 2f. Keep context files in sync

`AGENTS.md`, `CLAUDE.md`, `GEMINI.md` should carry the same content. On Unix, symlink `CLAUDE.md` and `GEMINI.md` → `AGENTS.md`. On Windows, copy.

### 3. Audit flow (already a plugin)

For each platform the user targets, check what exists vs what should. Produce a short checklist:

- ✅ / ⚠️ `.claude-plugin/plugin.json` — missing fields (`name`, `version`, `author`) flagged.
- ✅ / ⚠️ `.claude-plugin/marketplace.json` — name matches plugin.json?
- ✅ / ⚠️ `.cursor-plugin/plugin.json` — references non-existent dirs?
- ✅ / ⚠️ `gemini-extension.json` — `contextFileName` points to an existing file?
- ✅ / ⚠️ `CLAUDE.md` / `GEMINI.md` in sync with `AGENTS.md`?
- ✅ / ⚠️ Hooks declared but `${CLAUDE_PLUGIN_ROOT}` not used?

Show the checklist before editing. Fix only what the user approves.

### 4. Validate

- All JSON files parse.
- `plugin.json.name` == `marketplace.json.plugins[*].name` (when both exist).
- `plugin.json.name` == `.cursor-plugin/plugin.json.name` == `gemini-extension.json.name` (consistent across platforms).
- At least one `skills/*/SKILL.md` OR `agents/*.md` OR `commands/*.md`.
- Each `SKILL.md` has valid YAML frontmatter with `name` and `description`.
- Hook commands use `${CLAUDE_PLUGIN_ROOT}` when referencing in-plugin files.

### 5. Smoke test

Claude Code (from local path):

```bash
/plugin marketplace add <path-to-repo>
/plugin install <plugin-name>@<marketplace-name>
/plugin list
```

Codex / OpenCode: follow the generated INSTALL.md, then restart and ask the agent "what skills do you have?"

Gemini: load as extension, confirm `GEMINI.md` content surfaces in context.

## Common mistakes

- **Hardcoding absolute paths in hooks** — always use `${CLAUDE_PLUGIN_ROOT}`.
- **Mismatched names** between `plugin.json` / `marketplace.json` / `cursor-plugin/plugin.json` / `gemini-extension.json` — installers silently fail.
- **Referencing non-existent directories** in Cursor's `plugin.json` (`agents`, `commands`, `hooks`) — drop them until they exist.
- **Adding `package.json` when not needed** — only for plugins that actually ship JS runtime (OpenCode JS plugins).
- **Forgetting to commit `.claude-plugin/` or `.cursor-plugin/`** — remote-based installs will 404.
- **Empty `agents/` or `commands/` directories** — create only when populated.
- **Stale `CLAUDE.md` / `GEMINI.md`** — if copied not symlinked, diverge quickly. Note the sync requirement for the user.

## Output

After running this skill, the user has:

1. A valid `.claude-plugin/plugin.json` (+ optional `marketplace.json`).
2. Platform adapters for every target they picked (Cursor / Codex / Gemini / OpenCode).
3. `AGENTS.md` / `CLAUDE.md` / `GEMINI.md` in sync.
4. Any scaffolding for hooks / agents / commands that their skills actually reference.
5. A short validation report + smoke-test commands per platform.

No other files change unless the audit explicitly flagged them.
