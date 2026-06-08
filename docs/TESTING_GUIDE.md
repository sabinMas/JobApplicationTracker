# Phase 5: Testing Guide — Job Enrichment & Actor Framework

This guide covers testing the production-ready Phase 5 implementation, including the actor-based scraper framework, job enrichment pipeline, and end-to-end auto-apply workflows.

## Prerequisites

- Backend running locally: `uvicorn app.main:app --reload` on `http://localhost:8000`
- Frontend running: `npm run dev` on `http://localhost:5173`
- `.env` file configured with `CEREBRAS_API_KEY` and `DATABASE_URL`
- Docker and `docker-compose` available for containerized testing

## 1. API Health & Initialization

### 1.1 Health Check

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "ok",
  "service": "JobApplicationTracker",
  "db_initialized": true
}
```

### 1.2 Verify Actors Are Registered

Check CloudWatch logs (or stdout during local dev) for actor registration messages:

```
INFO     app.main:_init_actors:33 - Actors initialized successfully
```

You should see 4 actors registered:
- `TestActor` — Simple test scraper, always returns mock data
- `LinkedInActor` — LinkedIn.com job scraper
- `IndeedActor` — Indeed.com job scraper
- `GitHubActor` — GitHub Jobs scraper

## 2. Individual Actor Testing

### 2.1 Test Actor

The simplest actor — always succeeds, returns 3 mock jobs.

```bash
curl -X POST http://localhost:8000/api/scrapers/run \
  -H "Content-Type: application/json" \
  -d '{"actor": "test"}'
```

Expected response:
```json
{
  "actor": "test",
  "count": 3,
  "jobs": [
    {
      "title": "Mock Python Developer",
      "company": "Acme Corp",
      "location": "Remote",
      "source": "test",
      "source_url": "https://example.com/mock-job-1"
    },
    ...
  ]
}
```

### 2.2 LinkedIn Actor

Scrapes LinkedIn job search results. Requires network access and rate limiting.

```bash
curl -X POST http://localhost:8000/api/scrapers/run \
  -H "Content-Type: application/json" \
  -d '{
    "actor": "linkedin",
    "config": {
      "query": "senior python engineer",
      "location": "United States",
      "max_pages": 1
    }
  }'
```

**Parameters:**
- `query`: Job title/keywords (required)
- `location`: Geographic area (default: "United States")
- `max_pages`: Number of pages to scrape (default: 1, max: 3 recommended)

**Expected behavior:**
- Fetches LinkedIn search page
- Extracts 10–25 job links per page
- For each job, navigates to detail page and extracts text via Cerebras
- Returns list of jobs with title, company, description, requirements, salary range (if present)
- Respects 0.5s rate limit between fetches to prevent IP bans

**Common errors:**
- 403 Forbidden: LinkedIn blocking the bot. Wait 1 hour and retry.
- Timeout after 30s: Network issue or LinkedIn slow. Retry with smaller scope.
- No jobs returned: Search term too specific or no matches. Adjust query.

### 2.3 Indeed Actor

Scrapes Indeed.com for job listings.

```bash
curl -X POST http://localhost:8000/api/scrapers/run \
  -H "Content-Type: application/json" \
  -d '{
    "actor": "indeed",
    "config": {
      "query": "data scientist",
      "location": "new york",
      "max_results": 10
    }
  }'
```

**Parameters:**
- `query`: Job title (required, spaces converted to `+`)
- `location`: City or region (default: "united states")
- `max_results`: Max jobs to return (default: 25)

**Expected behavior:**
- Searches Indeed.com with given query/location
- Extracts job IDs from search results (limited to first 5 per page)
- Fetches each job detail page
- Uses Cerebras to extract structured data
- Returns jobs with source="indeed" and Indeed apply URL

**Rate limiting:** 0.5s between job detail page fetches to avoid 429 Too Many Requests.

### 2.4 GitHub Actor

Scrapes GitHub Jobs (https://jobs.github.com).

```bash
curl -X POST http://localhost:8000/api/scrapers/run \
  -H "Content-Type: application/json" \
  -d '{
    "actor": "github",
    "config": {
      "query": "rust developer",
      "location": "remote",
      "max_results": 15
    }
  }'
```

**Parameters:**
- `query`: Job title (required)
- `location`: Job location (default: "remote")
- `max_results`: Number of jobs to return (default: 25)

**Expected behavior:**
- Searches jobs.github.com
- Extracts job links with regex pattern
- Fetches each job detail and extracts with Cerebras
- Returns jobs with source="github"

---

## 3. Job Enrichment Pipeline

The enrichment pipeline automatically triggers for high-scoring jobs (score ≥ 7) to fetch detailed descriptions and requirements.

### 3.1 Trigger Enrichment Manually

```bash
curl -X POST http://localhost:8000/api/jobs/enrich-high-scoring \
  -H "Content-Type: application/json" \
  -d '{"score_threshold": 7}'
```

Expected response:
```json
{
  "enrichment_runs_created": 3,
  "jobs_processed": 3,
  "message": "Enrichment pipeline triggered for 3 high-scoring jobs"
}
```

### 3.2 Verify Enrichment Progress

Check Application metrics dashboard to see enrichment status:

```bash
curl http://localhost:8000/api/metrics/dashboard
```

Look for `enriched_count` in the response — should increase as enrichment completes.

### 3.3 Check Job Enrichment Status

Retrieve a specific job to see if enrichment completed:

```bash
curl http://localhost:8000/api/jobs/{job_id}
```

Successful enrichment should have:
- `status: "enriched"` (instead of "discovered")
- `description` field populated (longer, more detailed text)
- `requirements` field populated with bullet-point list
- `salary_range` if available

### 3.4 Verify Source-Based Actor Routing

The enrichment service automatically selects the correct actor based on job source:

| Job Source | Actor Used |
|---|---|
| `linkedin` | LinkedInActor |
| `indeed` | IndeedActor |
| `github` | GitHubActor |
| `rss` | TestActor (fallback) |
| `manual` | TestActor (fallback) |

If a job has `source="linkedin"`, enrichment will use `LinkedInActor` to fetch additional details.

---

## 4. Load Testing & Concurrent Actors

### 4.1 Simulate Multiple Concurrent Scrapes

This tests the event-driven scraper framework under load. Use Apache Bench or similar:

```bash
ab -n 5 -c 2 -p scrape-payload.json -T application/json http://localhost:8000/api/scrapers/run
```

Where `scrape-payload.json` contains:
```json
{"actor": "test"}
```

This sends 5 requests with 2 concurrent connections. Expected:
- All requests complete within 10s
- No memory leaks or zombie processes
- Logs show 5 successful scraper executions

### 4.2 Stress Test with Different Actors in Sequence

```bash
# Run test, linkedin, indeed, github in sequence
for actor in test linkedin indeed github; do
  curl -X POST http://localhost:8000/api/scrapers/run \
    -H "Content-Type: application/json" \
    -d "{\"actor\": \"$actor\"}" \
    2>&1 | jq '.count'
done
```

Each should complete with a non-zero job count.

### 4.3 Monitor Memory During Concurrent Runs

In production (ECS Fargate), the container is limited to 1 GB. Monitor during load:

```bash
# In CloudWatch Logs Insights
fields @timestamp, @message, @duration
| filter @message like /scraper|actor/
| stats avg(@duration) as avg_duration, max(@duration) as max_duration by actor
```

Expected: All actors complete within 5s per run on average.

---

## 5. Error Handling & Resilience

### 5.1 Test Retry Logic on Transient Failures

Mock a network error by temporarily blocking access:

```bash
# Add iptables rule (Linux/macOS) to block LinkedIn
# sudo iptables -A OUTPUT -d api.linkedin.com -j DROP

curl -X POST http://localhost:8000/api/scrapers/run \
  -H "Content-Type: application/json" \
  -d '{"actor": "linkedin", "config": {"query": "python"}}'

# Wait 30s, then unblock:
# sudo iptables -D OUTPUT -d api.linkedin.com -j DROP
```

Expected behavior:
- First attempt fails with timeout/connection error
- System logs `"error_count": 1` in automation_log
- Retry logic triggers after 1s delay
- Subsequent attempts succeed (if network restored)

### 5.2 Test Invalid Configuration Handling

```bash
# Missing required 'query' parameter
curl -X POST http://localhost:8000/api/scrapers/run \
  -H "Content-Type: application/json" \
  -d '{"actor": "linkedin", "config": {"location": "USA"}}'
```

Expected: HTTP 400 with error message explaining missing 'query'.

### 5.3 Test Unknown Actor Gracefully

```bash
curl -X POST http://localhost:8000/api/scrapers/run \
  -H "Content-Type: application/json" \
  -d '{"actor": "nonexistent"}'
```

Expected: HTTP 404 with message like "Actor 'nonexistent' not found. Available: test, linkedin, indeed, github".

---

## 6. Debugging & Observability

### 6.1 Check Structured Logs

Logs are JSON-formatted and should include:
- `@timestamp`: ISO 8601 timestamp
- `level`: INFO, WARNING, ERROR
- `logger`: Module name (e.g., "app.scrapers.linkedin_actor")
- `message`: Human-readable message
- `actor` (if applicable): Actor name
- `duration_ms` (if applicable): Execution time

Example from local logs:
```
2026-06-08T12:34:56.789Z INFO     app.services.actor_framework - Registered actor: linkedin
2026-06-08T12:34:57.100Z INFO     app.scrapers.linkedin_actor:run:49 - Scraping page 1: https://www.linkedin.com/jobs/search/?keywords=...
2026-06-08T12:35:02.234Z INFO     app.scrapers.linkedin_actor:run:80 - LinkedIn actor scraped 12 jobs
```

### 6.2 View CloudWatch Logs (Production)

In AWS Console → CloudWatch → Log Groups → `/aws/ecs/jobtracker-api`:

```
fields @timestamp, @message, actor, duration_ms, error
| filter ispresent(actor)
| stats count() as runs, avg(duration_ms) as avg_duration by actor
```

### 6.3 Inspect S3 Results (Production)

Scraper results are stored in S3 at `s3://jobtracker-documents-{account-id}/scraper-results/{date}/{actor}/{uuid}.jsonl`:

```bash
aws s3 ls s3://jobtracker-documents-245091941294/scraper-results/ --recursive

# Download and inspect a result file
aws s3 cp s3://jobtracker-documents-245091941294/scraper-results/2026-06-08/linkedin/abc123.jsonl -
```

Each line is a JSON object with the scraped job data.

### 6.4 Check Database State

Query the Job table for enrichment status:

```bash
sqlite3 data/app.db "SELECT id, title, source, status, score FROM job LIMIT 10;"
```

Expected columns:
- `id`: Job ID
- `title`: Job title
- `source`: Where scraped from (linkedin, indeed, github)
- `status`: discovered, enriching, enriched, applied
- `score`: 1–10 (0 if not yet scored)

---

## 7. End-to-End Application Flow

### 7.1 Full Auto-Apply Workflow

1. **Discover jobs:**
   ```bash
   curl -X POST http://localhost:8000/api/scheduler/apply-now \
     -H "Content-Type: application/json" \
     -d '{
       "source": "github",
       "min_score": 7,
       "max_applications": 5
     }'
   ```

2. **Check jobs were created:**
   ```bash
   curl 'http://localhost:8000/api/jobs?status=discovered&limit=5' | jq '.items[] | {id, title, company, score}'
   ```

3. **Score jobs (manual or automatic):**
   Each job gets a score 1–10. Jobs with score ≥ 7 are candidates for enrichment.

4. **Enrich high-scoring jobs:**
   ```bash
   curl -X POST http://localhost:8000/api/jobs/enrich-high-scoring \
     -H "Content-Type: application/json" \
     -d '{"score_threshold": 7}'
   ```

5. **Create applications and auto-apply:**
   ```bash
   curl -X POST http://localhost:8000/api/applications \
     -H "Content-Type: application/json" \
     -d '{"job_id": 42}'
   
   # Get application ID from response, then trigger auto-apply
   curl -X POST http://localhost:8000/api/auto-apply/full/{application_id} \
     -H "Content-Type: application/json"
   ```

6. **Monitor via WebSocket:**
   Open browser dev tools and connect to:
   ```
   ws://localhost:8000/api/automation/ws/{session_id}
   ```
   to see real-time screenshots and status updates.

---

## 8. Performance Benchmarks

Target metrics for a healthy Phase 5 deployment:

| Metric | Target | Notes |
|---|---|---|
| Actor initialization time | < 100ms | Per actor |
| Job scrape (single page) | 2–5s | Playwright + Cerebras latency |
| Enrichment pipeline (10 jobs) | < 30s | Depends on actor + AI latency |
| Auto-apply (form fill + submit) | 10–30s | Depends on ATS complexity |
| API response time (p95) | < 2s | Excluding long-running operations |
| Memory (idle) | < 256 MB | Container allocated 1 GB |
| Memory (during scrape) | < 512 MB | Spike under load |
| CPU (idle) | < 10% | Single core, multi-process OK |
| CPU (during scrape) | < 80% | Spike during Playwright/Cerebras |

To verify:

```bash
# Local memory/CPU check (macOS/Linux)
ps aux | grep uvicorn

# Kubernetes (production)
kubectl top pods -n default | grep jobtracker
```

---

## 9. Common Issues & Troubleshooting

### Issue: Actor not registered

**Symptom:** `Actor 'linkedin' not found` when calling scraper endpoint.

**Root cause:** Actor registration failed during startup.

**Fix:**
1. Check logs for startup errors: `grep -i "actor init error" logs.txt`
2. Verify all actor classes are imported in `main.py`
3. Restart the API service
4. Confirm health check shows `db_initialized: true`

### Issue: Playwright browser timeout

**Symptom:** `TimeoutError: page.goto: Timeout 30000ms exceeded.`

**Root cause:** Target website slow or blocking Playwright.

**Fix:**
1. Increase timeout in actor config: `"timeout": 60000` (ms)
2. Check if site is blocking headless browsers (user-agent headers may help)
3. For LinkedIn/Indeed: wait 1 hour and retry (IP ban)

### Issue: Cerebras API rate limit

**Symptom:** `429 Too Many Requests` from Cerebras API.

**Root cause:** Too many concurrent extraction calls.

**Fix:**
1. Reduce `max_pages` or `max_results` in actor config
2. Increase rate limit delays in actor code (currently 0.5s between fetches)
3. Check Cerebras quota: `curl -H "Authorization: Bearer ${CEREBRAS_API_KEY}" https://api.cerebras.ai/account/usage`

### Issue: Database locked

**Symptom:** `sqlite3.OperationalError: database is locked`

**Root cause:** Multiple processes writing to SQLite simultaneously.

**Fix:**
1. For production: switch to PostgreSQL (already configured in RDS)
2. For local dev: stop all other backend instances
3. Check: `lsof | grep app.db` to find process holding lock

---

## 10. Deployment Verification Checklist

Before marking Phase 5 as production-ready:

- [ ] All 4 actors register successfully on startup (check CloudWatch logs)
- [ ] TestActor returns mock data consistently
- [ ] LinkedIn scraper fetches real jobs with Cerebras extraction
- [ ] Indeed scraper fetches real jobs
- [ ] GitHub scraper fetches real jobs
- [ ] Job enrichment endpoint processes high-scoring jobs (status changes to "enriched")
- [ ] Rate limiting (0.5s delays) prevents IP bans (monitor via logs)
- [ ] Retry logic handles transient failures (1s exponential backoff)
- [ ] Auto-apply form filling detects and populates form fields
- [ ] WebSocket broadcasts screenshots and status in real-time
- [ ] Dashboard metrics aggregate enrichment and application counts correctly
- [ ] CloudWatch logs capture all actor executions with structured format
- [ ] S3 stores result JSONLs with correct schema
- [ ] Memory stays below 512 MB during concurrent scrapes
- [ ] API responds within 2s for non-long-running endpoints

---

## 11. Next Steps

Once Phase 5 testing is complete:

1. **Phase 5.1 (Monitoring):** Set up CloudWatch alarms for actor failures, timeout spikes
2. **Phase 6 (Email Tracking):** Integrate email parsing for interview invitations
3. **Phase 7 (Niche Detection):** Implement ML-based job category detection
4. **Feedback Loop:** Use application success/rejection data to retrain job scorer

---

**Last updated:** 2026-06-08  
**Author:** Mason  
**Status:** Production-ready Phase 5
