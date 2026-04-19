# artie-dev-skills

## Overview

> A minimalist home for general-purpose agent skills — plugin-ready, composable, delightful.

This is the **`artie-dev-skills`** plugin — dev-focused agent skills, distributed via the [`artie-marketplace`](https://github.com/artieax/artie-marketplace) hub. Other categories (e.g. tax, design) will ship as separate plugins registered under the same marketplace.

```
artie-dev-skills  (plugin in the artie-marketplace)
├── .claude-plugin/plugin.json    → artie-dev-skills manifest
├── .cursor-plugin/plugin.json
├── .codex/INSTALL.md
├── .opencode/INSTALL.md
├── gemini-extension.json
├── AGENTS.md             → shared agent instructions
├── CLAUDE.md             → mirrors AGENTS.md
├── GEMINI.md             → mirrors AGENTS.md
├── README.md             ← you are here
└── skills/
    ├── pluginize/
    └── bommit/
```

---

## Install

### Claude Code

```bash
/plugin marketplace add artieax/artie-marketplace
/plugin install artie-dev-skills@artie-marketplace
```

The marketplace lives at [`artieax/artie-marketplace`](https://github.com/artieax/artie-marketplace); other artie plugins register there too — only the plugin name after `/plugin install` changes.

### Cursor

Install via Cursor's plugin surface pointed at this repo — the `.cursor-plugin/plugin.json` is read automatically.

### Codex CLI

See [`.codex/INSTALL.md`](./.codex/INSTALL.md) — clone + symlink into `~/.agents/skills/`.

### Gemini

The repo ships `gemini-extension.json` + `GEMINI.md`. Point your Gemini setup at this repo as an extension.

### OpenCode

See [`.opencode/INSTALL.md`](./.opencode/INSTALL.md).

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
