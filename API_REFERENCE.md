# JobApplicationTracker - Complete API Reference

## Base URL
- **Development**: `http://localhost:8000`
- **Production**: Your Railway/Render backend URL

All responses are JSON. Timestamps are ISO 8601 format.

---

## Authentication

Currently no authentication required. For production, consider adding:
- API keys per user
- JWT tokens
- OAuth (GitHub, Google, etc.)

---

## Health Check

### GET /health
Check if the API is running.

**Response:**
```json
{
  "status": "ok",
  "service": "JobApplicationTracker"
}
```

---

## Profile Management

### GET /api/profile
Get your profile.

**Response:**
```json
{
  "id": 1,
  "full_name": "John Doe",
  "email": "john@example.com",
  "phone": "+1-555-1234",
  "location": "San Francisco, CA",
  "linkedin_url": "https://linkedin.com/in/johndoe",
  "github_url": "https://github.com/johndoe",
  "portfolio_url": "https://johndoe.dev",
  "summary": "Software engineer with 5 years experience",
  "skills": ["Python", "React", "PostgreSQL"],
  "experience": [...],
  "education": [...],
  "certifications": [...]
}
```

### PUT /api/profile
Update your profile.

**Request:**
```json
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "skills": ["Python", "React", "TypeScript"],
  "location": "Remote"
}
```

### POST /api/profile/extract
Extract profile from resume PDF (uses BERT NER + Cerebras AI).

**Request:** (multipart/form-data)
- `file`: PDF resume file

**Response:**
```json
{
  "extracted": {
    "full_name": "John Doe",
    "email": "john@example.com",
    "skills": ["Python", "React"],
    ...
  },
  "document_id": 123
}
```

---

## Job Management

### GET /api/jobs
List all jobs with optional filtering.

**Query Parameters:**
- `status`: `discovered` | `saved` | `applying` | `applied` | `dropped`
- `source`: `linkedin` | `indeed` | `greenhouse` | `manual` | etc.

**Response:**
```json
[
  {
    "id": 1,
    "title": "Senior Backend Engineer",
    "company": "TechCorp",
    "location": "San Francisco, CA",
    "job_type": "full-time",
    "source": "linkedin",
    "source_url": "https://linkedin.com/jobs/view/123",
    "apply_url": "https://techcorp.greenhouse.io/apply",
    "salary_range": "$150k - $200k",
    "status": "discovered",
    "created_at": "2026-05-22T10:00:00Z"
  }
]
```

### POST /api/jobs
Create a job manually.

**Request:**
```json
{
  "title": "Senior Backend Engineer",
  "company": "TechCorp",
  "location": "San Francisco, CA",
  "job_type": "full-time",
  "apply_url": "https://techcorp.greenhouse.io/apply",
  "salary_range": "$150k - $200k",
  "description": "We are looking for...",
  "requirements": "5+ years experience..."
}
```

### POST /api/jobs/scrape
Scrape job details from a URL and import.

**Request:**
```json
{
  "url": "https://linkedin.com/jobs/view/123"
}
```

**Response:**
```json
{
  "id": 1,
  "title": "Senior Backend Engineer",
  "company": "TechCorp",
  "apply_url": "...",
  ...
}
```

### GET /api/jobs/greenhouse/{company_slug}
Fetch available jobs from a Greenhouse job board.

**Example:**
```
GET /api/jobs/greenhouse/techcorp
```

**Response:**
```json
[
  {
    "id": "123",
    "title": "Backend Engineer",
    "absolute_url": "https://techcorp.greenhouse.io/jobs/123"
  }
]
```

### GET /api/jobs/{job_id}
Get a specific job.

### PUT /api/jobs/{job_id}
Update a job.

### DELETE /api/jobs/{job_id}
Delete a job.

---

## Applications

### GET /api/applications
List all applications.

**Query Parameters:**
- `status`: `pending` | `applied` | `in_review` | `phone_screen` | `interview` | `offer` | `rejected`

### POST /api/applications
Create an application for a job.

**Request:**
```json
{
  "job_id": 1,
  "notes": "Great company, really interested"
}
```

### PUT /api/applications/{application_id}
Update application status.

**Request:**
```json
{
  "status": "applied",
  "ats_platform": "greenhouse",
  "ats_tracking_url": "https://techcorp.greenhouse.io/applications/123",
  "notes": "Application submitted"
}
```

### DELETE /api/applications/{application_id}
Delete an application.

---

## Documents

### GET /api/documents
List all documents (resumes, cover letters).

### POST /api/documents
Upload a new document.

**Request:** (multipart/form-data)
- `file`: PDF or text file
- `type`: `resume` | `cover_letter`
- `variant`: `base` | `tailored`
- `job_id`: (optional) Associate with specific job

### DELETE /api/documents/{document_id}
Delete a document.

---

## AI Services

### POST /api/ai/tailor-resume
Generate a tailored resume for a specific job.

**Request:**
```json
{
  "job_id": 1
}
```

**Response:**
```json
{
  "resume_text": "# John Doe\n\n## Experience\n...",
  "document_id": 456
}
```

### POST /api/ai/generate-cover-letter
Generate a tailored cover letter.

**Request:**
```json
{
  "job_id": 1
}
```

**Response:**
```json
{
  "cover_letter_text": "Dear Hiring Manager,\n\n...",
  "document_id": 457
}
```

---

## Automation (Semi-Auto with Manual Control)

### POST /api/automation/start
Start a browser session for a job application.

**Request:**
```json
{
  "application_id": 1
}
```

**Response:**
```json
{
  "session_id": "uuid-xxx-xxx",
  "status": "running",
  "message": "Browser opened for TechCorp — Senior Engineer"
}
```

### POST /api/automation/fill/{session_id}
Auto-fill form fields using your profile.

### POST /api/automation/upload-docs/{session_id}
Upload resume and/or cover letter to the form.

**Request:**
```json
{
  "application_id": 1
}
```

### GET /api/automation/screenshot/{session_id}
Get a base64-encoded screenshot of current page.

**Response:**
```json
{
  "screenshot_b64": "iVBORw0KGgoAAAANSUhEUgAA..."
}
```

### POST /api/automation/pause/{session_id}
Pause automation (you take manual control).

### POST /api/automation/resume/{session_id}
Resume automation from pause.

### POST /api/automation/stop/{session_id}
Stop the browser session and clean up.

### GET /api/automation/status/{session_id}
Get session status and logs.

### WS /api/automation/ws/{session_id}
WebSocket connection for real-time updates during automation.

**Events:**
```json
{
  "session_id": "uuid-xxx",
  "step": "navigate|detect_fields|fill_field|upload_docs|control",
  "status": "running|paused|done|error",
  "message": "Filled 'Email Address'",
  "screenshot_b64": "iVBORw0KGgoA..."
}
```

---

## Full Auto-Apply (Fully Automated)

### POST /api/auto-apply/full/{application_id}
Completely automate the job application process.

Automatically:
1. Fills all form fields
2. Uploads tailored documents
3. Submits the application
4. Verifies submission

**Response:**
```json
{
  "status": "success|submitted_unverified|pending_submission|error",
  "message": "Application submitted successfully!",
  "application_id": 1
}
```

Possible statuses:
- `success`: Application fully submitted and verified
- `submitted_unverified`: Button clicked but success not verified (manual review recommended)
- `pending_submission`: Form filled but submit button not found
- `error`: Something went wrong

### POST /api/auto-apply/detect-fields/{application_id}
Detect required fields on the application form.

**Response:**
```json
{
  "session_id": "uuid-xxx",
  "required_fields": ["Email", "Phone", "Resume"],
  "status": "ready_for_review"
}
```

---

## Job Application Scheduler (Bulk Auto-Apply)

### POST /api/scheduler/apply-now
Immediately apply to all jobs matching criteria.

**Request:**
```json
{
  "keywords": ["Python", "Backend", "API"],
  "location": ["Remote", "San Francisco"],
  "job_types": ["full-time"],
  "exclude_companies": ["Company X"],
  "min_salary": 120000,
  "max_salary": 200000
}
```

**Response:**
```json
{
  "status": "completed",
  "results": {
    "applied": [
      {"job_id": 1, "company": "TechCorp", "title": "Backend Engineer"}
    ],
    "failed": [
      {"job_id": 2, "reason": "Form detection failed"}
    ],
    "skipped": [
      {"job_id": 3, "reason": "Already applied"}
    ]
  },
  "applied_count": 1,
  "failed_count": 1
}
```

### POST /api/scheduler/test
Test criteria without actually applying.

**Request:**
```json
{
  "keywords": ["Python"],
  "exclude_companies": ["Company X"]
}
```

**Response:**
```json
{
  "matching_jobs": 5,
  "jobs": [
    {
      "id": 1,
      "title": "Python Developer",
      "company": "StartupA",
      "location": "Remote"
    }
  ]
}
```

### POST /api/scheduler/schedule
Set up automatic applications on a schedule.

**Request:**
```json
{
  "enabled": true,
  "interval_minutes": 30,
  "criteria": {
    "keywords": ["Python", "Backend"],
    "job_types": ["full-time"],
    "exclude_companies": ["Company X"]
  }
}
```

### GET /api/scheduler/status
Get scheduler status.

---

## Error Responses

All errors follow this format:

```json
{
  "detail": "Error message here"
}
```

**Common HTTP Status Codes:**
- `200` - Success
- `400` - Bad request (invalid parameters)
- `404` - Not found
- `500` - Server error

---

## Rate Limiting

Currently no rate limiting. For production, consider implementing:
- Per-IP limits
- Per-API-key limits
- Prevent DOS attacks

---

## CORS

The backend accepts requests from:
- `ALLOWED_ORIGINS` environment variable
- Configurable per deployment

---

## WebSocket

Connect to `/api/automation/ws/{session_id}` for real-time updates during automation.

**Send:**
```json
{"type": "ping"}
```

**Receive:**
```json
{"type": "pong"}
```

Or automation events with screenshots.

---

## Example Workflow

### 1. Set up profile
```bash
POST /api/profile
{
  "full_name": "John Doe",
  "email": "john@example.com",
  "skills": ["Python", "React"]
}
```

### 2. Import a job
```bash
POST /api/jobs/scrape
{
  "url": "https://linkedin.com/jobs/view/123"
}
# Returns job with id=1
```

### 3. Create application
```bash
POST /api/applications
{
  "job_id": 1
}
# Returns application with id=1
```

### 4. Generate tailored documents
```bash
POST /api/ai/tailor-resume
{
  "job_id": 1
}
```

### 5. Apply (Full Auto)
```bash
POST /api/auto-apply/full/1
# Returns success status
```

**Done!** Application submitted.

---

## Swagger UI

Visit `http://localhost:8000/docs` for interactive API explorer.

---

## Questions?

See README.md for more info or check DEPLOYMENT.md for production setup.
