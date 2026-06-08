# CLAUDE.md — JobApplicationTracker

> **Authoritative context for all AI agents and agentic IDEs.**
> Read this file completely before touching any code. It is the single source of truth for architecture, rules, and conventions.

---

## 1. Project Identity

**What it is**: A full-stack personal automation tool that discovers job postings, scores them with AI, tailors a resume and cover letter per job, and submits the application through a real browser — with zero manual intervention.

**Owner**: Mason (single-user, personal use — no multi-tenant concerns yet)

**Live frontend**: https://jobapptracker-n60pbf6ah-sabinmas-projects.vercel.app

**Guiding principle**: 10 high-quality, well-matched applications per day beats 100 spray-and-pray submissions.

---

## 2. Strict Rules — Read Before Writing Any Code

These are non-negotiable. Violating them will be caught in review.

### 2.1 Code Quality
- **No synchronous I/O.** Every database call, HTTP request, and file read must be `async/await`. Use `AsyncSession`, `httpx.AsyncClient`, `aiofiles`. Never use `requests`, blocking `open()`, or synchronous SQLAlchemy.
- **No `any` in TypeScript.** Use `unknown` or a specific type. Enable `strictNullChecks`.
- **No class components in React.** Functional components + hooks only.
- **Type hints on all Python functions.** `async def my_fn(x: int) -> dict[str, str]:` — no exceptions.
- **No inline styles in the frontend.** Tailwind utility classes only. Never write `style={{ color: "red" }}`.

### 2.2 Secrets and Security
- **Never commit secrets.** `CEREBRAS_API_KEY`, DB passwords, AWS credentials, and API tokens live in `backend/.env` only. `.env` is gitignored.
- **Never hardcode URLs, IPs, or credentials** in source files.
- **CORS**: The `ALLOWED_ORIGINS` env var controls allowed origins. Do not hardcode origins.
- **SQL**: Use SQLAlchemy ORM — never raw string-interpolated SQL queries.
- **Never log sensitive data** (resume content, PII, API keys) to CloudWatch or stdout.

### 2.3 Architecture Boundaries
- **Routers are thin.** A router function calls a service and returns the result. No business logic in routers.
- **Services own business logic.** All non-trivial logic goes in `backend/app/services/`.
- **Frontend talks only to the FastAPI backend.** No direct AWS SDK calls from the React app (no `@aws-sdk/client-lambda` in frontend code).
- **Do not add new top-level root files.** Scripts, configs, and documentation belong in their respective subdirectories (`infra/`, `docs/`, `backend/`, `frontend/`). The root contains only `README.md`, `AGENT.md`, `CLAUDE.md`, `docker-compose.yml`, `Dockerfile`, `railway.json`, `vercel.json`, and deploy scripts.

### 2.4 Documentation
- **Update `CLAUDE.md`** any time you add a service, router, data model field, or change a core workflow.
- **No new markdown files at the project root.** Documentation belongs in `docs/`.
- **No session-note files** (`SESSION_SUMMARY.md`, `ACTION_ITEMS.md`, etc.). These are generated noise — commit meaningful changes, not AI session logs.

### 2.5 Testing and Deployment
- **All tests must pass before pushing.** Run `pytest backend/` from the repo root.
- **Do not modify `infra/` scripts without understanding the AWS state** — Lambda, RDS, and S3 are live resources.
- **Never run `git push --force` to master.**
- **Do not push with `--no-verify`.**

### 2.6 AI and Automation
- **Always set `temperature=0.1`–`0.3` for extraction tasks** and `0.4`–`0.6` for creative writing (resumes, cover letters).
- **Never auto-submit an application without a tailored resume attached.** Verify `tailored_resume_id` is set on the Application before calling `auto_apply`.
- **Respect ATS platform rate limits.** Add a 200–500ms delay between field fills (`await page.wait_for_timeout(200)`). Never fire-and-forget bulk apply jobs.

---

## 3. Repository Layout

```
JobApplicationTracker/
├── backend/
│   ├── app/
│   │   ├── main.py                      # FastAPI app init + router registration
│   │   ├── database.py                  # Async SQLAlchemy engine + session factory
│   │   ├── models.py                    # ORM models (single source of truth)
│   │   ├── schemas.py                   # Pydantic request/response schemas
│   │   ├── logging_config.py            # Structured JSON logging to CloudWatch
│   │   ├── routers/
│   │   │   ├── ai.py                    # Resume tailoring + cover letter endpoints
│   │   │   ├── applications.py          # Application CRUD + status tracking
│   │   │   ├── auto_apply.py            # Full automation trigger endpoint
│   │   │   ├── auto_apply_scored.py     # Score-gated auto-apply
│   │   │   ├── automation.py            # Semi-auto WebSocket session (legacy)
│   │   │   ├── dashboard.py             # Dashboard metrics aggregation
│   │   │   ├── documents.py             # Resume/cover letter upload + retrieval
│   │   │   ├── jobs.py                  # Job CRUD + scraping + Greenhouse search
│   │   │   ├── metrics.py               # Metrics API
│   │   │   ├── profile.py               # Profile CRUD + PDF extraction
│   │   │   └── scheduler.py             # Bulk auto-apply scheduling
│   │   └── services/
│   │       ├── ats_integration.py       # ATS URL detection + platform routing
│   │       ├── ats_routers/
│   │       │   ├── base.py              # Abstract ATS router interface
│   │       │   ├── form_fallback.py     # Generic HTML form filler
│   │       │   ├── greenhouse.py        # Greenhouse API integration
│   │       │   └── lever.py             # Lever API integration
│   │       ├── auto_apply_with_scoring.py # Score check before apply
│   │       ├── auto_scheduler.py        # Scheduled bulk application runner
│   │       ├── auto_submit.py           # Form detection, field mapping, submission
│   │       ├── cerebras_service.py      # All Cerebras AI calls (extraction + tailoring)
│   │       ├── job_scorer.py            # AgentCore job scoring (1–10)
│   │       ├── job_sources/
│   │       │   ├── base.py              # Abstract job source
│   │       │   ├── angellist_source.py
│   │       │   ├── github_source.py
│   │       │   ├── linkedin_source.py
│   │       │   └── rss_source.py
│   │       ├── job_sync_scheduler.py    # Periodic job discovery runner
│   │       ├── pdf_service.py           # PDF generation (ReportLab)
│   │       ├── playwright_service.py    # Browser session lifecycle
│   │       ├── resume_extractor.py      # pdfplumber text extraction
│   │       ├── retry_service.py         # Exponential backoff retry logic
│   │       ├── s3_service.py            # AWS S3 document storage
│   │       ├── scraper_service.py       # BeautifulSoup job page scraping
│   │       └── websocket_manager.py     # Real-time event broadcasting
│   ├── tests/                           # pytest test suite
│   ├── requirements.txt
│   └── .env.example
├── frontend/
│   └── src/
│       ├── App.tsx                      # Router + layout
│       ├── api/client.ts                # Axios instance + typed API calls
│       ├── pages/
│       │   ├── Dashboard.tsx
│       │   ├── JobSearch.tsx
│       │   ├── Profile.tsx
│       │   ├── ApplicationDetail.tsx
│       │   ├── Documents.tsx
│       │   └── Onboarding.tsx
│       └── components/
│           ├── ApplicationCard.tsx
│           ├── AutomationPanel.tsx
│           ├── DocumentUpload.tsx
│           ├── KanbanBoard.tsx
│           └── StatusBadge.tsx
├── infra/                               # AWS Lambda + deployment scripts
├── docs/                                # All documentation (never dump files here from root)
│   ├── architecture/
│   ├── api/
│   ├── deployment/
│   ├── getting-started/
│   ├── integrations/
│   ├── phases/
│   └── roadmap.md
├── data/                                # gitignored — SQLite DB + PDFs
├── CLAUDE.md                            # ← this file
├── AGENT.md                             # Extended technical reference
└── README.md                            # Project entry point
```

---

## 4. Tech Stack

| Layer | Technology | Version | Notes |
|---|---|---|---|
| Backend framework | FastAPI | 0.115.5 | Async-first |
| ORM | SQLAlchemy (async) | 2.0.36 | Never use sync Session |
| Validation | Pydantic | 2.10.3 | All request/response schemas |
| Browser automation | Playwright | 1.49.0 | Chromium, headed in dev |
| AI model | Cerebras `llama-3.3-70b` | via OpenAI SDK | Fast + cheap |
| PDF extraction | pdfplumber | 0.11.4 | Resume text extraction |
| PDF generation | ReportLab | 4.2.5 | Tailored resume output |
| HTTP client | httpx | 0.28.0 | Async, never `requests` |
| HTML scraping | BeautifulSoup4 | 4.12.3 | |
| AWS | boto3 / mangum | 1.43.24 / 0.21.0 | Lambda ASGI adapter |
| Frontend | React 18 + Vite | 18.3.1 + 6.0.5 | |
| Styling | TailwindCSS | — | Utility classes only |
| Data fetching | React Query | — | |
| Charts | Recharts | — | |
| Local DB | SQLite (aiosqlite) | — | `data/app.db` |
| Prod DB | PostgreSQL (asyncpg) | — | AWS RDS |
| Prod storage | AWS S3 | — | `jobtracker-documents-245091941294` |
| Scheduling | AWS EventBridge | — | Daily 8 AM EST sync |
| Logging | Python `logging` + watchtower | — | CloudWatch |
| Test runner | pytest + pytest-asyncio | — | |

---

## 5. Data Models

Defined in `backend/app/models.py`. Do not alter models without a migration plan.

### Profile (single row, `id=1`)
| Field | Type | Notes |
|---|---|---|
| `full_name`, `email`, `phone`, `location` | String | Contact info |
| `linkedin_url`, `github_url`, `portfolio_url` | String | Links |
| `summary` | Text | Professional summary |
| `skills` | JSON `[]` | `["Python", "React", ...]` |
| `experience` | JSON `[]` | `{company, title, start, end, bullets:[]}` |
| `education` | JSON `[]` | `{school, degree, field, start, end, gpa}` |
| `certifications` | JSON `[]` | `{name, issuer, date}` |

### Job
| Field | Type | Notes |
|---|---|---|
| `title`, `company`, `location` | String | |
| `job_type` | String | `full-time \| part-time \| contract \| internship` |
| `source` | String | `linkedin \| indeed \| greenhouse \| github \| angellist \| rss \| manual` |
| `source_url`, `apply_url` | String | Where found vs. where to apply |
| `description`, `requirements` | Text | |
| `status` | String | `discovered \| saved \| applying \| applied \| dropped` |
| `score` | Integer | 1–10, set by `job_scorer.py` |
| `score_reasoning` | Text | Why this score |
| `score_strengths`, `score_concerns` | JSON `[]` | Positive/negative factors |
| `score_recommendation` | String | `SUBMIT \| SKIP` |

### Application
| Field | Type | Notes |
|---|---|---|
| `job_id` | FK → Job | |
| `status` | String | `pending \| applied \| in_review \| phone_screen \| interview \| offer \| rejected \| withdrawn` |
| `ats_platform` | String | `greenhouse \| lever \| workday \| taleo \| bamboohr \| other` |
| `tailored_resume_id`, `tailored_cover_letter_id` | FK → Document | Must be set before auto-apply |
| `automation_log` | JSON `[]` | `{step, status, message, timestamp}` |
| `retry_count`, `last_error`, `error_history` | — | Retry tracking |

### Document
| Field | Type | Notes |
|---|---|---|
| `type` | String | `resume \| cover_letter` |
| `variant` | String | `base \| tailored` |
| `job_id` | FK → Job (nullable) | Set for tailored variants |
| `filename`, `file_path` | String | Filesystem paths under `data/` |
| `content_text` | Text | Extracted text for AI consumption |

### ApplicationMetric
Tracks every submission attempt for analytics — timing, status, ATS platform, error type.

---

## 6. Core Workflows

### 6.1 Job Discovery
```
EventBridge (daily 8 AM) OR POST /api/scheduler/apply-now
  → job_sync_scheduler.py → job_sources/{linkedin,github,angellist,rss}_source.py
  → scraper_service.py (BeautifulSoup)
  → cerebras_service.extract_job(page_text) → Job record created, status="discovered"
  → job_scorer.py → score 1–10 written to Job
```

### 6.2 Resume Tailoring
```
POST /api/ai/tailor-resume  { job_id }
  → cerebras_service.tailor_resume(job_desc, requirements, base_resume, profile)
  → temperature=0.5, structured markdown output
  → Document(type=resume, variant=tailored, job_id=X) saved to data/generated/
  → Application.tailored_resume_id updated
```

### 6.3 Full Auto-Apply  ← The most important flow
```
POST /api/auto-apply/full/{application_id}
  1. Verify tailored_resume_id is set — abort if missing
  2. playwright_service.start_session() → headless Chromium
  3. page.goto(apply_url)
  4. ats_integration.detect_ats_from_url(url) → platform name
  5. ats_routers/{greenhouse,lever,form_fallback}.submit(job, profile, page)
       Form fallback path:
         auto_submit.detect_and_fill_required_fields(page, profile)
         → Extract labels → cerebras_service.map_form_fields() → fill each field
         → 200ms delay between fields
         → upload_documents(resume_path, cover_letter_path)
         → find_and_click_submit()
         → detect_submission_success() → check "Thank you" / URL redirect
  6. Application.status updated, automation_log appended
  7. ApplicationMetric row written
  8. Return { status: "success|submitted_unverified|pending_submission|error" }
```

### 6.4 Retry Logic
`retry_service.py` implements exponential backoff: 1s → 4s → 16s → 64s, max 3 attempts. On each retry, ATS detection reruns in case the URL changed. Tracked via `retry_count`, `error_history[]` on Application.

---

## 7. API Endpoints (Summary)

Full reference: [docs/api/reference.md](docs/api/reference.md)

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/api/profile` | Get user profile |
| `PUT` | `/api/profile` | Update profile |
| `POST` | `/api/profile/extract` | Extract profile from resume PDF |
| `GET` | `/api/jobs` | List jobs (supports `?status=discovered`) |
| `POST` | `/api/jobs/scrape` | Scrape job from URL |
| `GET` | `/api/jobs/greenhouse/{slug}` | Browse a company's Greenhouse board |
| `GET` | `/api/applications` | List applications |
| `POST` | `/api/applications` | Create application from job_id |
| `PUT` | `/api/applications/{id}` | Update status / notes |
| `POST` | `/api/ai/tailor-resume` | Generate tailored resume |
| `POST` | `/api/ai/generate-cover-letter` | Generate cover letter |
| `POST` | `/api/auto-apply/full/{id}` | **Trigger full automation** |
| `POST` | `/api/auto-apply/detect-fields/{id}` | Debug: inspect form fields |
| `POST` | `/api/scheduler/apply-now` | Bulk apply with filter criteria |
| `GET` | `/api/metrics/dashboard` | Aggregated analytics |
| `WS` | `/api/automation/ws/{session_id}` | Real-time automation events |

WebSocket event shape:
```json
{
  "session_id": "uuid",
  "step": "navigate | detect_fields | fill_field | upload_docs | submit | verify",
  "status": "running | paused | done | error",
  "message": "Filled 'Email Address'",
  "screenshot_b64": "iVBOR..."
}
```

---

## 8. Development Conventions

### Python
- **PEP 8**, 88-char line length (Black-compatible)
- All I/O is `async` — see [Tech Stack](#4-tech-stack) for the right library per operation
- Errors return `{"detail": "message"}` with the correct HTTP status code
- Log with the structured logger from `logging_config.py`, not `print()`
- New routers: create in `routers/`, include in `main.py` with `app.include_router()`
- New services: create in `services/`, call from router with dependency injection

### TypeScript / React
- Functional components + `useState`/`useEffect`/`useQuery` only
- All API calls go through `src/api/client.ts` — never `fetch()` or raw `axios` calls
- Types for all API responses — export from `client.ts`

### Environment Variables
```
# Required
CEREBRAS_API_KEY=your-key

# Optional — defaults shown
DATABASE_URL=sqlite+aiosqlite:///../data/app.db
ALLOWED_ORIGINS=http://localhost:5173
ENVIRONMENT=development
AWS_REGION=us-east-1
S3_BUCKET_NAME=jobtracker-documents-245091941294
```

### Running Locally
```bash
# Backend
cd backend && .\venv\Scripts\activate   # or source venv/bin/activate
uvicorn app.main:app --reload --port 8000
# Swagger: http://localhost:8000/docs

# Frontend
cd frontend && npm run dev
# App: http://localhost:5173

# Full stack
docker-compose up
```

### Running Tests
```bash
pytest backend/          # all tests
pytest backend/ -v -k "test_apply"  # filter by name
```

---

## 9. Current Deployment State

| Component | Status | Detail |
|---|---|---|
| Frontend (Vercel) | ✅ Live | Auto-deploys on push to master |
| Lambda function | ✅ Active | `jobtracker-api`, Python 3.13, 512 MB |
| PostgreSQL (RDS) | ✅ Ready | Scoring columns migration applied via `infra/add_scoring_to_jobs.sql` |
| S3 bucket | ✅ Available | `jobtracker-documents-245091941294`, versioning on |
| EventBridge scheduler | ✅ Enabled | Daily 8 AM EST |
| Function URL / API Gateway | ⚠️ Blocked | 403 Forbidden — `smm-app` IAM user needs `AmazonAPIGatewayFullAccess`. See [docs/deployment/phase4-guide.md](docs/deployment/phase4-guide.md) |
| Lambda binary deps | ⚠️ Fixed | `deploy-package-linux/` has the correct Linux-built `pydantic_core`. Use `lambda-deploy-linux-fixed.zip` |

**Immediate unblock path**: Grant API Gateway IAM permissions → run `infra/setup-api-gateway-simple.ps1` → set `VITE_API_URL` in Vercel → done.

---

## 10. Roadmap Phases

| Phase | Goal | Status |
|---|---|---|
| 1 | Observability, retry logic, monitoring dashboard, intelligent routing | ✅ Complete |
| 2 | AWS Lambda, RDS PostgreSQL, S3, EventBridge | ✅ Complete |
| 3 | AgentCore scoring, Lever/Greenhouse API routing | ✅ Complete |
| 4 | Dashboard API, scored auto-apply, binary fix for Lambda | ✅ Complete (unblocked pending IAM fix) |
| 5 | Email tracking, interview notification parsing, follow-up automation | Planned |
| 6 | ML niche job detection, user feedback scoring loop | Planned |

---

## 11. Key File Locations

| What | Where |
|---|---|
| Environment variables | `backend/.env` (gitignored) |
| Local SQLite database | `data/app.db` |
| Uploaded resumes | `data/documents/resumes/` |
| AI-generated documents | `data/generated/` |
| ORM models | `backend/app/models.py` |
| Cerebras AI calls | `backend/app/services/cerebras_service.py` |
| Form fill + submit logic | `backend/app/services/auto_submit.py` |
| ATS detection | `backend/app/services/ats_integration.py` |
| Job scoring | `backend/app/services/job_scorer.py` |
| Retry logic | `backend/app/services/retry_service.py` |
| Structured logging setup | `backend/app/logging_config.py` |
| Lambda deployment zip | `infra/lambda-deploy-linux-fixed.zip` |
| DB scoring migration | `infra/add_scoring_to_jobs.sql` |
| API Gateway setup script | `infra/setup-api-gateway-simple.ps1` |

---

## 12. Anti-Patterns — Never Do These

- **Do not** use `requests` or synchronous `open()` anywhere in the backend
- **Do not** put business logic in router functions — routers call services
- **Do not** store PDFs or generated documents in the git repo
- **Do not** create markdown files at the project root — use `docs/`
- **Do not** log PII (email, phone, resume text) to CloudWatch
- **Do not** call the Lambda function from the React frontend directly (no `@aws-sdk/client-lambda` in frontend)
- **Do not** skip the `tailored_resume_id` check before auto-applying
- **Do not** run bulk apply without per-job delay — instant loops will trigger IP bans
- **Do not** amend published commits or force-push to master
- **Do not** add new root-level config, script, or doc files without a strong reason

---

## 13. Security Checklist

Before any PR:
- [ ] No secrets, tokens, or credentials in code or committed files
- [ ] No raw SQL string interpolation
- [ ] CORS `ALLOWED_ORIGINS` is not `*` in production config
- [ ] No PII in log statements
- [ ] File uploads validate MIME type before saving
- [ ] Playwright sessions are always closed in a `finally` block

---

**Maintained by**: Mason  
**Last updated**: June 2026  
**Version**: 2.0
