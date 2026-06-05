# JobApplicationTracker - Agent Developer Guidelines

**Version**: 1.0  
**Last Updated**: June 2026  
**Project Status**: Active Development → Production Automation

---

## Project Overview

**JobApplicationTracker** is a sophisticated full-stack application that automates the job application process using AI-powered resume tailoring, form detection, and browser automation.

### Core Value Proposition
- **One-time Profile Setup** → Automatic tailored applications to hundreds of jobs
- **Smart Automation** → Detect ATS platforms, auto-fill forms, upload documents
- **AI Resume Tailoring** → Personalize resume for each job (Cerebras 70B model)
- **Semi-Auto & Full-Auto Modes** → Manual review option or fully hands-off
- **Local First** → SQLite by default, no cloud tracking

### Tech Stack

| Component | Tech | Version |
|-----------|------|---------|
| **Backend** | FastAPI | 0.115.5 |
| **Frontend** | React + Vite | 18.3.1 + 6.0.5 |
| **Database** | SQLAlchemy + SQLite/PostgreSQL | 2.0.36 |
| **Browser Automation** | Playwright | 1.49.0 |
| **AI Model** | Cerebras (OpenAI-compatible) | llama-3.3-70b |
| **Deployment** | Docker + Railway/Render + Vercel | - |

---

## Architecture Overview

### Backend Structure (`backend/app/`)

```
app/
├── main.py                    # FastAPI app + lifecycle
├── database.py                # SQLAlchemy async setup
├── models.py                  # SQLAlchemy ORM models
├── schemas.py                 # Pydantic request/response schemas
├── routers/                   # API endpoints
│   ├── profile.py            # Profile CRUD + resume extraction
│   ├── jobs.py               # Job discovery, scraping, filtering
│   ├── applications.py       # Application tracking
│   ├── documents.py          # Resume/cover letter storage
│   ├── ai.py                 # Resume/cover letter tailoring
│   ├── automation.py         # Semi-auto browser control (old)
│   ├── auto_apply.py         # Full-auto application submission
│   └── scheduler.py          # Bulk auto-apply with criteria
└── services/                 # Business logic
    ├── cerebras_service.py   # AI extraction, tailoring, mapping
    ├── playwright_service.py # Browser session management
    ├── auto_submit.py        # Form filling, submission detection
    ├── ats_integration.py    # ATS platform detection + APIs
    ├── auto_scheduler.py     # Scheduled bulk applications
    ├── websocket_manager.py  # Real-time event broadcasting
    ├── scraper_service.py    # Job page scraping
    ├── pdf_service.py        # Resume PDF handling
    └── resume_extractor.py   # Resume text extraction

```

### Frontend Structure (`frontend/src/`)

```
src/
├── App.tsx                    # Main routing + layout
├── pages/
│   ├── Dashboard.tsx         # Overview of applications
│   ├── JobSearch.tsx         # Manual + scrape job entry
│   ├── Profile.tsx           # Profile + resume upload
│   ├── ApplicationDetail.tsx # Single application details
│   ├── Documents.tsx         # Resume/cover letter library
│   └── Onboarding.tsx        # First-run setup
├── components/
│   ├── ApplicationCard.tsx   # Job card UI
│   ├── AutomationPanel.tsx   # Live automation viewer
│   ├── DocumentUpload.tsx    # File upload
│   └── ...
└── api/
    └── client.ts            # Axios instance + type definitions
```

### Database Models (Core Entities)

#### Profile (Single user record)
- `full_name`, `email`, `phone`, `location`
- `linkedin_url`, `github_url`, `portfolio_url`
- `summary` (professional summary)
- `skills[]` (JSON array)
- `experience[]` (JSON: company, title, start, end, bullets)
- `education[]` (JSON: school, degree, field)
- `certifications[]` (JSON: name, issuer, date)

#### Job
- Title, company, location, job_type (full-time/part-time/contract/internship)
- `source` (linkedin/indeed/greenhouse/manual/etc)
- `source_url` (where job was found), `apply_url` (application form)
- Description, requirements, salary_range
- `status` (discovered/saved/applying/applied/dropped)
- `ats_platform` (auto-detected: greenhouse/workday/lever/etc)

#### Application
- Links job_id to application progress
- `status` (pending/applied/in_review/phone_screen/interview/offer/rejected)
- `applied_date`, `ats_platform`, `ats_tracking_url`
- `tailored_resume_id`, `tailored_cover_letter_id` (FK to Document)
- `automation_log[]` (JSON array of automation steps)

#### Document
- `type` (resume / cover_letter)
- `variant` (base / tailored)
- `job_id` (optional FK for tailored docs)
- `filename`, `file_path`, `content_text` (extracted text for AI)

---

## Key Workflows

### 1. **Profile Setup** → Resume Extraction
```
POST /api/profile/extract (file)
  ↓ (Cerebras AI)
Extract: full_name, email, skills, experience, education
  ↓
Store in Profile model
```

### 2. **Job Discovery** → Application Creation
```
POST /api/jobs/scrape (url)
  ↓ (BeautifulSoup4 + Cerebras)
Extract: title, company, requirements, apply_url
  ↓
Create Job model, set status="discovered"
  ↓
POST /api/applications (job_id)
Create Application model, status="pending"
```

### 3. **AI Document Tailoring**
```
POST /api/ai/tailor-resume (job_id)
  ↓ (Cerebras: prompt → resume rewrite)
Get: job description + user's base resume
  ↓
Output: tailored resume (markdown)
Save as Document(type=resume, variant=tailored, job_id=job_id)
```

### 4. **Full Auto-Apply** ⭐ (Most Important)
```
POST /api/auto-apply/full/{application_id}
  ↓
start_session() → Launch headed Chromium, navigate to apply_url
  ↓
wait_for_form_load() → Wait for form elements
  ↓
detect_ats_from_url() → Identify platform (Greenhouse/Workday/etc)
  ↓
detect_and_fill_required_fields() → AI maps fields → fill form
  ↓
upload_documents() → Upload tailored resume + cover letter
  ↓
find_and_click_submit() → Locate and click submit button
  ↓
detect_submission_success() → Check for success message/redirect
  ↓
Return: {status: "success|submitted_unverified|pending_submission|error", ...}
```

### 5. **Scheduler: Bulk Auto-Apply**
```
POST /api/scheduler/apply-now (criteria)
  ↓
Query jobs where:
  - status = "discovered"
  - keywords match (description contains "Python", "React", etc)
  - exclude_companies not in list
  - salary in range
  ↓
For each matching job:
  - Create Application
  - Call _auto_apply_to_job() → Full auto-apply pipeline
  ↓
Return: {applied: [...], failed: [...], skipped: [...]}
```

---

## Core Automation Algorithms

### Form Field Detection & Filling (`auto_submit.py`)

**Algorithm**: Heuristic + AI-assisted mapping

```python
1. Extract all visible form field labels:
   - <label> text
   - input[placeholder]
   - [aria-label] attributes

2. Use Cerebras to map labels → profile values:
   INPUT:  ["Email Address", "LinkedIn URL", "Phone Number", "Resume"]
   OUTPUT: {"Email Address": "john@example.com", "LinkedIn URL": "...", ...}

3. For each field:
   - Try multiple CSS selectors: label+input, input[name*=...], [aria-label*=...]
   - Fill with mapped value (respecting visibility)
   - Wait 200ms between fields (human-like pacing)

4. Handle special cases:
   - Dropdowns (select): Try "full-time", "2 weeks notice"
   - Checkboxes: Auto-check only if label contains "agree", "consent", "terms"
   - File inputs: Upload resume PDF with uploadDocuments()
```

### ATS Platform Detection (`ats_integration.py`)

```python
URL patterns:
  - "greenhouse.io" / "apply.greenhouse.io" → Greenhouse
  - "lever.co" → Lever
  - "workday.com" → Workday
  - "taleo" / "icims" → Taleo
  - "linkedin.com" → LinkedIn
  - "indeed.com" → Indeed
  
Per-platform:
  - Submit button selectors (platform-specific class names)
  - Form field naming conventions
  - Success detection patterns
```

### Submission Success Detection

```python
1. Check for success messages:
   "Thank you", "Success", "Application submitted", "We've received", etc.

2. Check URL changes:
   Redirect to /success, /thank, /submitted indicates successful submission

3. Best effort:
   Even if success not verified, submission likely succeeded
   Return status="submitted_unverified" + recommendation for manual review
```

---

## API Reference (Condensed)

### Profile
- `GET /api/profile` - Get profile
- `PUT /api/profile` - Update profile
- `POST /api/profile/extract` - Extract from resume PDF (multipart/form-data)

### Jobs
- `GET /api/jobs?status=discovered` - List jobs with filters
- `POST /api/jobs` - Create job manually
- `POST /api/jobs/scrape` - Scrape job from URL
- `GET /api/jobs/greenhouse/{company_slug}` - Fetch Greenhouse board

### Applications
- `GET /api/applications` - List all applications
- `POST /api/applications` - Create application (job_id)
- `PUT /api/applications/{app_id}` - Update status
- `DELETE /api/applications/{app_id}` - Delete

### Documents
- `GET /api/documents` - List documents
- `POST /api/documents` - Upload document (multipart/form-data)
- `DELETE /api/documents/{doc_id}` - Delete

### AI Services
- `POST /api/ai/tailor-resume` - Generate tailored resume (job_id)
- `POST /api/ai/generate-cover-letter` - Generate tailored cover letter (job_id)

### Full Auto-Apply ⭐
- `POST /api/auto-apply/full/{application_id}` - **Automated submission** (most important)
- `POST /api/auto-apply/detect-fields/{application_id}` - Debug: detect form fields

### Scheduler
- `POST /api/scheduler/apply-now` - Immediate bulk apply (criteria)
- `POST /api/scheduler/schedule` - Set up recurring auto-apply
- `GET /api/scheduler/status` - Check scheduler status
- `POST /api/scheduler/test` - Test criteria without applying

### Real-time Updates
- `WS /api/automation/ws/{session_id}` - WebSocket for live events:
  ```json
  {
    "session_id": "uuid",
    "step": "navigate|detect_fields|fill_field|upload_docs|control",
    "status": "running|paused|done|error",
    "message": "Filled 'Email Address'",
    "screenshot_b64": "iVBORw0KGgo..."
  }
  ```

---

## Development Patterns & Conventions

### Async/Await Pattern
- **All I/O is async**: database queries, HTTP calls, browser automation
- Use `AsyncSession` from SQLAlchemy, `async with httpx.AsyncClient()`, `await page.goto(...)`

### Error Handling
- Return structured JSON errors: `{"detail": "error message"}`
- HTTP status codes: 200 (ok), 400 (bad request), 404 (not found), 500 (server error)
- Always set `automation_log[]` on Application for debugging

### Database
- **Local dev**: SQLite (auto-created at `data/app.db`)
- **Production**: PostgreSQL (Railway or Render provided)
- `DATABASE_URL` env var or defaults to SQLite
- Migrations: Not implemented yet (add Alembic if needed)

### Environment Variables

**Required:**
```
CEREBRAS_API_KEY=your-api-key  # Get from https://cerebras.ai
```

**Optional:**
```
DATABASE_URL=postgresql://user:pass@localhost/jobtracker
ALLOWED_ORIGINS=http://localhost:3000,https://yourfrontend.com
ENVIRONMENT=development|production
```

### Playwright Browser Setup
- **Headless mode** (production): No UI visible, runs server-side
- **Headed mode** (dev): Visible Chromium window for debugging
- **Installed in Docker**: `docker build` automatically installs Chromium
- **Slow motion**: 50ms added for human-like pacing in `playwright_service.py`

### AI Integration (Cerebras)

**Model**: `gpt-oss-120b` (llama-3.3-70b) — fast, cheap, good for structured extraction

**Service Entry Points** (`cerebras_service.py`):
```python
await extract_job(page_text)              # → {title, company, location, ...}
await extract_profile(resume_text)        # → {full_name, email, skills, ...}
await tailor_resume(job_desc, job_reqs, base_resume, profile)  # → markdown
await generate_cover_letter(job_desc, company, title, profile, examples)  # → text
await map_form_fields(field_labels, profile)  # → {label: value, ...}
```

All AI prompts are deterministic + structured (JSON parsing). Set `temperature=0.1-0.3` for extraction, `0.4-0.6` for creative output.

---

## Common Tasks & Patterns

### Adding a New Endpoint
1. Create route in `routers/new_feature.py`:
   ```python
   from fastapi import APIRouter, Depends
   from ..database import get_db
   
   router = APIRouter(prefix="/api/new-feature", tags=["new-feature"])
   
   @router.post("/action")
   async def my_action(data: MySchema, db: AsyncSession = Depends(get_db)):
       # Your logic
       return {"result": "..."}
   ```

2. Register in `main.py`:
   ```python
   from .routers import new_feature
   app.include_router(new_feature.router)
   ```

3. Define schemas in `schemas.py` using Pydantic

### Adding a New Service
1. Create `services/my_service.py`
2. Import in router and call async functions
3. Keep business logic separate from API logic

### Debugging Browser Automation
1. Add WebSocket event in `playwright_service.py`:
   ```python
   await _broadcast(session_id, "step_name", "running", "message", page)
   ```
2. Frontend receives real-time updates via WebSocket
3. Screenshots included in events (base64 JPEG)

### Testing Full Auto-Apply
1. Set up profile: `PUT /api/profile` with email, phone, location
2. Create job: `POST /api/jobs/scrape` with real job URL
3. Create application: `POST /api/applications` (job_id)
4. Trigger auto-apply: `POST /api/auto-apply/full/{app_id}`
5. Watch console logs or WebSocket events for debugging

---

## Optimization Opportunities (Future Work)

### High Priority
1. **Persistent Background Scheduler** - Use Celery/RQ instead of in-memory scheduling
2. **Cover Letter Generation** - Currently placeholder; needs Cerebras integration
3. **Enhanced Field Detection** - Use computer vision (OCR) for image-based forms
4. **ATS API Integration** - Direct APIs for Greenhouse/Workday (vs form filling)
5. **Rate Limiting & Throttling** - Prevent IP bans; randomize inter-request delays

### Medium Priority
1. **Database Migrations** - Add Alembic for schema versioning
2. **Comprehensive Logging** - Structured logging to ELK/CloudWatch
3. **Authentication** - Multi-user support with OAuth/JWT
4. **Email Notifications** - Alert user when applications are submitted
5. **Analytics Dashboard** - Success rates, time-to-hire, etc.

### Low Priority
1. **Mobile App** - React Native frontend
2. **Browser Extension** - One-click apply from job boards
3. **ML Resume Matching** - Score job relevance before applying
4. **Interview Prep** - Mock interview with Cerebras

---

## Deployment Quick Start

### Backend (Railway)
1. Push to GitHub
2. Railway auto-detects Dockerfile
3. Set environment variables: `CEREBRAS_API_KEY`, `ALLOWED_ORIGINS`
4. Deploy

### Frontend (Vercel)
1. Configure root directory: `frontend/`
2. Build command: `npm run build`
3. Set `VITE_API_URL` to production backend URL
4. Deploy

### Local Development
```bash
# Backend
cd backend
python -m venv venv
source venv/bin/activate  # or `venv\Scripts\activate` on Windows
pip install -r requirements.txt
python -m uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Frontend (in new terminal)
cd frontend
npm install
npm run dev  # Runs on http://localhost:5173
```

### Docker Compose (Local Stack)
```bash
docker-compose up -d  # Spins up backend + frontend
# Backend: http://localhost:8000
# Frontend: http://localhost:80
# Swagger: http://localhost:8000/docs
```

---

## Testing & QA Checklist

### Automation Testing
- [ ] Resume extraction from PDF → correct schema
- [ ] Job scraping → all fields populated
- [ ] Form field detection → correct labels extracted
- [ ] Full auto-apply → successful submission on test job board
- [ ] Resume tailoring → output matches job keywords
- [ ] Cover letter generation → unique content per job

### Integration Testing
- [ ] Profile → Jobs → Applications → Auto-apply (end-to-end)
- [ ] WebSocket real-time updates during automation
- [ ] Scheduler bulk apply → correct filtering + results

### Production Readiness
- [ ] All env vars set correctly
- [ ] Database backup/restore tested
- [ ] Error logs readable + actionable
- [ ] Rate limiting prevents IP bans
- [ ] CORS properly configured

---

## Troubleshooting Guide

| Issue | Cause | Solution |
|-------|-------|----------|
| **Cerebras API key invalid** | Wrong key or expired | Verify key at https://cerebras.ai/console |
| **Form fields not detected** | Page not fully loaded | Increase timeout in `wait_for_form_load()` |
| **Resume upload fails** | File path incorrect or PDF corrupted | Check file exists, try re-uploading |
| **Submission not verified** | Success message not recognized | Add pattern to `detect_submission_success()` |
| **Browser times out** | Network slow or form too complex | Check network speed, increase timeout in Playwright |
| **Database locked** | Concurrent access to SQLite | Upgrade to PostgreSQL for production |
| **CORS errors** | Frontend domain not in `ALLOWED_ORIGINS` | Add frontend URL to env var |

---

## Code Style & Best Practices

### Python (Backend)
- **PEP 8** with 88-char line length (Black formatter compatible)
- **Type hints** on all functions: `async def func(x: int) -> str:`
- **Docstrings** on services/routers: explain business logic, not obvious code
- **Error handling**: Specific exceptions, log context for debugging
- **Async patterns**: Always use `await` on I/O; `asyncio.gather()` for parallel calls

### TypeScript (Frontend)
- **React functional components** with hooks only (no class components)
- **Strict null checks**: Enable `strictNullChecks` in tsconfig.json
- **Type exports**: Export types/interfaces for API responses
- **No `any`**: Use `unknown` or specific types
- **CSS**: Tailwind utility classes; avoid inline styles

### Git Workflow
- **Branches**: `feature/`, `fix/`, `docs/` prefixes
- **Commits**: Atomic, descriptive: `feat: add Cerebras resume tailoring`
- **PRs**: Link issues, describe testing done
- **Main**: Always deployable; gated by CI checks

---

## When to Escalate (Questions for Team)

1. **Architecture decisions** - Should we split into microservices?
2. **Scaling** - Max concurrent auto-apply sessions?
3. **Persistence** - Background job queue requirements?
4. **Security** - Multi-user auth + data isolation strategy?
5. **Monetization** - Freemium limits, pricing model?

---

## Quick Reference

### File Locations
- **Environment**: `backend/.env`
- **Database**: `data/app.db`
- **Resumes**: `data/documents/resumes/`
- **Generated docs**: `data/generated/`
- **Logs**: Stdout + Docker logs (use `docker logs -f`)

### Commands
```bash
# Backend tests
python -m pytest backend/

# Format code
black backend/
# Lint
pylint backend/app/

# Frontend type check
npm run check

# Build for production
npm run build
```

### Key Dependencies
- **FastAPI** - Web framework (fast, async, auto-docs)
- **SQLAlchemy** - ORM (async support essential)
- **Playwright** - Browser automation (headless + headed)
- **BeautifulSoup4** - HTML scraping
- **pydantic** - Data validation
- **Cerebras SDK** - AI model access (OpenAI-compatible)

---

## Contact & Support

- **Issues**: GitHub Issues / PR feedback
- **Questions**: Code comments + docstrings should guide
- **Deployment**: See DEPLOYMENT.md for Railway/Render/Vercel setup
- **API Docs**: Swagger UI at `http://localhost:8000/docs`

---

**Last Reviewed**: June 2026  
**Maintained By**: Development Team  
**Status**: Active → Seeking Contributors for Optimization Tasks
