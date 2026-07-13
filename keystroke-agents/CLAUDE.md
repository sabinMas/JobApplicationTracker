# keystroke

This codebase is a Keystroke project. Keystroke is a code-first AI automation platform: you build AI agents, workflows, triggers, and actions in TypeScript under `src/`, deploy them to a managed cloud runtime, then run and inspect what's deployed.

You are the user's AI automation engineer — the coding agent that builds and maintains this project. Read `src/` first (existing agents, workflows, actions, triggers). This guide is a map, not the manual: the docs are the source of truth (see [Documentation](#documentation)). Before building or changing any primitive, read its docs page first. The `keystroke` CLI drives everything else: deploy, run, inspect, credentials, integrations, triggers.

## Match the user's level

Users range from staff engineers to Zapier-caliber automation builders. You are the medium through which they build.

- **Mirror their voice.** Only get as technical as the user does.
- **Narrate in outcomes, not plumbing.** "I'll set this to run every morning and message you a summary", not "deploying the cron trigger to the runtime." Don't surface internals (build artifacts, event logs, correlation IDs, filtered deploys) unless the user must decide about one.
- **Don't hand them the work.** They build *through* you — don't tell them to run commands, edit files, or paste code unless they've shown they want to. Do it yourself and report the result.
- **Simplify the talk, never the work.** Follow every invariant in this guide regardless of how the user communicates.

## Clarify as you build

Act as the user's automation engineer, not just an implementer. Before and while building, inspect the existing code, integration catalog, and connected credentials. Resolve what you can yourself; ask when a choice changes the outcome, access, or architecture.

- Clarify the trigger, inputs, destination, account, and approval or failure behavior when they are unclear.
- When several integrations, credentials, or designs fit, give the concrete options, recommend one briefly, and ask the user to choose. Never expose secret values.
- Recommend a workflow for a known, reliable path and an agent when runtime judgment, tool choice, or conversation is required.
- Batch related questions into one short message. Don't conduct an open-ended interview or ask what code, docs, or CLI inspection can answer.
- Use sensible, reversible defaults and state assumptions. Confirm before consequential side effects or ambiguous access.

## Local codebase vs platform project

| | What it is | Lives |
| --- | --- | --- |
| **Local codebase** | This directory — `keystroke.config.ts` + `src/`. Source of truth. | Your machine / Git |
| **Platform project** | Org-owned cloud runtime (its own server, URL, credentials, run history). Inactive until first deploy. | Keystroke cloud |

Most platform commands read `organization` / `project` from `keystroke.config.ts`; pass `--organization <slug>` / `--project <slug>` only to override or when config is missing. The usual bootstrap is `keystroke projects link --project <slug>` (writes both after you pass `--organization` on first link).

`keystroke deploy` builds `src/` into `dist/`, runs lint and typecheck, uploads the artifact, and promotes it as the project's single live runtime. A deploy replaces what's running — no separate dev and prod within one project.

Once deployed, your user works in the **web platform** — a shared workspace with an interactive workflow canvas, agent chat, run/trace inspection, credentials, and teammates. Most users spend far more time there than in code, so frame what you build around what they'll see and do there, not CLI plumbing.

### Project layout

Everything under `src/` is discovered by convention.

```
my-app/
  keystroke.config.ts    # optional project + organization slugs (set via `keystroke projects link`)
  tsconfig.json          # standalone strict config (committed) — includes noUncheckedIndexedAccess
  package.json           # dev/build/lint/typecheck/test scripts
  src/
    agents/              # LLM agents
    actions/             # reusable leaf units of work
    workflows/           # multi-step automations
    triggers/            # schedules, webhooks, app events
    skills/              # runtime playbooks for agents
    files/               # context files attached to agents
  AGENTS.md              # this guide
```

Each primitive imports from `@keystrokehq/keystroke/<piece>` (`/agent`, `/action`, `/workflow`, `/trigger`, `/sandbox`). Integrations are `@keystrokehq/<slug>` packages.

When you add any `@keystrokehq/*` package, pin it to `"latest"` in `package.json` — e.g. `"@keystrokehq/gmail": "latest"`, never exact semver or caret ranges.

### Dev tooling

Lint, typecheck, and test run through the globally installed CLI (`npm i -g @keystrokehq/cli`). Projects depend on `@keystrokehq/keystroke` and `zod`, plus `typescript`, `vitest`, and `@types/node` as devDependencies (for the IDE and local runs). Two things are **not** configurable per-project:

- **Lint** — oxlint and its config are bundled in the CLI; a project `.oxlintrc.json` is ignored. `typescript/no-explicit-any` is an **error** and the same lint runs at deploy. At external-JSON boundaries, parse into a Zod schema (or type as `unknown` and narrow) instead of `any`.
- **Typecheck** — the committed `tsconfig.json` is strict, including `noUncheckedIndexedAccess`: indexing (`arr[0]`, `record[key]`, regex `match[1]`) yields `T | undefined`, so guard before use.

**Deploy is the gate.** `keystroke deploy` runs lint and typecheck before it builds and ships — don't run them separately first. Attempt deploy, fix what it reports, redeploy. Use the commands below only for a faster local loop (especially `keystroke test`).

**Keep `@keystrokehq/*` on latest.** The CLI auto-updates itself (global install). `keystroke deploy` / `build` / `lint` / `typecheck` require installed project `@keystrokehq/*` packages to be on npm `latest` (CI skips the check). When they report outdated packages — or a build/deploy fails in a way that doesn't point at your code — run `keystroke update` and retry **before** debugging anything else. A registry minimum-release-age can hold a release back.

```bash
keystroke update            # bump @keystrokehq/* deps + CLI to latest
keystroke deploy            # lint + typecheck + build + ship dist/ — start here
keystroke test              # optional local loop (unit + integration)
pnpm test                   # same — package.json scripts call the CLI
```

## The deploy-first loop

Build, ship, then run and inspect what's live. Deploy often.

1. **Auth once** — `keystroke auth login` (token stored and reused).
2. **Link the directory** — `keystroke --organization <slug> projects link --project <slug>` writes `project` and `organization` into `keystroke.config.ts` (or pass the flags on every command).
3. **Verify prerequisites** — run each integration action once for real with `keystroke apps execute` before wiring it in (see [Integrations & credentials](#integrations--credentials)).
4. **Edit** primitives under `src/`. Unit-test workflow logic in-process with `executeWorkflow` when a fast local check helps — deploying is still the shipping checkpoint.
5. **Deploy** — `keystroke deploy` (full) or `keystroke deploy --filter agents/support` (one module).
6. **Run** — `keystroke workflows run <slug> --input '{...}'` / `keystroke agents prompt <slug> --message "..."`.
7. **Inspect** — read the real run/trace before claiming done (see [Audit & debug](#audit--debug)).
8. Repeat.

`keystroke auth status` shows the current user + org memberships; `keystroke --organization <slug> projects list` shows an org's projects.

New project: `keystroke init my-app --yes`, link, then deploy. Join an existing cloud project: `keystroke pull --project <slug>` (with `--organization` or linked config).

## Choosing a primitive

| Build a… | When |
| --- | --- |
| **Agent** | The path isn't fixed — needs judgment, tool use, language, or multi-turn context. Or the user explicitly asks for an agent (AI data analyst in Slack, support agent, etc). |
| **Workflow** | You know the order of steps and want durability and predictability. |
| **Action** | A single reusable capability (an API call, a computation) used by workflows or agents. |
| **Trigger** | Something should start a workflow/agent automatically — schedule, webhook, or poll. |

Prefer a workflow (or a plain action / LLM step) unless the path genuinely varies at runtime — reach for an agent only when the user clearly asks for one or the work needs judgment, tool selection, or multi-turn context, not because it's easier to wire up. Primitives compose: workflows orchestrate actions and prompt agents; agents call actions, subagents, and workflows as tools.

## Building blocks

**Every primitive requires `slug`, `name`, and `description`** — agents, workflows, actions, and all trigger sources. Omitting `name` or `description` throws at module load, so it fails lint/typecheck-passing code at deploy. `name` is the human label in the platform; `description` is what the model sees when the primitive is a tool.

### Agent — `defineAgent`

Required: `slug`, `name`, `description`, `systemPrompt`, `model`. Everything else is optional. Full detail: `/learn/agents/build-agents`.

```ts
import { defineAgent } from "@keystrokehq/keystroke/agent";

export default defineAgent({
  slug: "support",
  name: "Support",
  description: "Answers customer support questions concisely.",
  systemPrompt: "You are a helpful support assistant. Answer concisely.",
  model: "anthropic/claude-sonnet-4.6",
});
```

- **Model** — exact catalog id in `vendor/model-id` format from https://keystroke.ai/models.md. Do **not** kebab-case the version (`anthropic/claude-sonnet-4.6` is valid; `...-4-6` fails at deploy).
- **Tools** — attach actions, subagents, workflows, and MCP tools directly in `tools: [...]`. Do **not** hand-roll a `defineTool` + `executeWorkflow()` wrapper. A subagent's tool name is its `slug` and takes a `message`.
- **Built in** — isolated workspace with file + `bash` tools: `/workspace/agent` persists across sessions (skills, `src/files/`, anything worth keeping); `/workspace/session` is per-session scratch. Plus session + persistent memory (`memory: false` to disable), `web_search`/`web_fetch` when configured, and self-scheduling tools.
- **Credentials** are declared on actions, not agents — the agent gets them by calling those actions as tools.
- **Sandbox** — default in-process bash covers most needs. For real CLIs/isolation: `sandbox: defineSandbox({ mode: "vm" })` (`mode` lives on `defineSandbox`, not as a top-level agent field).

### Workflow — `defineWorkflow`

Global `slug`, typed Zod `input`/`output`, a normal `async` `run`. Full detail: `/learn/workflows/build-workflows`.

```ts
import { defineWorkflow } from "@keystrokehq/keystroke/workflow";
import { z } from "zod";

export default defineWorkflow({
  slug: "signup-pipeline",
  name: "Signup Pipeline",
  description: "Research a new signup and post a brief to Slack.",
  input: z.object({ name: z.string(), email: z.string().email() }),
  output: z.object({ brief: z.string() }),
  async run(input) {
    const { brief } = await researchSignup.run(input);
    await postBrief.run({ text: brief });
    return { brief };
  },
});
```

| Step | Syntax |
| --- | --- |
| Action | `await action.run(input)` |
| Agent | `await agent.prompt({ message })` |
| One-shot LLM | `await promptLlm(prompt, { model, outputSchema? })` |
| Sub-workflow | `await otherWorkflow.run(input)` — never pass `ctx` |
| Durable sleep | `await ctx.sleep("1h")` |
| Durable wait | `await ctx.hook<T>()` |

`ctx` is the second `run` argument (`async run(input, ctx)`) — add it only when a step needs `ctx.sleep`/`ctx.hook`. Use `promptLlm(...)` (import from `@keystrokehq/keystroke/workflow`) for one-shot generation/classification; use `agent.prompt(...)` when the step needs tools, memory, or multi-turn reasoning.

**Durability** — completed steps replay on retry: keep side effects inside steps; make steps idempotent; keep control flow deterministic (no `Date.now()` / randomness). Step ids come from each call's position in `run`, so adding or removing an unrelated step never shifts the others. `ctx.sleep`/`ctx.hook` work from triggers/CLI/HTTP but not when a workflow is inline as an agent tool.

#### Canvas-legible, replayable workflows

The platform renders every workflow as an interactive **canvas** (a deploy-time parser reads your source) and lights up each step in run history. These habits keep steps rendering as real nodes and runs replayable. Full detail: `/learn/workflows/authoring-best-practices`.

**Principle** — put durable work in steps (`action.run`, `agent.prompt`, `promptLlm`, `ctx.sleep`, `ctx.hook`) and orchestrate them directly in `run` (or a same-file helper). Code between steps isn't checkpointed — it re-runs on every replay.

**Hard rules (break them and the build fails):**

1. **Never call a step outside a workflow file** — a `.run()` / `.prompt()` in `src/lib/**` or any imported module is invisible and uncorrelated. Cross-file helpers are encouraged for pure logic (formatting, date math, prompt building) — just don't hide steps in them.
2. **Never nest a step in another call's arguments** — hoist it first (`const p = await x.run({}); await y.run({ v: p.field })`).

**Soft rules (build warns; the step runs but renders as one opaque block):**

- Call steps **directly in `run()`**; a same-file helper is fine only if called once (reused helpers collapse).
- Iterate step work with **`for-of`**, not `.map` / `.filter` / `.forEach` / `.reduce`.
- Parallelize with a **literal** `Promise.all([a.run(), b.run()])`, not `Promise.all(arr.map(...))` / `race` / `allSettled` / `any`.
- List step **input fields explicitly** — no `...spread` or computed `[key]:` keys.
- Branch with **`if` / `else` / `switch`**, not step-bearing ternaries.
- Keep all side effects and non-determinism **inside steps**.
- Do HTTP/IO through an **action** (prebuilt integration *or* your own `defineAction`/`defineApp`), never a bare `fetch` in `run` — an inline `fetch` is neither a durable step nor a canvas node.

### Action — `defineAction`

Leaf unit — **never calls another action** (yours or an integration's). Enforced at runtime and by lint. Full detail: `/learn/actions/overview`.

```ts
import { defineAction } from "@keystrokehq/keystroke/action";
import { z } from "zod";

export const triage = defineAction({
  slug: "triage",
  name: "Triage",
  description: "Classify an inbound message by priority.",
  input: z.object({ message: z.string() }),
  output: z.object({ priority: z.enum(["low", "normal", "high", "urgent"]) }),
  run: async (input) => ({ priority: /urgent/i.test(input.message) ? "urgent" : "normal" }),
});
```

Compose in workflows. Attach integration actions directly as workflow steps or agent tools — never wrap in a custom action. An action *may* call an agent (`await agent.prompt(...)`).

### Trigger — source + `.attach()`

Exactly three sources: `defineCronSource`, `defineWebhookSource`, `definePollSource`. Default-export the attached result. Full detail: `/learn/triggers/overview` (then the per-source page).

```ts
import { defineWebhookSource } from "@keystrokehq/keystroke/trigger";
import { z } from "zod";
import workflow from "../workflows/signup-pipeline";

export default defineWebhookSource({
  slug: "signup",
  name: "Signup",
  description: "Fires when a new signup is posted.",
  endpoint: "signup",
  payload: z.object({ name: z.string(), email: z.string().email() }),
}).attach({ workflow });
```

| Source | Use when |
| --- | --- |
| **Schedule** (`defineCronSource`) | The workflow should run **every** tick, unconditionally — no filters exist on cron. Cron fields are wall-clock times in optional `timezone` (IANA, e.g. `America/New_York`); omit for UTC. Prefer `timezone` for local times like "9am". Optional static `payload` on the source (defaults to `{}`); without a `transform`, the payload must match the workflow `input`. |
| **Webhook** (`defineWebhookSource`) | Another system pushes events. Best option when available. |
| **Poll** (`definePollSource`) | Check an external system each tick and fire **only when the result passes `.filter(...)`**. A filtered tick creates no run and doesn't count toward execution limits — for "run only if X", a poll is correct and a cron is wrong. Same optional `timezone` as cron. |

Webhook match lives in the source `payload` schema; poll filters live on the source; `transform` lives on the workflow attachment. Agents use `.attach({ agent, prompt })` (not `transform`). Attachment id: `{sourceSlug}:{targetSlug}`.

**Ephemeral (self-scheduling) webhooks** — `set_trigger` with `kind: "webhook"` takes `endpoint` plus optional `payload` (shallow `{ "type": "invoice.paid" }` matcher). Omit `payload` to accept any body. `list_triggers` returns the compiled `payload` schema.

**Poll cursor state** — declare a `state` Zod schema and `run` receives `{ state, setState }` (`state` is `undefined` on the first tick). At-least-once delivery; see `/learn/triggers/polling#cursor-state`.

```ts
state: z.object({ lastCheckedAt: z.string() }),
run: async ({ state, setState }) => {
  const since = state?.lastCheckedAt ?? "1970-01-01T00:00:00.000Z";
  const messages = await fetchInbox.run({ after: since });
  setState({ lastCheckedAt: new Date().toISOString() });
  return messages;
},
```

**Deploy timing** — webhooks are passive and safe to deploy any time. A poll fires immediately on deploy; a cron waits for its next slot, then runs unattended. Until the workflow is verified, pause with `keystroke triggers disable <trigger-slug>` — the disabled state survives redeploys.

## Integrations & credentials

Keystroke has 1,000+ built-in integrations, and it's easy to build a custom one for any HTTP API or MCP server (including private/internal). **Research first, then build:** search the catalog thoroughly before assuming an app is missing; for anything custom or unfamiliar, web-fetch/search the system's real docs — `llms.txt`, OpenAPI/GraphQL specs, API reference — before writing code. Never guess endpoints or payloads.

Discover apps and actions with the CLI — the docs integration index is **not** reliable for discovery. One `<app> <tool>` shape flows through discovery → inspect → run; `apps actions get` / `apps actions list` print the next step (run, import, connect) after their output.

Think about testing as you build. Local tests don't link cloud credentials or the Keystroke client, so unit-test pure logic locally; for integrations, check needed apps/credentials and run each action once for real with `keystroke apps execute` (no deploy, no server) before wiring it into a workflow or agent — confirm the IDs, custom fields, and labels you're about to hard-code exist in the *connected* account. Schema inspection and dry-run flags prove nothing about the mutating path.

```bash
keystroke apps list                          # all registered apps
keystroke apps search "{query}"              # find an app + slug in the full catalog
keystroke apps actions list <app> --search <q>    # actions an app exposes
keystroke apps actions get <app> <tool>           # schema + how to run/import one action
keystroke apps execute <app> <tool> --input '{...}'   # run a connected catalog action (no server)
keystroke credentials list                  # what's already connected
keystroke connect <slug>                    # connect an app credential (opens web OAuth/api key flow for the user)
keystroke credentials create <key> --set apiKey=@env:MY_KEY   # static API key
```

`keystroke credentials list` is the **only** reliable connection check (`apps actions get` doesn't show status) — check it before connecting anything; the credential often already exists.

Credentials are for secrets. Non-secret config — spreadsheet IDs, channel names, base URLs — belongs in code as a literal constant or a workflow input. Keystroke projects don't use `.env`. Missing a built-in integration? After researching the system's docs/spec, let `keystroke apps create --mcp|--openapi|--graphql <url>` scaffold it from the source, or hand-write `defineCredential` + an action / `defineApp` / `defineMcp`. See `/learn/credentials/custom-integrations`.

## Skills & files

- **Skills** (`src/skills/<name>/SKILL.md`) — runtime playbooks that teach an agent *how* to do a task. Attach with `skills: ["<name>"]`.
- **Files** (`src/files/<set>/`) — static context an agent can access. Attach with `sandbox: defineSandbox({ files: true })` (set folder matches the agent `slug`).

Both materialize into the agent's `/workspace/agent/...` environment before each prompt.

## Deploy targets & scope

- **Organization / project** — org-scoped commands need `--organization <slug>` or `organization` in `keystroke.config.ts`. Project-scoped commands need `--project <slug>` or `project` in config. Missing either flag prints a hint to set the slug in `keystroke.config.ts` via `keystroke projects link --project <slug>`.
- **Target** — after link + first deploy, commands in this directory use the linked cloud project automatically.
- **Full vs filtered** — first deploy must be full. `keystroke deploy --filter agents/support` patches one module; filter keys are exact paths (`agents/support`, `workflows/morning-check`), no globs. Changing `keystroke.config.ts` or shared skills/files/integrations needs a full deploy.
- **WIP** — `// @keystroke ignore` skips a file everywhere; `// @keystroke ignore:deploy` keeps it local but out of deploys. A shipped module cannot import an ignored one.

## Audit & debug

Inspect deployed runs progressively — start lean, then request richer detail only when needed:

```bash
keystroke workflows runs list <workflow-slug>
keystroke workflows runs get <workflow-slug> <run-id> --summary
keystroke workflows runs get <workflow-slug> <run-id> --field output
keystroke workflows runs get <workflow-slug> <run-id> --include steps,trace

keystroke agents sessions list <agent-slug>
keystroke agents sessions get <agent-slug> <session-id> --summary
keystroke agents sessions get <agent-slug> <session-id> --field status
keystroke agents sessions get <agent-slug> <session-id> --include messages,trace

keystroke triggers list
keystroke triggers url <trigger-slug>                          # webhook URL (+ ?token= on platform)
keystroke triggers invoke <trigger-slug>                       # fire poll/cron/webhook on demand (platform only; --input is webhook-only)
keystroke triggers runs get <trigger-slug> <run-id> --workflow <workflow-slug> --include workflows,trace
keystroke triggers disable <trigger-slug>   # pause without redeploy; --workflow/--agent narrows to one attachment

keystroke history list --kind workflow --status failed
```

Workflows have durable **runs**; agents have durable **sessions** (use `agents sessions get`, not `agents runs get`).

Invoke/inspect commands print JSON to stdout (exit 0 on success, 1 on failure) — pipe to `jq` when you need arbitrary paths. Prefer `--summary` / `--field` for common inspection so you don't dig through nested envelopes. Lifecycle commands (`init`/`dev`/`deploy`) print human status.

## Before you claim you're done

- [ ] Deployed the change and read the real run output/trace — not just "it should work".
- [ ] Prompted agents / ran workflows with realistic input and verified behavior.
- [ ] Researched real APIs before mirroring them in custom integration actions — no guessed endpoints or payloads.
- [ ] Executed each mutating integration action once via `keystroke apps execute` before composing it — a passing dry-run flag doesn't count.
- [ ] Covered obvious edge cases (null field, empty array, a step that throws) with a simple test where warranted.
- [ ] Checked `keystroke credentials list` before connecting; connected any new apps with `keystroke connect`.
- [ ] Tested manually before deploying attached cron/polling triggers, or used `triggers disable` to pause until ready.

## Common gotchas

1. **Stale `@keystrokehq/*` versions** — the first suspect for any build or deploy failure; run `keystroke update` and retry before debugging (see [Dev tooling](#dev-tooling)).
2. **Action calling an action** — throws at runtime and fails lint. Compose in a workflow, or attach the integration action directly.
3. **Bad model id** — must be exact `vendor/model-id` from the catalog; don't kebab the version. Fails at deploy, not typecheck.
4. **LLM structured output: use `.nullish()`, not `.optional()`** — models emit `"field": null` for "not applicable", and Zod `.optional()` rejects `null` (the step fails). Use `.nullish()` (or `.nullable()`) for any optional field in an `outputSchema`.
5. **Structured output + tools is vendor-specific** — Anthropic Sonnet/Opus and OpenAI/Google/xAI are reliable; z-ai GLM uses a submit tool when tools are present; Alibaba Qwen is best-effort. See [structured output with tools](/learn/agents/build-agents#structured-output-with-tools).
6. **Silent fallbacks hide real failures** — for live config (Sheets, DBs, credentials), don't `catch` and quietly substitute fallback/empty data in production paths; a run that "completes" with empty inputs looks like success in the trace but is a silent failure. Throw when required config is missing or empty, and validate response shape, not just status.
7. **Side effects outside steps** — they re-run on every replay. Keep them inside `.run()` / `.prompt()`.
8. **Schedule input** — a cron trigger defaults to `{}`, or pass `payload` on `defineCronSource` (and optional `transform` on `.attach`) when the workflow needs input.
9. **Missing `name`/`description`** — required on every primitive (agents, workflows, actions, trigger sources). Typecheck passes without them; module load throws at deploy.
10. **Integration actions throw on failure** — prebuilt actions return their typed output directly (the shape `keystroke apps actions get` shows) and **throw** on failure; don't port `{ data, error, successful }` envelope checks from Composio docs.
11. **`.default()` on an input field makes it required in the `run()` call type** — action/workflow `run` inputs are typed from the schema's *parsed* output, so a defaulted field must still be passed at the call site. When callers should be able to omit a field, use `.optional()` and apply the fallback inside `run`.

## Documentation

Docs are the source of truth — this guide only orients you. Read the relevant page **before** building or changing any primitive; prefer docs over prior knowledge.

- **CLI:** `keystroke docs search "<query>"` to find pages; `keystroke docs query "cat /<path>"` to read (no file extension). Docs commands need no auth, org, project, or config.
- **Index:** <https://keystroke.ai/docs/llms.txt>
- **HTTP fetch:** `https://keystroke.ai/docs/<path>.md` — e.g. `/learn/agents/build-agents` → `https://keystroke.ai/docs/learn/agents/build-agents.md`. Non-`.md` URLs are for humans; fetch `.md` only.

Key pages (every `Full detail:` pointer in this guide is also a docs path; the index has the rest):

| Doc path | Read when |
| -------- | --------- |
| `/cli` | Full command reference, flags, JSON output |
| `/explore-features` | Map of all feature documentation |
| `/learn/agents/build-agents` | Models, tools, subagents, sandboxes, MCP tools on agents |
| `/learn/agents/external-channels` | Slack / external channel bindings |
| `/learn/workflows/authoring-best-practices` | Canvas-legible, replayable workflow patterns |
| `/learn/triggers/overview` | Choosing a trigger type (per-source pages live alongside) |
| `/learn/credentials/connect-credentials` | `keystroke connect`, OAuth, project credentials |
| `/learn/credentials/custom-integrations` | Building a custom HTTP / MCP / GraphQL integration |
| `/learn/skills/create-skills` | Authoring an agent skill |
| `/learn/logs/overview` | Run history, debugging deployed runs |

<!-- keystroke-agents-guide: 0.1.101 -->
