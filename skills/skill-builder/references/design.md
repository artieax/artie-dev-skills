# design — Phase 1 (CREATE)

Answer these before any `SKILL.md` body exists. If you cannot answer all sections, it is too early to scaffold.

---

## Pre-check

```bash
ls skills/
```

**Local duplicate check:** confirm no existing skill already owns the same trigger.

---

## Marketplace scan

After the local check, search the marketplace for similar skills:

```bash
# list installed marketplace plugins and their skills
/plugin marketplace search <keyword>
# or via gh extension if artie-marketplace is available
gh extension exec artie-marketplace list | grep -i "<keyword>"
```

For each match, decide:

| Match type | Decision |
|---|---|
| Identical trigger and scope | Extend the existing skill — do not create a new one |
| Overlapping trigger, different scope | Build with a clear `Do not trigger` boundary; add a reciprocal note to the matched skill |
| Similar purpose, reusable reference data | Compose — copy or symlink their reference files into yours |
| Similar purpose, incompatible design | Build fresh; document the boundary in both SKILL.md files |

If no marketplace match exists, proceed to the three design questions.

---

## The three design questions

1. **What is the trigger phrase?** — Write 1–3 natural-language phrases the user would say.
2. **What is the output?** — File / commit / report / message — be concrete.
3. **Where is the boundary with adjacent skills?** — One sentence separating this skill's scope from its neighbors.

---

## Persistence tier decision

| Data character | Tier | Location |
|---|---|---|
| Config, reports, human-readable docs | A (markdown) | `references/` |
| Logs, append-heavy structured data | B (JSONL) | `references/*.jsonl` |

Default to Tier A.
