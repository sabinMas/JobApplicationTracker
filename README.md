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
| `ALLOWED_ORIGINS` | CORS origins (e.g., `http://localhost:5173,https://your-domain.com`) |
| `ENVIRONMENT` | `development` or `production` |

---

## 🚀 Full Automation Features

The app now supports **fully automated job applications** across all major ATS platforms:

### Supported Platforms
- **Greenhouse** - Most common for startups/tech
- **Lever** - Popular for modern companies
- **Workday** - Large enterprises
- **Taleo** - Fortune 500 companies
- **LinkedIn** - Direct applications
- **Indeed** - Indeed's application flow
- **ZipRecruiter** - Job boards
- **Custom forms** - Any standard HTML form

### Automation Endpoints

#### Full Auto-Apply
```bash
POST /api/auto-apply/full/{application_id}
```
Automatically:
1. Opens the application page
2. Auto-fills all form fields using your profile
3. Uploads tailored resume and cover letter
4. Submits the application
5. Verifies successful submission

**Response:**
```json
{
  "status": "success|submitted_unverified|pending_submission|error",
  "message": "Application submitted successfully!",
  "application_id": 123
}
```

#### Detect Required Fields
```bash
POST /api/auto-apply/detect-fields/{application_id}
```
Returns list of required form fields before automation.

---

## Deployment

### Local Docker
```bash
docker-compose up
```
Starts backend on port 8000.

### Production Deployment
See [DEPLOYMENT.md](./DEPLOYMENT.md) for full guide.

**Quick Deploy to Railway:**
1. Push to GitHub
2. Go to railway.app → New Project → GitHub
3. Set environment variables
4. Railway auto-deploys

**Deploy Frontend to Vercel:**
1. Go to vercel.com → Import Project
2. Select your repo and `frontend` folder
3. Set `VITE_API_URL` to your backend URL
4. Deploy

---

## API Reference

### Jobs
- `GET /api/jobs` - List all jobs
- `POST /api/jobs` - Create job manually
- `POST /api/jobs/scrape` - Scrape job from URL
- `GET /api/jobs/{id}` - Get job details
- `PUT /api/jobs/{id}` - Update job
- `DELETE /api/jobs/{id}` - Delete job
- `GET /api/jobs/greenhouse/{company_slug}` - Fetch Greenhouse jobs

### Applications
- `GET /api/applications` - List all applications
- `POST /api/applications` - Create application
- `PUT /api/applications/{id}` - Update status
- `DELETE /api/applications/{id}` - Delete application

### Profile
- `GET /api/profile` - Get your profile
- `PUT /api/profile` - Update profile
- `POST /api/profile/extract` - Extract from resume PDF

### Documents
- `GET /api/documents` - List documents
- `POST /api/documents` - Upload document
- `DELETE /api/documents/{id}` - Delete document

### AI
- `POST /api/ai/tailor-resume` - Generate tailored resume
- `POST /api/ai/generate-cover-letter` - Generate cover letter

### Automation
- `POST /api/automation/start` - Start browser session
- `POST /api/automation/fill/{session_id}` - Fill form fields
- `POST /api/automation/upload-docs/{session_id}` - Upload files
- `POST /api/automation/submit/{session_id}` - Submit form (semi-auto)
- `GET /api/automation/screenshot/{session_id}` - Get screenshot
- `POST /api/automation/pause/{session_id}` - Pause automation
- `POST /api/automation/resume/{session_id}` - Resume automation
- `POST /api/automation/stop/{session_id}` - Stop session
- `WS /api/automation/ws/{session_id}` - WebSocket for live updates

### Auto-Apply (Full Automation)
- `POST /api/auto-apply/full/{application_id}` - Fully automate application
- `POST /api/auto-apply/detect-fields/{application_id}` - Detect required fields

---

## How It Works

### The Job Search → Application Workflow

```
1. Search & Import
   ├─ Paste job URL (LinkedIn, Indeed, etc.)
   ├─ Cerebras extracts: title, company, salary, requirements
   └─ Job saved to Kanban board

2. Prepare Documents
   ├─ Cerebras generates tailored resume
   ├─ Cerebras generates cover letter
   └─ AI mirrors keywords from job posting

3. Apply (2 Options)
   ├─ OPTION A: Semi-Auto (Old)
   │  ├─ Browser opens with you watching
   │  ├─ Click "Pause" to take control anytime
   │  └─ Click "Resume" to let AI continue
   │
   └─ OPTION B: Full Auto (New)
      ├─ Completely automated end-to-end
      ├─ No manual intervention needed
      └─ Supports 10+ ATS platforms

4. Track Status
   ├─ Update application status (Applied → Interview → Offer)
   ├─ Add interview notes
   └─ Monitor all applications in one place
```

---

## Why This Works

- **AI-Powered**: Cerebras 70B model handles complex form mapping
- **Multi-ATS Support**: Detects and handles different application systems
- **Real Browser**: Uses Playwright for JavaScript-heavy forms
- **Tailored Docs**: Each application gets a custom resume + cover letter
- **Fully Tracked**: Everything logged in one dashboard

---

## Troubleshooting

### "Browser timeout"
- Increase `timeout` in playwright_service.py
- Check your internet connection
- Some sites block automation; use semi-auto instead

### "Form fields not detected"
- The ATS may use JavaScript rendering; browser will wait
- You can pause and manually fill fields
- Manual review is sometimes needed

### "Submission failed"
- Some companies require email verification
- Others have captchas
- Check the browser screenshot for clues

### "Cerebras API errors"
- Verify your API key is valid
- Check rate limits at cerebras.ai
- API is very affordable

---

## Contributing

Ideas or issues? Open a GitHub issue or PR.

---

## License

MIT
