---
name: scaffold-user
role: user
used_by: scripts/optimize.py (generate_scaffold)
description: User prompt for the SCAFFOLD turn. Receives optional few-shot demos plus the new skill's description and requirements.
vars:
  - few_shot_block: rendered few-shot examples (or empty string)
  - description: one-line description of the skill being scaffolded
  - requirements: bulleted constraints
---

{{few_shot_block}}Description: {{description}}
Requirements: {{requirements}}
Generate the SKILL.md:
