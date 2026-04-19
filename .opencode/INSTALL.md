# Installing artie-dev-skills for OpenCode

Skills install via symlink into OpenCode's skills directory.

## Prerequisites

- Git

## Installation

1. **Clone the repository:**

   ```bash
   git clone https://github.com/artieax/artie-dev-skills.git ~/.opencode/artie-dev-skills
   ```

2. **Symlink skills:**

   **macOS / Linux:**
   ```bash
   mkdir -p ~/.opencode/skills
   ln -s ~/.opencode/artie-dev-skills/skills ~/.opencode/skills/artie-dev-skills
   ```

   **Windows (PowerShell):**
   ```powershell
   New-Item -ItemType Directory -Force -Path "$env:USERPROFILE\.opencode\skills"
   cmd /c mklink /J "$env:USERPROFILE\.opencode\skills\artie-dev-skills" "$env:USERPROFILE\.opencode\artie-dev-skills\skills"
   ```

3. **Restart OpenCode** to pick up the skills.

## Updating

```bash
cd ~/.opencode/artie-dev-skills && git pull
```
