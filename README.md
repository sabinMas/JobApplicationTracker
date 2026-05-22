# Job Application Tracker

A local-first dashboard to automate your entire job application process — powered by Cerebras AI and Playwright.

## Features

- **Kanban dashboard** — drag and drop jobs across Discovered → Applied → Interview → Offer
- **URL import** — paste any job URL (LinkedIn, Indeed, ZipRecruiter, Handshake) and AI extracts all details
- **Greenhouse search** — browse open roles directly from any company's Greenhouse board
- **AI tailoring** — Cerebras generates a custom resume + cover letter for every job
- **Playwright auto-apply** — watch a real browser open the company site and fill the form for you
- **ATS tracking** — store links to each company's application portal and track your status
- **100% local** — SQLite database, local file storage, no cloud required

---

## Quick Start

### 1. Backend

```bash
cd backend

# Copy env and add your Cerebras API key
cp .env.example .env
# Edit .env: set CEREBRAS_API_KEY=your_key_here

# Activate virtual environment
.\venv\Scripts\activate          # Windows
# source venv/bin/activate       # Mac/Linux

# Start the API server
uvicorn app.main:app --reload --port 8000
```

The API will be at `http://localhost:8000` with Swagger docs at `http://localhost:8000/docs`.

### 2. Frontend

```bash
cd frontend
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## First-Time Setup

1. Go to **Profile** → upload your resume PDF → click "Extract with AI" to auto-populate your profile
2. Go to **Documents** → upload 1–3 cover letter examples for AI style matching
3. Go to **Add Job** → paste a job URL → click Import
4. Open the job → click **Tailor Resume + Cover Letter** → Cerebras generates custom docs
5. Click **Auto-Apply** → watch Playwright fill out the application form in a real browser
6. After applying → paste the company's application tracking URL to monitor your status

---

## Project Structure

```
JobApplicationTracker/
├── backend/         FastAPI + SQLAlchemy + Playwright + Cerebras
├── frontend/        React + Vite + TypeScript + TailwindCSS
├── data/            Local SQLite DB + uploaded/generated PDFs (gitignored)
└── README.md
```

---

## Environment Variables (`backend/.env`)

| Variable | Description |
|---|---|
| `CEREBRAS_API_KEY` | Your Cerebras API key |
| `DATA_DIR` | Path to data folder (default: `../data`) |
| `DATABASE_URL` | SQLite URL (default: `sqlite+aiosqlite:///../data/app.db`) |
