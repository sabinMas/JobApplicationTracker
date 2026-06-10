# JobApplicationTracker — Architecture Overview

**Status**: Phases 0–4 complete, Phase 5 (frontend/docs) in progress  
**Last Updated**: June 10, 2026  
**Owner**: Mason  

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                           FRONTEND (Vercel)                          │
│   React 18 + Vite + TailwindCSS + React Query + Recharts           │
│   Pages: Dashboard, Pipeline, Preferences, Profile, Jobs, Docs     │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │ HTTPS
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      API GATEWAY (HTTP API v2)                       │
│   CORS: explicit origins + regex (*.vercel.app)                     │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
                                   ▼
┌─────────────────────────────────────────────────────────────────────┐
│                      LAMBDA (FastAPI + Mangum)                       │
│   • Profile, Jobs, Applications, Documents CRUD                     │
│   • AI tailoring (Bedrock Haiku/Sonnet)                             │
│   • Pipeline orchestrator (discover → score → enrich → submit)      │
│   • Enqueues heavy work (scraping, auto-apply) → SQS               │
└─────────────┬───────────────────────────────┬───────────────────────┘
              │ enqueue                        │ Bedrock
              ▼                                ▼
┌──────────────────────┐          ┌─────────────────────────┐
│   SQS Queue          │          │  Amazon Bedrock          │
│   + Dead Letter Q    │          │  Haiku: extract/score    │
│   (3 retries)        │          │  Sonnet: write/reason    │
└──────────┬───────────┘          └─────────────────────────┘
           │ poll
           ▼
┌─────────────────────────────────────────────────────────────────────┐
│                ECS FARGATE WORKER (min=0, max=3)                     │
│   Base: mcr.microsoft.com/playwright/python:v1.49.0-noble           │
│   • Playwright browser automation (auto-apply, scraping)            │
│   • @playwright/mcp (agentic scraper actor)                         │
│   • Actor framework (LinkedIn, Indeed, GitHub, Agentic actors)      │
│   • FARGATE_SPOT (80%) + FARGATE (20%)                              │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      EVENTBRIDGE SCHEDULER                           │
│   Daily 8:00 AM EST → Lambda POST /api/scheduler/run-pipeline       │
└─────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────┐
│                      DATA STORES                                     │
│   PostgreSQL (RDS) — jobs, applications, profiles, pipeline runs    │
│   S3 — resumes, cover letters, generated documents                  │
└─────────────────────────────────────────────────────────────────────┘
```

---

## Completed Phases

| Phase | Scope | Key Deliverables |
|-------|-------|-----------------|
| **0** | Security & cleanup | Removed hardcoded secrets, structured logging, StructuredLogger |
| **1** | SearchPreferences + Bedrock | `SearchPreferences` model, Bedrock `ai_service`, scoring |
| **2** | Serverless infrastructure | Dockerfile.lambda, CloudFormation stack, EventBridge, ECS min=0, CORS fix, Budget alert |
| **3** | Pipeline orchestrator | 5-stage pipeline (discover→score→enrich→tailor→submit), `PipelineRun` model |
| **4** | MCP agentic scraper | Actor framework, AgenticScraperActor with @playwright/mcp, SQS dispatch |
| **5** | Frontend + docs | Preferences page, Pipeline page, deployment guide (in progress) |

---

## Tech Stack

| Layer | Technology | Notes |
|-------|-----------|-------|
| Frontend | React 18, Vite 6, TailwindCSS 3, React Query 5, Recharts | Vercel deploy |
| API | FastAPI 0.115, Mangum 0.21 | Lambda container image |
| Database | SQLAlchemy 2.0 (async), PostgreSQL (asyncpg) | Alembic migrations |
| AI | Amazon Bedrock (Claude Haiku + Sonnet) | Replaced Cerebras |
| Browser | Playwright 1.49, @playwright/mcp | ECS worker only |
| Queue | AWS SQS + DLQ | 14-day retention, 3 retries |
| Scheduler | EventBridge Scheduler | Timezone-aware cron |
| IaC | CloudFormation | `infra/aws/cloudformation.yaml` |
| CI/CD | GitHub → ECR → Lambda/ECS update | `deploy-lambda.ps1`, `deploy-stack.ps1` |

---

## Key Design Decisions

1. **Lambda for API, ECS for worker** — Lambda is cheap and fast for HTTP; Playwright needs a full container runtime with browsers.

2. **Mangum with lifespan="off"** — Avoids running background schedulers and actor registration on every Lambda cold start. The daily pipeline is triggered by EventBridge, not an in-process scheduler.

3. **Worker min=0** — No cost when idle. SQS target-tracking auto-scaling spins up workers within ~60s of messages arriving.

4. **FARGATE_SPOT** — 70% cheaper than on-demand. Workers are stateless and retry-safe, so spot interruptions are fine.

5. **Bedrock over Cerebras** — Native AWS IAM auth (no API keys to rotate), lower latency from us-east-1, structured output support.

6. **CORS regex** — `allow_origin_regex=r"https://.*\.vercel\.app"` handles preview deploys without wildcarding credentials.

---

## File Map

```
├── Dockerfile.lambda          Lambda container (Python 3.12 + mangum)
├── Dockerfile.worker          Worker container (Playwright + Node + MCP)
├── Dockerfile.api             Legacy: gunicorn direct-serve (not used in prod)
├── backend/
│   ├── lambda_handler.py      Mangum entrypoint for Lambda
│   ├── worker_main.py         SQS poll loop for ECS
│   ├── app/
│   │   ├── main.py            FastAPI app + CORS + routers
│   │   ├── models.py          SQLAlchemy models (Job, Application, SearchPreferences, PipelineRun)
│   │   ├── schemas.py         Pydantic request/response models
│   │   ├── routers/           API endpoints
│   │   ├── services/          Business logic (pipeline, ai_service, scoring, etc.)
│   │   └── scrapers/          Actor implementations (LinkedIn, Indeed, GitHub, Agentic)
│   └── alembic/               Database migrations
├── frontend/src/
│   ├── App.tsx                Routing + nav
│   ├── api/                   Client functions (preferences, pipeline, dashboard, etc.)
│   └── pages/                 Dashboard, Pipeline, Preferences, Profile, JobSearch, etc.
├── infra/
│   ├── aws/cloudformation.yaml   Full stack template
│   └── scripts/                  Deploy scripts (PowerShell)
└── docs/
    ├── architecture/             This file + decision framework
    └── deployment/               AWS serverless deployment guide
```

---

## Daily Pipeline Flow

```
8:00 AM EST — EventBridge triggers Lambda
    │
    ├── 1. DISCOVER: Sync jobs from preference-derived sources
    │       (LinkedIn, Indeed, GitHub based on SearchPreferences)
    │
    ├── 2. SCORE: Bedrock Haiku scores new jobs 1-10
    │       (compares against niches, keywords, salary)
    │
    ├── 3. ENRICH: Queue high-scoring jobs for full scraping
    │       (SQS → ECS worker → Playwright)
    │
    ├── 4. PREPARE: Tailor resume + cover letter (Bedrock Sonnet)
    │       for jobs scoring >= min_score_to_apply
    │
    └── 5. SUBMIT: If auto_submit_enabled, enqueue auto-apply
            (SQS → ECS worker → Playwright form fill → submit)
```

---

## Budget

- **Monthly budget alert**: $30 (80% actual + 100% forecasted notifications)
- **AWS credits**: $185 available
- **Expected cost**: $5–15/month at current usage
  - Lambda: ~$1 (low invocations)
  - API Gateway: ~$1
  - ECS Fargate Spot: ~$3–8 (depends on apply volume)
  - SQS: < $1
  - RDS (if used): ~$5–10 (t4g.micro)
  - S3/Bedrock: < $2
