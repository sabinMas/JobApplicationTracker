# Mini-Apify: Scraper Actor Framework

JobApplicationTracker now has a pluggable, actor-based scraping system. Think of it like a simplified Apify — register scrapers ("actors"), trigger runs via API, get results in S3.

## Quick Start

### 1. List Available Actors

```bash
curl http://3.238.37.105:8000/api/scraper/actors
```

Response:
```json
[
  {
    "name": "linkedin",
    "display_name": "LinkedIn",
    "description": "Scrapes LinkedIn for jobs",
    "input_schema": {}
  }
]
```

### 2. Launch a Scraper Run

```bash
curl -X POST http://3.238.37.105:8000/api/scraper/run \
  -H "Content-Type: application/json" \
  -d '{
    "actor_name": "linkedin",
    "run_name": "Q2 2026 Tech Jobs",
    "input_config": {
      "query": "software engineer",
      "location": "United States",
      "max_pages": 2
    },
    "webhook_url": "https://your-domain.com/webhook"
  }'
```

Response:
```json
{
  "id": 42,
  "actor_name": "linkedin",
  "run_name": "Q2 2026 Tech Jobs",
  "status": "pending",
  "items_scraped": 0,
  "created_at": "2026-06-08T19:30:00Z"
}
```

The run is now enqueued to SQS. The ECS worker will pick it up and execute it.

### 3. Monitor Run Status

```bash
curl http://3.238.37.105:8000/api/scraper/run/42
```

Response (while running):
```json
{
  "id": 42,
  "actor_name": "linkedin",
  "status": "running",
  "started_at": "2026-06-08T19:31:00Z",
  "items_scraped": 0
}
```

Response (after completion):
```json
{
  "id": 42,
  "actor_name": "linkedin",
  "status": "success",
  "started_at": "2026-06-08T19:31:00Z",
  "finished_at": "2026-06-08T19:45:00Z",
  "items_scraped": 47,
  "dataset_id": 5
}
```

### 4. Access Results

```bash
curl http://3.238.37.105:8000/api/scraper/dataset/5
```

Response:
```json
{
  "id": 5,
  "s3_bucket": "jobtracker-documents-245091941294",
  "s3_key": "runs/linkedin/42/results.jsonl",
  "item_count": 47,
  "s3_url": "s3://jobtracker-documents-245091941294/runs/linkedin/42/results.jsonl"
}
```

Download and parse the JSONL file from S3 to get job listings.

## Creating Custom Actors

### Step 1: Extend the Actor Base Class

Create `backend/app/scrapers/indeed_actor.py`:

```python
from app.services.actor_framework import Actor
from app.services.playwright_service import PlaywrightService
import logging

logger = logging.getLogger(__name__)

class IndeedActor(Actor):
    """Scrapes Indeed jobs."""

    name = "indeed"

    async def run(self, config: dict) -> list:
        """
        Execute the scraper.
        
        Config:
        {
            "query": "python developer",
            "location": "remote",
            "max_results": 100
        }
        """
        query = config.get("query", "")
        location = config.get("location", "")
        max_results = config.get("max_results", 50)

        items = []
        pw = PlaywrightService()

        try:
            url = f"https://indeed.com/jobs?q={query}&l={location}"
            logger.info(f"Scraping: {url}")

            html = await pw.fetch_page(url, timeout=30000)
            # Parse HTML, extract jobs
            # ... custom parsing logic ...

            return items
        finally:
            await pw.close()
```

### Step 2: Register the Actor

Update `backend/app/main.py`:

```python
from .scrapers.indeed_actor import IndeedActor

def _init_actors():
    actor_registry.register(LinkedInActor())
    actor_registry.register(IndeedActor())  # Add this
    logger.info("Actors initialized")
```

### Step 3: Database

The actor is automatically registered in the `actors` table on startup. No schema changes needed.

## Architecture

```
POST /api/scraper/run {actor: "linkedin", config: {...}}
    ↓
Create ScraperRun record (status=pending)
    ↓
Enqueue to SQS
    ↓
ECS Worker picks up message
    ↓
Load actor from registry
    ↓
Execute actor.run(config) → List[dict]
    ↓
Write results to S3 as JSONL
    ↓
Create Dataset record
    ↓
Update ScraperRun (status=success, items_scraped=N)
    ↓
Call webhook_url (if provided)
```

## WebHooks

When a run completes, we POST to your webhook:

```
POST <webhook_url>
{
  "run_id": 42,
  "status": "success",
  "items_count": 47
}
```

Or on failure:

```
{
  "run_id": 42,
  "status": "failed",
  "error": "Timeout waiting for page load"
}
```

Use webhooks to integrate with EventBridge, Lambda, or external pipelines.

## Querying Runs

```bash
# List all runs
curl http://3.238.37.105:8000/api/scraper/runs

# Filter by actor
curl http://3.238.37.105:8000/api/scraper/runs?actor_name=linkedin

# Filter by status
curl http://3.238.37.105:8000/api/scraper/runs?status=success&limit=10
```

## Best Practices

1. **Rate Limiting**: Add delays between requests in your actor to respect target site rate limits
2. **Retries**: Failed runs stay in SQS queue and auto-retry
3. **Timeout**: Each run has a 5-minute visibility timeout. Keep actors under that
4. **Webhook Idempotency**: Assume webhooks may be called multiple times; make your handlers idempotent
5. **Result Size**: JSONL results are streamed to S3. No size limit, but very large datasets (100k+ items) may need pagination

## Hooking into AgentCore Scoring

When AgentCore scores a job ≥7, trigger a scraper run:

```python
# In your job scoring pipeline
if job.score >= 7:
    # POST to /api/scraper/run to gather more data
    run = await enqueue_actor_run(
        db,
        actor_name="linkedin",
        input_config={"query": job.title, "location": job.location},
        webhook_url="https://your-api.com/job-enrichment-webhook"
    )
```

Then in your webhook handler, enrich the job with the scraped data and re-score.
