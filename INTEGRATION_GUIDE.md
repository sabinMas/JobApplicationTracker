# Integration Guide: Pipeline Visualizer with Automation Service

This guide shows how to update your existing automation service to use the new pipeline stage tracking and mandatory review gate.

## Current Flow (Before)

```
Job Discovery → Scoring → Enrichment → Document Prep → AUTO SUBMIT
```

## New Flow (After)

```
Job Discovery → Scoring → Enrichment → Document Prep → REVIEW GATE → SUBMIT
                         (Human Approval Required)
```

## Required Changes

### 1. Update Job Discovery Service

**File:** `backend/app/routers/scraper.py` or equivalent

When a job is discovered, **set pipeline_stage to "discovered":**

```python
from ..models import Job
from ..database import get_db
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

async def save_discovered_job(db: AsyncSession, job_data: dict):
    job = Job(
        title=job_data['title'],
        company=job_data['company'],
        # ... other fields ...
        pipeline_stage="discovered",  # ← NEW: Set initial stage
        created_at=datetime.now(timezone.utc)
    )
    db.add(job)
    await db.commit()
    return job
```

### 2. Update Scoring Service

**File:** `backend/app/routers/auto_apply_scored.py`

After scoring, **move job to "scored" stage and update pipeline:**

```python
from ..routers.pipeline_visualizer import router as pipeline_router
from ..schemas import PipelineStageUpdate

async def score_and_store(db: AsyncSession, job: Job):
    """Score job and update pipeline stage"""
    
    # Existing scoring logic
    score = await job_scorer.score_job(job)
    job.score = score['score']
    job.score_reasoning = score['reasoning']
    job.score_strengths = score['strengths']
    job.score_concerns = score['concerns']
    job.scored_at = datetime.now(timezone.utc)
    
    # ← NEW: Move to "scored" stage
    job.pipeline_stage = "scored"
    job.pipeline_data = {
        'score_details': {
            'reasoning': score['reasoning'],
            'strengths': score['strengths'],
            'concerns': score['concerns'],
        }
    }
    
    await db.commit()
```

### 3. Update Enrichment Service

**File:** `backend/app/routers/job_enrichment.py`

After enrichment, **move job to "enriched" stage:**

```python
async def enrich_job(db: AsyncSession, job: Job):
    """Enrich job details with AI analysis"""
    
    # Existing enrichment logic
    enrichment = await ai_service.enrich_job(job)
    
    job.enrichment_data = enrichment['analysis']
    job.enriched_at = datetime.now(timezone.utc)
    
    # ← NEW: Move to "enriched" stage
    job.pipeline_stage = "enriched"
    job.pipeline_data = job.pipeline_data or {}
    job.pipeline_data['enrichment'] = enrichment
    
    await db.commit()
```

### 4. Update Document Preparation Service

**File:** `backend/app/routers/ai.py` (tailor endpoint)

After generating tailored documents, **move job to "prepared" and then "review":**

```python
async def tailor_documents(db: AsyncSession, job_id: int):
    """Generate tailored resume and cover letter"""
    
    job = await db.get(Job, job_id)
    profile = await get_profile(db)
    
    # Existing tailor logic
    cover_letter = await ai_service.generate_cover_letter(job, profile)
    resume_id = await document_service.create_tailored_resume(job_id, profile)
    cover_letter_id = await document_service.create_document(
        job_id, 'cover_letter', cover_letter
    )
    
    # Create application record
    application = Application(
        job_id=job_id,
        tailored_resume_id=resume_id,
        tailored_cover_letter_id=cover_letter_id,
        status="pending"
    )
    db.add(application)
    
    # ← NEW: Store generated cover letter in pipeline_data and move to "review"
    job.pipeline_stage = "review"  # HALT HERE - Wait for human review
    job.pipeline_data = job.pipeline_data or {}
    job.pipeline_data['generated_cover_letter'] = cover_letter
    job.pipeline_data['application_id'] = application.id
    
    await db.commit()
```

### 5. Handle Review Gate Decision

**File:** `backend/app/routers/pipeline_visualizer.py` (already implemented)

When user approves from frontend, the `review_job` endpoint handles:

```python
@router.post("/review-job")
async def review_job(request: JobReviewRequest, db: AsyncSession = Depends(get_db)):
    """
    User action on job review:
    - "approve" → Move to "submitted" stage (ready for submission service)
    - "reject" → Move to "skipped" stage
    - "edit" → Save edited cover letter, move to "prepared" stage
    """
    job = await db.get(Job, request.job_id)
    
    if request.action == "approve":
        job.pipeline_stage = "submitted"  # Ready to submit
    elif request.action == "reject":
        job.pipeline_stage = "skipped"    # Don't submit
    elif request.action == "edit":
        job.pipeline_stage = "prepared"   # Will review again
        job.pipeline_data['edited_cover_letter'] = request.edited_cover_letter
    
    await db.commit()
```

### 6. Update Submission Service

**File:** `backend/app/routers/auto_apply.py`

**CRITICAL:** Only submit jobs in "submitted" stage (not "review"):

```python
async def get_applications_to_submit(db: AsyncSession):
    """Get jobs ready for submission (in 'submitted' pipeline stage)"""
    
    result = await db.execute(
        select(Job)
        .join(Application)
        .where(
            (Job.pipeline_stage == "submitted") &  # ← ONLY this stage
            (Application.status == "pending")
        )
        .order_by(Job.score.desc())
    )
    return result.scalars().all()

async def submit_applications():
    """Main submission loop"""
    
    for job in await get_applications_to_submit(db):
        try:
            # Submit to ATS
            result = await auto_apply_service.run_full_auto_apply(db, job.applications[0].id)
            
            if result['status'] == 'success':
                job.pipeline_stage = "submitted"  # Keep tracking
                job.applications[0].status = "applied"
                job.applications[0].applied_date = datetime.now(timezone.utc)
        except Exception as e:
            logger.error(f"Failed to submit job {job.id}: {e}")
            job.pipeline_stage = "prepared"  # Revert for retry
```

## Discovery Limits Implementation

### Respect max_jobs_per_discovery_run

**File:** `backend/app/routers/scraper.py`

```python
async def discover_jobs(db: AsyncSession, query: str):
    """Discover jobs with limit from preferences"""
    
    prefs = await db.get(SearchPreferences, 1)
    max_discovery = prefs.max_jobs_per_discovery_run or 25
    
    discovered_count = 0
    jobs = []
    
    for source in job_sources:
        if discovered_count >= max_discovery:
            logger.info(f"Hit discovery limit: {discovered_count}/{max_discovery}")
            break
        
        batch = await source.search(query)
        for job_data in batch:
            if discovered_count >= max_discovery:
                break
            
            # Save job with "discovered" stage
            job = await save_discovered_job(db, job_data)
            jobs.append(job)
            discovered_count += 1
    
    return jobs
```

### Respect max_jobs_to_score_per_run and score_batch_size

**File:** `backend/app/routers/auto_apply_scored.py`

```python
async def score_all_jobs(
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
):
    """Score jobs respecting discovery limits"""
    
    prefs = await db.get(SearchPreferences, 1)
    max_to_score = prefs.max_jobs_to_score_per_run or 25
    batch_size = prefs.score_batch_size or 5
    
    # Get unscored jobs, limit to max_to_score
    unscored_jobs = await db.execute(
        select(Job)
        .where(
            (Job.score.is_(None)) &
            (Job.pipeline_stage == "discovered")
        )
        .order_by(Job.created_at.desc())
        .limit(min(limit, max_to_score))  # ← Apply limit
    )
    jobs = unscored_jobs.scalars().all()
    
    # Score in batches to prevent API overload
    for i in range(0, len(jobs), batch_size):
        batch = jobs[i:i+batch_size]
        
        # Score batch concurrently
        tasks = [
            score_and_store(db, job)
            for job in batch
        ]
        await asyncio.gather(*tasks)
    
    return {
        'jobs_scored': len(jobs),
        'batch_size': batch_size,
        'discovery_limit_applied': max_to_score,
    }
```

## Configuration in Preferences

Users configure limits in Settings → Search Preferences:

```
Discovery Limits
├── Max Jobs Per Discovery Run: 25
├── Max Jobs to Score Per Run: 25
└── Scoring Batch Size: 5

Recommended values to avoid timeouts:
- Prevent 504 Gateway Timeout errors
- Keep scoring API calls manageable
- Allow time for enrichment without overwhelm
```

## Testing the Integration

### 1. Test Pipeline Stage Progression

```bash
# Get initial pipeline state
curl http://localhost:8000/api/pipeline-visualizer/jobs

# Should show jobs in "discovered" stage
```

### 2. Test Scoring Stage

```bash
# Trigger scoring
curl -X POST http://localhost:8000/api/auto-apply-scored/score-jobs

# Check pipeline - should show jobs in "scored" stage
curl http://localhost:8000/api/pipeline-visualizer/jobs
```

### 3. Test Review Gate

```bash
# Get jobs for review
curl http://localhost:8000/api/pipeline-visualizer/jobs-for-review

# Should show jobs in "review" stage
```

### 4. Test Human Approval

```bash
# User approves a job from frontend (via JobReviewGate component)
curl -X POST http://localhost:8000/api/pipeline-visualizer/review-job \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": 123,
    "action": "approve"
  }'

# Check pipeline - job should move to "submitted" stage
curl http://localhost:8000/api/pipeline-visualizer/jobs
```

## Key Points

1. **Pipeline stages are sequential** - Jobs move through stages in order
2. **Review gate is mandatory** - No jobs bypass human approval
3. **Discovery limits prevent timeouts** - Configure for your infrastructure
4. **Real-time UI updates** - Frontend polls every 5 seconds
5. **Editable cover letters** - Users can edit before submission
6. **Complete audit trail** - All stages tracked in pipeline_data

## Database Migration

Run the provided migration to add pipeline tracking fields:

```bash
cd backend
alembic upgrade head
```

This adds:
- `pipeline_stage` column to jobs table
- `pipeline_data` JSON column for stage-specific data
- `enriched_at`, `enrichment_data` columns
- Discovery limit columns to search_preferences

## Monitoring

Track pipeline health via the stats endpoint:

```bash
curl http://localhost:8000/api/pipeline-visualizer/stats

# Response:
{
  "total_jobs": 150,
  "by_stage": {
    "discovered": 45,
    "scored": 30,
    "enriched": 25,
    "prepared": 20,
    "review": 15,  # ← Jobs awaiting human review
    "submitted": 10,
    "skipped": 5
  },
  "bottlenecks": [
    {"stage": "review", "count": 15}  # User has 15 pending reviews
  ]
}
```

Use this to identify bottlenecks and adjust discovery limits if needed.
