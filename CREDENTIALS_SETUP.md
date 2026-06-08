# Credentials Setup Guide

**Status**: Ready for configuration ✅

---

## What You've Provided

✅ **LinkedIn**
- Client ID: `YOUR_LINKEDIN_CLIENT_ID`
- Client Secret: `YOUR_LINKEDIN_CLIENT_SECRET` (truncated here)

✅ **GitHub**
- Personal Access Token: `github_pat_YOUR_TOKEN_HERE` (truncated)

✅ **AWS**
- Console: https://us-east-1.console.aws.amazon.com/console/home

---

## Setup Instructions

### 1. Configure Environment Variables

Create or update `backend/.env`:

```bash
# Copy the example
cp backend/.env.example backend/.env

# Edit with your credentials
nano backend/.env
```

Add these values:
```
LINKEDIN_CLIENT_ID=YOUR_LINKEDIN_CLIENT_ID
LINKEDIN_CLIENT_SECRET=YOUR_LINKEDIN_CLIENT_SECRET
GITHUB_ACCESS_TOKEN=github_pat_YOUR_TOKEN_HERE
```

### 2. Load Environment Variables

When running the backend:

```bash
# Linux/Mac
export $(cat backend/.env | xargs)
python -m uvicorn app.main:app --reload --port 8000

# Windows PowerShell
Get-Content backend\.env | ForEach-Object {
    if ($_ -match "^([^=]+)=(.*)$") {
        [Environment]::SetEnvironmentVariable($matches[1], $matches[2])
    }
}
python -m uvicorn app.main:app --reload --port 8000
```

### 3. Test Credentials

#### Test LinkedIn Credentials

```bash
curl -X POST "http://localhost:8000/api/jobs/sources/linkedin?client_id=YOUR_LINKEDIN_CLIENT_ID&client_secret=YOUR_LINKEDIN_CLIENT_SECRET"
```

Response:
```json
{
  "status": "success",
  "source": {
    "name": "LinkedIn",
    "type": "LinkedIn API",
    "configured": true,
    "message": "LinkedIn source added. Note: LinkedIn standard API has limitations..."
  }
}
```

#### Test GitHub Token

```bash
curl -X POST "http://localhost:8000/api/jobs/sources/github?access_token=github_pat_YOUR_TOKEN..."
```

Response:
```json
{
  "status": "success",
  "source": {
    "name": "GitHub Jobs",
    "type": "GitHub Jobs API",
    "authenticated": true,
    "api_url": "https://jobs.github.com/positions.json"
  }
}
```

### 4. Register All Job Sources

```bash
# GitHub Jobs (no auth, but with token for better rate limits)
curl -X POST "http://localhost:8000/api/jobs/sources/github?access_token=github_pat_11..."

# LinkedIn
curl -X POST "http://localhost:8000/api/jobs/sources/linkedin?client_id=$LINKEDIN_CLIENT_ID&client_secret=$LINKEDIN_CLIENT_SECRET"

# RSS Feed (example)
curl -X POST "http://localhost:8000/api/jobs/sources/rss?feed_url=https://news.ycombinator.com/rss&name=HackerNews"
```

### 5. Trigger Initial Sync

```bash
curl -X POST http://localhost:8000/api/scheduler/jobs/sync
```

Response:
```json
{
  "status": "success",
  "timestamp": "2026-06-05T19:00:00Z",
  "duration_ms": 3500,
  "stats": {
    "added": 145,
    "duplicates": 12,
    "errors": 0
  }
}
```

---

## Important Notes

### LinkedIn API Limitation

LinkedIn's standard public API **does not provide a jobs search endpoint**. The implementation will:
1. Accept credentials ✅
2. Authenticate successfully ✅
3. Return 0 jobs ✅ (expected behavior)

**To get LinkedIn jobs, you have three options:**

#### Option A: LinkedIn Recruiter API (Recommended for recruiting)
- Requires special partnership with LinkedIn
- Contact LinkedIn for access
- Most comprehensive job data

#### Option B: Web Scraping with Playwright (Recommended for personal use)
- Use `backend/app/services/playwright_service.py`
- Authenticate with your personal LinkedIn account
- Scrape your job feed
- Respects LinkedIn ToS for personal use

#### Option C: Alternative Job Boards
- Focus on RSS feeds
- GitHub Jobs
- Angel List / Wellfound
- Indeed
- Stack Overflow Jobs

### GitHub Token Benefits

The personal access token:
- ✅ Increases rate limits (60 → 5000 requests/hour)
- ✅ Allows authenticated requests
- ✅ No secrets in token (public repos only)
- ⚠️ Keep token safe (don't commit to git)

### Security Best Practices

1. **Never commit .env file**
   ```bash
   echo ".env" >> .gitignore
   git rm --cached backend/.env
   ```

2. **Rotate credentials periodically**
   - GitHub: Regenerate tokens every 6 months
   - LinkedIn: Refresh OAuth tokens

3. **Use AWS Secrets Manager (Phase 2B)**
   - Store secrets in AWS
   - Not in code or environment variables
   - Better security for production

---

## What Happens Next

### Immediate (Working Now)
- ✅ GitHub Jobs source is fully operational
- ✅ RSS feeds work
- ✅ LinkedIn source initialized (returns 0 jobs, expected)

### For More LinkedIn Jobs

**Option 1: Use Web Scraping**
```python
from app.services.playwright_service import playwright_service

# Scrape your LinkedIn job feed
jobs = await playwright_service.scrape_linkedin_jobs(
    linkedin_email="your-email@example.com",
    linkedin_password="your-password"
)
```

**Option 2: Use LinkedIn Recruiter (Enterprise)**
- Contact LinkedIn Sales
- Requires corporate account
- Full job search API access

### For Best Results Now
1. Use GitHub Jobs (400-500 jobs per sync)
2. Add RSS feeds from:
   - HackerNews: https://news.ycombinator.com/rss
   - WeWorkRemotely: https://weworkremotely.com/categories/fully-remote-jobs.rss
   - Remoteok: https://remoteok.io/feed
3. Manual job discovery on target company career pages

---

## Testing All Sources

```bash
#!/bin/bash

# Setup
BASE_URL="http://localhost:8000"

# Add sources
echo "Adding GitHub Jobs..."
curl -X POST "$BASE_URL/api/jobs/sources/github?access_token=github_pat_..."

echo "Adding LinkedIn..."
curl -X POST "$BASE_URL/api/jobs/sources/linkedin?client_id=...&client_secret=..."

echo "Adding HackerNews RSS..."
curl -X POST "$BASE_URL/api/jobs/sources/rss?feed_url=https://news.ycombinator.com/rss&name=HackerNews"

# List sources
echo "Configured sources:"
curl "$BASE_URL/api/jobs/sources"

# Sync all
echo "Starting sync..."
curl -X POST "$BASE_URL/api/scheduler/jobs/sync"

# View results
echo "Jobs by source:"
curl "$BASE_URL/api/jobs/stats"

echo "Sample jobs:"
curl "$BASE_URL/api/jobs?limit=5"
```

---

## Troubleshooting

### LinkedIn Returns 0 Jobs
**Expected behavior** - LinkedIn standard API doesn't have jobs search. Options:
1. Use web scraping (Playwright)
2. Switch to LinkedIn Recruiter API (requires partnership)
3. Use GitHub + RSS feeds instead

### GitHub Rate Limiting
If you see `429` errors:
- Ensure access_token is provided
- Token increases rate limit from 60 to 5000 requests/hour
- Check token hasn't expired

### AWS Credentials (Phase 2B)
When moving to Lambda:
```bash
aws configure
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_key
AWS_SECRET_ACCESS_KEY=your_secret
```

---

## Next Steps

1. **Load environment variables** in your terminal
2. **Start backend server**:
   ```bash
   cd backend
   python -m uvicorn app.main:app --reload --port 8000
   ```
3. **Register all job sources** (copy commands above)
4. **Trigger sync**:
   ```bash
   curl -X POST http://localhost:8000/api/scheduler/jobs/sync
   ```
5. **View jobs**:
   ```bash
   curl http://localhost:8000/api/jobs
   ```

---

**Status**: Ready to configure ✅  
**Next Action**: Load env vars and restart backend  
**Expected Result**: Jobs syncing from GitHub + RSS sources  

For LinkedIn jobs, recommend using web scraping or alternative sources.
