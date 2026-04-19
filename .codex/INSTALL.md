# Installing artie-dev-skills for Codex

Skills install via symlink — no plugin runtime needed.

## Prerequisites

- Git

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/artieax/artie-dev-skills.git ~/.codex/artie-dev-skills
   ```

2. **Create the skills symlink:**

   **macOS / Linux:**
   ```bash
   mkdir -p ~/.agents/skills
   ln -s ~/.codex/artie-dev-skills/skills ~/.agents/skills/artie-dev-skills
   ```

   **Windows (PowerShell):**
   ```powershell
   New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.agents\skills"
   cmd /c mklink /J "$env:USERPROFILE\.agents\skills\artie-dev-skills" "$env:USERPROFILE\.codex\artie-dev-skills\skills"
   ```

3. **Restart Codex** (quit and relaunch the CLI) to discover the skills.

## Updating

```bash
cd ~/.codex/artie-dev-skills && git pull
```
