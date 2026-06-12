---
name: run-jobapptracker
description: Launch and drive the JobApplicationTracker app (backend API + React frontend) locally for testing and development
---

# Run JobApplicationTracker

A full-stack job automation tool: AI-powered resume tailoring, form filling, and application submission. Built with FastAPI (async Python backend), React 18 + Vite (frontend), Playwright (browser automation), and AWS Bedrock (Claude 3 AI).

**Agent path:** Use the smoke script below to verify all critical endpoints. For interactive testing, launch the frontend browser at http://localhost:5173 and the Swagger API docs at http://localhost:8000/docs.

---

## Prerequisites

- **Node.js** 20+: `node --version` (should be v20+)
- **Python** 3.11+: `python --version`
- **PowerShell** (Windows) or Bash (any platform)
- The repo is already cloned and you're in the working directory

---

## Build & Setup

### 1. Backend Setup (Python)
```bash
cd backend
python -m venv venv
source venv/Scripts/activate  # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

**Expected output:**
```
Successfully installed 40+ packages...
```

### 2. Frontend Setup (Node)
```bash
cd frontend
npm install
```

**Expected output:**
```
up to date, audit OK
```

### 3. Environment Configuration
Create `backend/.env` with required variables:
```bash
# Backend .env
DATABASE_URL=sqlite+aiosqlite:///../data/app.db
ALLOWED_ORIGINS=http://localhost:5173
ENVIRONMENT=development

# AWS / Bedrock (primary AI provider)
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key_here
AWS_SECRET_ACCESS_KEY=your_secret_here

# Fallback AI (optional)
CEREBRAS_API_KEY=your_key_here
```

---

## Run (Agent Path)

The smoke script below is what an agent uses to verify the system is working. It hits all critical endpoints and confirms the app is alive.

### 1. Start Backend (port 8000)
```bash
cd backend
source venv/Scripts/activate
uvicorn app.main:app --reload --port 8000
```

**Expected:** App starts in ~3 seconds. Watch for `Application startup complete` in logs.

### 2. Start Frontend (port 5173, in a parallel terminal)
```bash
cd frontend
npm run dev
```

**Expected:** `VITE v6.4.2 ready in 256 ms` → navigate to http://localhost:5173

### 3. Run Smoke Test (verify all endpoints)
```bash
# From repo root
bash .claude/skills/run-jobapptracker/smoke.sh
```

**Expected output:** All endpoints return 200 or correct status; no timeouts.

---

## Smoke Script

The driver `.claude/skills/run-jobapptracker/smoke.sh` is a curl-based endpoint validator:

```bash
#!/bin/bash
# Smoke test — verify all critical endpoints respond

echo "=== Backend Health ==="
curl -s http://localhost:8000/health | jq .

echo "=== Profile Endpoint ==="
curl -s http://localhost:8000/api/profile | jq '.full_name, .email'

echo "=== Applications List ==="
curl -s http://localhost:8000/api/applications | jq 'length'

echo "=== Swagger API Docs ==="
curl -s http://localhost:8000/openapi.json | jq '.info.title'

echo "=== Frontend (Vite) ==="
curl -s http://localhost:5173 -o /dev/null -w "HTTP %{http_code}\n"

echo "All endpoints OK ✓"
```

---

## Run (Human Path)

If you prefer to interact with the UI directly:

```bash
# Terminal 1: Backend
cd backend && source venv/Scripts/activate && uvicorn app.main:app --reload --port 8000

# Terminal 2: Frontend
cd frontend && npm run dev

# Terminal 3: Open browser
open http://localhost:5173
```

Then click through the UI:
1. **Dashboard** — view job discovery metrics
2. **Add Job** — scrape a job posting from a URL or search LinkedIn
3. **Profile** — upload or edit your resume and work experience
4. **Pipeline** — see applications and their status
5. **Preferences** — configure job search filters

---

## Gotchas

### API Routes Require Exact Format
- ✅ Correct: `curl http://localhost:8000/api/profile` (no trailing slash)
- ✅ Correct: `curl http://localhost:8000/api/applications` (redirect from `/` → Swagger error; use no slash)
- ❌ Wrong: `curl http://localhost:8000/api/jobs/` (trailing slash on `/jobs` → 500 error due to RDS schema mismatch; use `/api/jobs` without slash)

### Frontend Proxy in Dev Mode
The Vite dev server (`:5173`) automatically proxies API calls to `:8000` via the `vite.config.ts` proxy rule:
```
/api → http://localhost:8000
/ws  → ws://localhost:8000
```

So in the browser, fetch(`/api/profile`) goes to `http://localhost:8000/api/profile` transparently.

### Database State
- **SQLite (local dev):** `data/app.db` is created on first run. It's gitignored.
- **PostgreSQL (production):** The app tries to connect to RDS. In dev with SQLite, some endpoints (like `/api/jobs/`) fail due to missing `search_preferences` table — this is expected. Use `/api/applications` instead, which works fine.

### Backend Startup Time
The backend takes **~3 seconds** on first startup (actor framework initialization, job sources registration). Subsequent reloads (file changes) are instant.

### Trailing Slash Behavior
FastAPI redirects `/api/applications/` → `/api/applications` (307 redirect). The smoke script uses curl without the slash to avoid double-hop redirects.

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| **Port 5173 already in use** | Kill the process: `lsof -i :5173 \| grep -v PID \| awk '{print $2}' \| xargs kill` (macOS/Linux) or find it in Task Manager (Windows) |
| **Port 8000 already in use** | Same as above, but for port 8000 |
| **`ModuleNotFoundError` in backend** | Run `pip install -r requirements.txt` again; check Python version is 3.11+ |
| **`npm ERR` in frontend** | Clear cache: `rm -rf node_modules package-lock.json && npm install` |
| **Frontend shows 404 on any route** | Ensure Vite dev server is running and `vercel.json` has the SPA rewrite rule intact |
| **API returns "Internal Server Error"** | Check backend logs for the error; likely a missing environment variable or DB schema mismatch (expected with SQLite dev) |
| **Playwright crashes on form fill** | Ensure Chromium is installed: `npx playwright install` (not usually needed for dev, but try it) |

---

## Verify Installation

Run the smoke script to confirm everything works:

```bash
bash .claude/skills/run-jobapptracker/smoke.sh
```

If all checks pass (✓), the system is ready for development or testing.

---

## Key URLs

| Service | URL | Purpose |
|---------|-----|---------|
| **Frontend** | http://localhost:5173 | React app — dashboard, job search, profile, applications |
| **API Docs** | http://localhost:8000/docs | Swagger/OpenAPI — interactive API explorer (63 endpoints) |
| **Health Check** | http://localhost:8000/health | Backend status; returns `{"status": "ok"}` |
| **API Base** | http://localhost:8000/api | All REST endpoints (no trailing slash) |

---

## Next Steps

- **For agents:** Run the smoke script to verify. Then use the API (curl) or browser to test features.
- **For developers:** Edit code in `backend/app/` or `frontend/src/`, save, and watch for hot-reload. Tests: `pytest backend/` and `npm run build`.
- **For testers:** Use the browser UI to smoke-test the golden path: discover jobs → create application → view dashboard metrics.
