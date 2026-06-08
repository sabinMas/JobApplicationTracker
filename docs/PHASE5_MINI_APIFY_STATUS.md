# Phase 5: Mini-Apify Scraper Framework - Current Status

**Date**: June 8, 2026  
**Status**: ✅ Core Framework Complete, Ready for Testing

## What's Working

### Architecture
- **ECS Fargate Cluster**: `jobtracker-cluster` with 2 services
  - `api-service`: 1 running task (FastAPI + gunicorn, 4 workers)
  - `worker-service`: 1 running task (SQS poller for actor runs)
- **Docker Images**: Built and pushed to ECR
  - `jobtracker-api:latest`: FastAPI with all routers
  - `jobtracker-worker:latest`: ECS worker with Playwright support
- **SQS Queue**: `jobtracker-scraper-runs` for message dispatch
- **Database**: SQLAlchemy models ready (ScraperRun, Dataset, Actor)

### Actor Framework
- **Base Class**: `Actor` with async run() and hooks
- **Registry**: Global `actor_registry` for discovery
- **REST API**: `/api/scraper/*` endpoints
  - `GET /api/scraper/actors` - List registered actors
  - `POST /api/scraper/run` - Create and enqueue run
  - `GET /api/scraper/run/{id}` - Get run status
  - `GET /api/scraper/runs` - List runs with filtering
  - `GET /api/scraper/dataset/{id}` - Get results metadata

### Test Actor
- **TestActor**: Simple actor that generates mock job data
  - Registered and working
  - Generates N test jobs on request
  - Validates framework end-to-end

### API Health
- ✅ All routers loaded successfully
- ✅ Database initialized
- ✅ Job sync scheduler ready
- ✅ Actors registered
- ✅ Listening on 0.0.0.0:8000

## Known Issues

### Critical Blockers
1. **PlaywrightService Class Missing**
   - LinkedInActor is disabled (commented out in main.py)
   - Placeholder class added but not functional
   - Need full async browser automation implementation

2. **API Not Publicly Accessible**
   - Running on private VPC IP (172.31.1.189)
   - No ALB or API Gateway configured
   - Blocking external testing and integration

### Minor Issues
1. CloudWatch logging permission error (non-critical)
   - API still runs, just can't write to Lambda log group
   - Doesn't affect functionality

## Next Steps (Priority Order)

### 1. Fix PlaywrightService (Enables Real Scrapers)
```python
# Need to implement in backend/app/services/playwright_service.py
class PlaywrightService:
    async def fetch_page(url: str, timeout: int) -> str
    async def close()
```

### 2. Set Up API Gateway or ALB
- Option A: Use existing Lambda function URL with API Gateway
- Option B: Create ALB for ECS services (better long-term)
- Unblocks external testing and Vercel frontend integration

### 3. Test Framework End-to-End
```bash
# Test actor list
curl https://api.example.com/api/scraper/actors

# Launch test run
curl -X POST https://api.example.com/api/scraper/run \
  -H "Content-Type: application/json" \
  -d '{
    "actor_name": "test",
    "run_name": "test-run-1",
    "input_config": {"count": 5}
  }'
```

### 4. Implement Real Scrapers
- LinkedInActor (fixed PlaywrightService)
- IndeedActor
- GitHubJobsActor
- AngelListActor

### 5. EventBridge Integration
- Listen for jobs scored ≥ 7 from AgentCore
- Auto-trigger scraper runs for high-value matches
- Enrich job data with scraped details

### 6. Worker Auto-Scaling
- Set up target tracking scaling policy on SQS queue depth
- Configure min/max task counts for worker service

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                        Vercel Frontend                         │
│                  (jobapptracker-n60pbf6ah)                     │
└──────────────────────────┬──────────────────────────────────────┘
                           │ /api/* requests
                           ▼
                    [API Gateway/ALB]
                    (Public endpoint)
                           │
        ┌──────────────────┴──────────────────┐
        ▼                                      ▼
   [ECS Fargate - API Service]      [RDS PostgreSQL]
   - FastAPI + gunicorn                (Job models)
   - 4 uvicorn workers              (ScraperRun, Dataset)
   - Scraper router
   - Actor registry
        │
        ├─ POST /api/scraper/run
        │  └─> Create ScraperRun
        │  └─> Enqueue to SQS
        │
        └─ GET /api/scraper/actors
           └─> List registered scrapers

     ┌──────────────────────┐
     │   SQS Queue          │
     │ (jobtracker-scraper) │
     └──────────────────────┘
           ▲ (enqueue)
           │
           │ (poll)
           ▼
    [ECS Fargate - Worker Service]
    - SQS poller (worker_main.py)
    - Actor executor (actor_runner.py)
    - Playwright browser automation
    - Result aggregator
           │
           └─> Writes to S3 (JSONL)
               └─> Updates ScraperRun status
               └─> Calls webhook
```

## Files Modified This Session

- `Dockerfile.api` - ECS container for API
- `Dockerfile.worker` - ECS container for worker
- `backend/app/main.py` - Register TestActor
- `backend/app/routers/scraper.py` - Actor management API
- `backend/app/services/actor_framework.py` - Base framework (created prior)
- `backend/app/services/actor_runner.py` - Run executor
- `backend/app/scrapers/test_actor.py` - Test implementation
- `docs/scraper-api-guide.md` - Usage documentation

## To Resume

Next session should:
1. Implement PlaywrightService class
2. Set up API Gateway for public access
3. Test scraper endpoints with TestActor
4. Implement LinkedIn scraper
5. Connect to EventBridge for AgentCore integration
