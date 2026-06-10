# Job Application Tracker

A full-stack job automation platform — discovers jobs, scores them with AI, tailors resumes, and auto-applies via browser automation. Runs on AWS Lambda + ECS Fargate with zero idle cost.

**Live**: https://jobapptracker-n60pbf6ah-sabinmas-projects.vercel.app

---

## Features

- **Daily pipeline** — automated discover → score → enrich → tailor → submit (8 AM EST)
- **Kanban board** — drag jobs across Discovered → Applied → Interview → Offer
- **URL import** — paste any job URL and AI extracts all details
- **Search Preferences** — define target roles, niches, keywords, salary floor
- **AI scoring** — Bedrock Claude scores each job 1–10 against your preferences
- **AI tailoring** — Bedrock Sonnet generates custom resume + cover letter per job
- **Playwright auto-apply** — real browser fills forms and submits (ECS worker)
- **MCP agentic scraper** — @playwright/mcp actor for complex job board navigation
- **ATS support** — Greenhouse, Lever, Workday, Taleo, LinkedIn, Indeed, ZipRecruiter

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
| `DATABASE_URL` | PostgreSQL async URL (default: SQLite for local dev) |
| `ALLOWED_ORIGINS` | CORS origins (e.g. `http://localhost:5173`) |
| `ENVIRONMENT` | `development` or `production` |
| `SQS_QUEUE_URL` | SQS queue for worker tasks (auto-set by CloudFormation) |
| `S3_BUCKET` | Document storage bucket |
| `AWS_REGION` | AWS region (default: `us-east-1`) |

> **Note**: Bedrock uses IAM role auth — no API keys needed. Cerebras key is optional (legacy).

---

## Documentation

| Topic | File |
|---|---|
| Architecture overview | [docs/architecture/overview.md](docs/architecture/overview.md) |
| AWS serverless deployment | [docs/deployment/aws-serverless.md](docs/deployment/aws-serverless.md) |
| Scraper/Actor API guide | [docs/scraper-api-guide.md](docs/scraper-api-guide.md) |
| Roadmap | [docs/roadmap.md](docs/roadmap.md) |
| AI agent guidelines | [AGENT.md](AGENT.md) |

---

## Deployment Status

| Component | Status |
|---|---|
| Frontend (Vercel) | ✅ Live |
| Lambda + API Gateway | ✅ CloudFormation stack |
| ECS Worker (min=0) | ✅ Auto-scales on SQS depth |
| SQS + DLQ | ✅ 3 retries, 14-day retention |
| EventBridge Scheduler | ✅ Daily 8 AM EST |
| PostgreSQL (RDS) | ✅ Ready |
| S3 Storage | ✅ Available |
| Bedrock (Haiku + Sonnet) | ✅ Auto-enabled |
| Budget Alert ($30/mo) | ✅ Active |

---

## License

MIT
