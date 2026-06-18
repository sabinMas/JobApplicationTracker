# Agent Rules — JobApplicationTracker

**Version**: 1.0  
**Last Updated**: June 2026  
**Owner**: QA / Coordination role  

> Every coding agent MUST read this file completely before writing a single line of code.
> These rules are enforced by CI and PR review. Violations block merges.

---

## 0. Fresh-Start Protocol (Run at the start of every session)

Every agent session begins cold — no memory of prior sessions. Execute these steps in order before doing anything else:

```
1. Read CLAUDE.md in full (single source of truth for architecture + rules)
2. Read this file (AGENT_RULES.md) in full
3. Run: git pull origin master --rebase
4. Run: git status  (confirm clean working tree)
5. Read your domain's current files (see Section 3) to understand current state
6. Run: git log --oneline -20  (understand what changed recently)
7. Check for open PRs from your domain: gh pr list --state open
```

Only after completing all 7 steps may you begin writing code.

---

## 1. Domain Assignments

Each agent owns exactly one domain. **Never modify files outside your domain without explicit user instruction.** If a task requires cross-domain changes, coordinate via a PR comment and wait for acknowledgment.

### Agent 1 — Backend

**Owns:**
```
backend/app/main.py
backend/app/database.py
backend/app/models.py
backend/app/schemas.py
backend/app/logging_config.py
backend/app/routers/          (all .py)
backend/app/services/         (all .py, all subdirectories)
backend/app/scrapers/         (all .py)
backend/alembic/
backend/lambda_handler.py
backend/worker_main.py
backend/tests/
backend/requirements.txt
backend/pytest.ini
backend/alembic.ini
```

**Must not touch:** `frontend/`, `infra/`, `.github/`, `vercel.json`, `docker-compose.yml`, `Dockerfile.*`

**Primary rules:**
- All I/O is async — `AsyncSession`, `httpx.AsyncClient`, `aiofiles`. Never `requests`, never blocking `open()`.
- Type hints on every function signature. No exceptions.
- All AI calls go through `backend/app/services/ai_service.py` — never call `cerebras_service` or `bedrock_service` directly from routers.
- Routers are thin — call a service, return the result. No business logic in routers.
- New endpoints: add to router, register router in `main.py`, add schema to `schemas.py`.
- New model fields: include migration plan or Alembic migration file in the same PR.

---

### Agent 2 — Frontend

**Owns:**
```
frontend/src/
frontend/package.json
frontend/tsconfig.json
frontend/vite.config.ts
frontend/tailwind.config.js
frontend/postcss.config.js
frontend/index.html
vercel.json
```

**Must not touch:** `backend/`, `infra/`, `.github/`, `Dockerfile.*`, `docker-compose.yml`

**Primary rules:**
- No `any` in TypeScript. Use `unknown` or a specific type.
- All API calls go through `src/api/client.ts`. Never call `fetch()` or raw `axios` directly in components.
- No inline styles — Tailwind utility classes only. Never `style={{ ... }}`.
- Functional components + hooks only. No class components.
- Export all API response types from `client.ts`.
- The Vercel SPA rewrite in `vercel.json` (`/(.*) → /index.html`) must never be removed.
- If `VITE_API_URL` is undefined the app falls back to `/api` (breaks on Vercel). Always verify env var is set for production builds.

---

### Agent 3 — Infrastructure

**Owns:**
```
infra/scripts/
infra/aws/
Dockerfile.api
Dockerfile.worker
Dockerfile.lambda
docker-compose.yml
.github/workflows/
```

**Must not touch:** `backend/`, `frontend/`, `vercel.json` (Frontend owns this)

**Primary rules:**
- Every Docker build for Lambda must use `--provenance=false --sbom=false` — Lambda cannot read OCI manifest lists with attestations.
- Never hard-code credentials, account IDs, or endpoints in scripts. Use environment variables or AWS Parameter Store.
- CI/CD changes require a passing dry-run before merging.
- ECS task definitions: document any change to CPU/memory limits in the PR description.
- Any new GitHub Actions workflow must include a `concurrency` group to prevent duplicate runs.

---

## 2. Git Workflow

### Branch naming
```
<agent>/<short-description>
# Examples:
backend/add-email-tracking-model
frontend/fix-pipeline-kanban-drag
infra/add-secrets-scan-workflow
```

### Commit rules

| Trigger | Action |
|---|---|
| Every ~75–100 lines of new/changed code | Commit |
| Every completed logical unit (one feature, one bug fix, one refactor) | Commit |
| Before switching context within a session | Commit |
| Before any destructive operation (delete, rename, migrate) | Commit |
| After green test run | Commit (include `pytest OK` or `tsc OK` in message) |

**Commit message format:**
```
<type>(<scope>): <what changed>

# Types: feat, fix, refactor, test, docs, chore, infra
# Examples:
feat(backend): add email tracking model and migration
fix(frontend): restore VITE_API_URL fallback guard
test(backend): add pipeline service integration tests
docs: update CLAUDE.md AI provider section to Bedrock
```

**Never:**
- `git push --force` to master
- `git commit --no-verify`
- Commit `.env`, secrets, or generated PDFs
- Commit to master directly — always use a branch + PR

### Pull Request rules

- Open a PR when your branch has ≥ 1 commit and the work represents a reviewable unit
- PR description must include: what changed, why, how to test, screenshots for frontend changes
- CI must be green before requesting review
- One PR per domain per logical feature — don't bundle unrelated changes
- After CI passes and review is done, **squash-merge** into master
- Delete the branch immediately after merge

---

## 3. Documentation Review Schedule

Agents tend to hallucinate when their internal model of the codebase drifts from reality. Prevent this with regular review checkpoints.

| Checkpoint | When | What to read |
|---|---|---|
| **Session start** | Always (step 1–6 of Fresh-Start Protocol) | CLAUDE.md + AGENT_RULES.md + recent git log |
| **After every 3 commits** | Mandatory | Re-read your domain's main entry file (`main.py` / `App.tsx` / `ci.yml`) to confirm your mental model matches the file |
| **Before opening a PR** | Mandatory | Re-read CLAUDE.md Section 12 (Anti-Patterns) and Section 13 (Security Checklist) |
| **When you add a new service/router/model** | Mandatory | Confirm CLAUDE.md Sections 3, 5, 7, 11 still accurately describe the project. If not, update CLAUDE.md in the same PR. |
| **When a test fails unexpectedly** | Mandatory | Re-read the affected service file from disk before debugging — your cached understanding may be wrong |

---

## 4. Cleanup Protocol

Every session should leave the repo cleaner than it was found. Before closing a session:

### File hygiene checklist

```
[ ] No new markdown files added to the project root
[ ] No session-note files created anywhere (SESSION_SUMMARY, ACTION_ITEMS, HANDOFF, etc.)
[ ] No debug print() statements left in backend code
[ ] No console.log() left in frontend code (except inside error boundaries)
[ ] No commented-out code blocks left in committed files
[ ] No TODO comments added without a corresponding GitHub issue number
[ ] No .env files modified or created outside backend/.env
[ ] No duplicate imports in any file you touched
[ ] pytest passes (backend agent)  /  tsc -b passes (frontend agent)
```

### Stale file detection

Before committing, run:
```bash
# Backend: find files imported nowhere
grep -r "from app.services" backend/app/ | grep -oP "from \K[^\s]+" | sort -u

# Frontend: check for unused exports
npx ts-prune --project frontend/tsconfig.json 2>/dev/null | head -20
```

If you find a file that is imported nowhere and has no external callers, flag it in your PR description as a candidate for deletion. Do not delete without confirming with the user.

### Documentation update trigger

Update CLAUDE.md in the same commit/PR when you:
- Add or rename a service file
- Add or rename a router
- Add a field to a data model
- Change the deployment state (Section 9)
- Complete a roadmap phase (Section 10)
- Change a core workflow (Section 6)

---

## 5. CI Gates — What Blocks a Merge

The `.github/workflows/ci.yml` runs on every PR. All four jobs must pass:

| Job | What it checks | Blocks merge? |
|---|---|---|
| `backend-lint` | `ruff check` + `ruff format --check` on `backend/app/` | Yes |
| `backend-test` | `pytest tests/ -x` | Yes |
| `frontend-build` | `tsc -b --noEmit` + `vite build` | Yes |
| `secrets-scan` | gitleaks full commit history scan | Yes |

**If CI fails on your PR:**
1. Read the full error output — do not guess
2. Fix the issue locally, confirm it passes locally, then push
3. Do not mark CI failures as expected or bypass them with `--no-verify`

---

## 6. What Never Changes (Agent Hard Limits)

These actions require explicit user approval in the conversation before proceeding:

- Deleting any file outside your domain
- Modifying `backend/app/models.py` without an Alembic migration
- Changing `ALLOWED_ORIGINS` in any config
- Modifying anything in `infra/aws/` (live AWS resources)
- Force-pushing to any branch
- Changing the SPA rewrite in `vercel.json`
- Adding any new npm package with a bundle size > 50 KB (check with `bundlephobia`)
- Adding any new Python package that requires C extension compilation

---

## 7. Inter-Agent Communication Protocol

Since agents run in isolated sessions with no shared memory, coordination happens through git artifacts:

- **Blocking another agent's work**: Open a GitHub Issue tagged with the other agent's domain (e.g., `[Frontend]`) describing the dependency
- **API contract changes**: Backend agent must update `schemas.py` and open a PR with the comment "Frontend dependency — review before merging"
- **Shared model changes**: Backend agent opens the PR; Frontend and Infra agents must review before merge
- **Emergency cross-domain fix**: User explicitly instructs — agent notes it in commit message as `[cross-domain: <reason>]`

---

## 8. AI Provider Reference (Current)

The primary AI provider is **Amazon Bedrock (Nova Lite / Nova Pro)** via `backend/app/services/ai_service.py`.
Cerebras (`llama-3.3-70b`) is the fallback provider.

**All AI calls must route through `ai_service.py`.** Never import `cerebras_service` or `bedrock_service` directly in routers.

```python
# Correct
from app.services.ai_service import ai_service
result = await ai_service.extract_job(page_text)

# Wrong — direct provider call
from app.services.cerebras_service import extract_job
```

Temperature guidance:
- Extraction / classification tasks: `temperature=0.1`–`0.3`
- Creative writing (resume tailoring, cover letters): `temperature=0.4`–`0.6`

---

**Maintained by**: QA / Coordination role  
**Never modify this file without user instruction.**
