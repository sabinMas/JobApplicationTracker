# keystroke-agents

A Keystroke project — agents, workflows, actions, and triggers live in `src/`.

Lint, typecheck, and test configs live in the CLI; this project only adds the packages they need.

```bash
pnpm install
keystroke auth login                       # once
keystroke projects link --project <slug>    # keystroke projects list
keystroke deploy                           # lint + typecheck + build + ship dist/ (no pre-steps needed)
```

Iterate locally with `keystroke dev`. See **`AGENTS.md`** for the full authoring guide, commands, and project layout.
