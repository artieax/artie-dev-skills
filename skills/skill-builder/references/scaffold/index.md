# scaffold — atom-first index

Scaffolding a skill is **picking atoms and combining them**. Every preset (`minimal`, `standard`, `scripts`, `split`) is just a named combination of atoms. Every archetype (`versioned`, `comparator`, `sandbox`) is the same idea with a domain-specific layer.

Start here:

1. **Pick atoms** from the catalog below
2. **Combine them** — either match a preset, or assemble freely
3. **Generate the draft** via `atomic-builder.md` (uses exemplar atoms when available)
4. **Run the `quick` eval** before treating the draft as done

→ Pipeline details: [`atomic-builder.md`](atomic-builder.md) · How BUILD runs on your host (modes A/B/C): [`execution-modes.md`](execution-modes.md)

---

## Atom catalog

### Content atoms (sections inside `SKILL.md`)

| Atom | Purpose | Required? |
|---|---|---|
| [`frontmatter`](atoms/frontmatter.md) | YAML header (name / description / author) | always |
| [`trigger`](atoms/trigger.md) | `When to use` + `Do not trigger` | always |
| [`workflow`](atoms/workflow.md) | Ordered steps the skill runs | always |
| [`redflag`](atoms/redflag.md) | `Always` / `Never` lists | always |
| [`output`](atoms/output.md) | Concrete deliverable shape | always |
| [`requirements`](atoms/requirements.md) | Checklist with RFC 2119 (`MUST` / `SHOULD` / `MAY`) priorities | always |

### Structural atoms (directories alongside `SKILL.md`)

| Atom | Purpose | When to add |
|---|---|---|
| [`references-dir`](atoms/references-dir.md) | `references/` for delegated docs + `eval-log.jsonl` | workflow > 40 lines, or eval tracking needed |
| [`scripts-dir`](atoms/scripts-dir.md) | `scripts/` for encapsulated shell/file ops | > 3 chained commands or reusable logic |
| [`stdout-delegate`](atoms/stdout-delegate.md) | Scripts emit `__LLM_DELEGATE__:` lines; host executes LLM calls — no API key or `claude` CLI needed inside the script | scripts need selective LLM help but can't import a SDK |
| [`prompts-dir`](atoms/prompts-dir.md) | `prompts/` for reusable LLM prompts loaded by scripts | scripts make 2+ LLM calls, or prompts are large enough to obscure call-site code |
| [`atomic-builder`](atoms/atomic-builder.md) | EXTRACT → PICK → BUILD pipeline owned by this skill | skill's core job is generating artifacts from a catalog of parts |
| [`orchestrator`](atoms/orchestrator.md) | SKILL.md that calls top-level child skills in fixed order | multi-phase pipeline with independent triggers |
| [`match-router`](atoms/match-router.md) | Dispatch that auto-picks a sub-skill when intent is clear, asks when ambiguous | orchestrator with 2+ candidates where the right one depends on intent |
| [`child-skill`](atoms/child-skill.md) | Independent top-level skill called by an orchestrator | always paired with `orchestrator` or `match-router` |
| [`list-registry`](atoms/list-registry.md) | `references/<domain>-list.md` — curated candidate list read by comparator/orchestrator, auto-expanded via skill-auto-tuner | skill compares a domain with a growing candidate set |
| [`versioned-projects`](atoms/versioned-projects.md) | `projects/<name>/v<N>/` for iterated outputs | outputs evolve over time, rollback needed |
| [`sandbox-dir`](atoms/sandbox-dir.md) | `sandbox/{fixtures,runs}/` for self-validation | want to verify the skill before merging |
| [`apps-dir`](atoms/apps-dir.md) | `apps/<app-name>/` for standalone GUI/CLI/web apps launched by the skill | skill needs a visual UI, a compiled binary, or an app end-users run independently |

---

## Presets — named atom combinations

Every preset is `frontmatter + trigger + workflow + redflag + output + requirements` (the six required content atoms) plus the structural atoms listed below.

| Preset | Atoms added on top of the six required | Use when |
|---|---|---|
| [`minimal`](minimal.md) | (none) | ≤ 3 steps, no docs needed |
| [`standard`](standard.md) | `+ references-dir` | needs supplementary docs or eval tracking |
| [`scripts`](scripts.md) | `+ references-dir + scripts-dir` | shell or file operations |
| [`split`](split.md) | `+ orchestrator` + N × `child-skill` | 2+ independent triggers |

If none of these match, build a custom combination — that's what the atom catalog is for.

---

## Archetypes — domain-specific combinations

Archetypes layer additional atoms on top of a preset. Full templates → [`../archetypes.md`](../archetypes.md).

| Archetype | Combination | Use when |
|---|---|---|
| `versioned` | `standard` + `versioned-projects` | iterative outputs, rollback needed |
| `comparator` | `orchestrator` + 4 × `child-skill` (`-collect` / `-compare` / `-recommend` / `-report`) | comparing libraries / approaches |
| `sandbox` | `standard` + `sandbox-dir` | want to validate the skill before shipping |

---

## Naming conventions

| Target | Convention | Example |
|---|---|---|
| Skill name | `kebab-case`, no leading verb | `skill-builder`, `bommit` |
| Branch | `feature/<name>` / `iter/<name>-v<N>` / `refactor/<name>` | `feature/skill-builder` |
| Child skill | `<orchestrator>-<phase>` | `skill-builder-evals` |
| Reference files | `<topic>.md` lowercase | `scaffold.md`, `evals.md` |

---

## SKILL.md writing tips

- **`description` frontmatter is one sentence.** It's used in search and listings — start with a verb.
- **`When to use` lists natural-language phrases.** Write what the user would actually type.
- **Always write `Do not trigger`.** Explicit boundaries prevent trigger collisions with adjacent skills.
- **`Output` must be concrete.** Not "creates a file" but "generates `skills/<name>/SKILL.md` and appends a row to the AGENTS.md skill table."
- **`Red flags / Never` lists prohibitions only.** Add a one-line reason so the rule is understood, not just memorized.
