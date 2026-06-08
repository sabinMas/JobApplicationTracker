# Job Application Tracker

A full-stack dashboard that automates the job application process — powered by Cerebras AI, Playwright, and AWS Lambda.

**Live**: https://jobapptracker-n60pbf6ah-sabinmas-projects.vercel.app

---

## Features

- **Kanban board** — drag jobs across Discovered → Applied → Interview → Offer
- **URL import** — paste any job URL (LinkedIn, Indeed, ZipRecruiter, Handshake) and AI extracts all details
- **Greenhouse search** — browse open roles directly from any company's board
- **AI tailoring** — Cerebras 70B generates a custom resume and cover letter per job
- **Playwright auto-apply** — real browser fills forms and submits applications automatically
- **Job scoring** — AgentCore scores each job 1–10 based on your profile match
- **ATS support** — Greenhouse, Lever, Workday, Taleo, LinkedIn, Indeed, ZipRecruiter, custom forms

---

## Quick Start

### Backend

```bash
cd backend
cp .env.example .env          # add your CEREBRAS_API_KEY
.\venv\Scripts\activate       # Windows — or: source venv/bin/activate
uvicorn app.main:app --reload --port 8000
```

API available at `http://localhost:8000` · Swagger at `http://localhost:8000/docs`

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

---

## Project Structure

```
JobApplicationTracker/
├── backend/            FastAPI · SQLAlchemy · Playwright · Cerebras
├── frontend/           React · Vite · TypeScript · TailwindCSS
├── infra/              AWS Lambda · deployment scripts · IaC
├── data/               SQLite DB + PDFs (gitignored)
├── docs/               All project documentation
│   ├── architecture/   System design, decisions, executive summary
│   ├── api/            API reference and quick reference
│   ├── deployment/     Deployment guides, status, troubleshooting
│   ├── getting-started/ Setup, credentials, quickstart guides
│   ├── integrations/   Third-party integration notes (Lever, etc.)
│   ├── phases/         Development phase history
│   │   ├── phase-1/
│   │   ├── phase-2/
│   │   ├── phase-3/
│   │   └── phase-4/
│   └── roadmap.md
├── AGENT.md            AI agent developer guidelines
└── README.md
```

---

## Environment Variables (`backend/.env`)

| Variable | Description |
|---|---|
| `CEREBRAS_API_KEY` | Cerebras API key |
| `DATA_DIR` | Path to data folder (default: `../data`) |
| `DATABASE_URL` | SQLite URL (default: `sqlite+aiosqlite:///../data/app.db`) |
| `ALLOWED_ORIGINS` | CORS origins (e.g. `http://localhost:5173`) |
| `ENVIRONMENT` | `development` or `production` |

---

## Documentation

| Topic | File |
|---|---|
| Architecture & design decisions | [docs/architecture/overview.md](docs/architecture/overview.md) |
| API reference | [docs/api/reference.md](docs/api/reference.md) |
| Deployment guide | [docs/deployment/guide.md](docs/deployment/guide.md) |
| Credentials setup | [docs/getting-started/credentials.md](docs/getting-started/credentials.md) |
| Quickstart (live) | [docs/getting-started/quickstart.md](docs/getting-started/quickstart.md) |
| Roadmap | [docs/roadmap.md](docs/roadmap.md) |
| Lever integration | [docs/integrations/lever.md](docs/integrations/lever.md) |
| Deployment troubleshooting | [docs/deployment/troubleshooting-lambda.md](docs/deployment/troubleshooting-lambda.md) |
| AI agent guidelines | [AGENT.md](AGENT.md) |

---

## Deployment Status

| Component | Status |
|---|---|
| Frontend (Vercel) | ✅ Live |
| Lambda Function | ✅ Active |
| PostgreSQL (RDS) | ✅ Ready |
| S3 Storage | ✅ Available |
| EventBridge Scheduler | ✅ Daily 8 AM EST |
| Function URL / API Gateway | ⚠️ Needs IAM permissions — see [deployment guide](docs/deployment/phase4-guide.md) |

---

## License

MIT
