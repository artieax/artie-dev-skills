# artie-dev-skills

## Overview

> A minimalist home for general-purpose agent skills — plugin-ready, composable, delightful.

This repo hosts the **`artie-marketplace`** — a shared marketplace that may span multiple artie repos. It currently ships one plugin, `artie-dev-skills`, and is named generically so future plugins (from this repo or others) can register under the same marketplace.

```
artie-dev-skills  (plugin in the artie-marketplace)
├── .claude-plugin/
│   ├── plugin.json          → artie-dev-skills manifest
│   └── marketplace.json     → artie-marketplace descriptor
├── .cursor-plugin/plugin.json
├── .codex/INSTALL.md
├── .opencode/INSTALL.md
├── gemini-extension.json
├── AGENTS.md             → shared agent instructions
├── CLAUDE.md             → mirrors AGENTS.md
├── GEMINI.md             → mirrors AGENTS.md
├── README.md             ← you are here
└── skills/
    └── pluginize/
```

---

## Install

### Claude Code

```bash
/plugin marketplace add artieax/artie-dev-skills
/plugin install artie-dev-skills@artie-marketplace
```

Future artie plugins will register under the same `artie-marketplace` — only the plugin name after `/plugin install` changes.

### Cursor

Install via Cursor's plugin surface pointed at this repo — the `.cursor-plugin/plugin.json` is read automatically.

### Codex CLI

See [`.codex/INSTALL.md`](./.codex/INSTALL.md) — clone + symlink into `~/.agents/skills/`.

### Gemini

The repo ships `gemini-extension.json` + `GEMINI.md`. Point your Gemini setup at this repo as an extension.

### OpenCode

See [`.opencode/INSTALL.md`](./.opencode/INSTALL.md).

---

## Plugins in this marketplace

| Plugin | Skills | Focus |
|--------|--------|-------|
| **artie-dev-skills** | `pluginize`, `bommit` | Dev workflows — turning work into distributable plugins |

More plugins may split out from this repo later.

---

## Skills in `artie-dev-skills`

| Skill | Purpose |
|-------|---------|
| **pluginize** | Turn a skills repo into a multi-platform plugin |
| **bommit** | Commit the current diff with a clean conventional message |

> More skills coming soon.

---

## License

© 2026 artie — rights reserved, but **free to use**.

Use it commercially or personally — credit appreciated.
