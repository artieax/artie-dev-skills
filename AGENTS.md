## Marketplace

This repo hosts `artie-marketplace` — a shared marketplace intended to span multiple artie repos. It currently ships one plugin, `artie-dev-skills`.

Install pattern (future plugins register under the same marketplace):

```
/plugin marketplace add artieax/artie-dev-skills
/plugin install <plugin-name>@artie-marketplace
```

## Skills in `artie-dev-skills`

| Skill | Purpose |
|-------|---------|
| `pluginize` | Turn a skills repo into a multi-platform plugin |
| `bommit` | Commit the current diff with a clean conventional message |

See `skills/*` for details.
