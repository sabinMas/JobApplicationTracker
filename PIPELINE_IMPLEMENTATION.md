# Pipeline Visualizer & Review Gate Implementation

## Overview

This document describes the new pipeline visualization system with discovery limits and a mandatory human review gate before job applications are submitted.

## Key Features

### 1. **Discovery Limits**
- Jobs are now limited to **50 per discovery run** (configurable via `SearchPreferences.max_jobs_per_discovery_run`)
- Prevents overwhelming the backend with thousands of jobs
- Duplicate prevention: Uses `DiscoveredJobURL` table to track and skip previously discovered URLs
- Safeguard against re-discovering the same jobs on every run

### 2. **Pipeline Stages**
Each job progresses through these stages:

1. **discovered** - New job found by scraper
2. **scored** - Job has been scored by AI (1-10 fit score)
3. **enriched** - Additional details scraped and added
4. **prepared** - Resume and cover letter tailored for the job
5. **review** - **MANDATORY** - Waiting for human approval before submission
6. **submitted** - Application has been sent to the company
7. **skipped** - Job was rejected (either by AI or human)

### 3. **Mandatory Review Gate**
- All jobs with score ≥ 8 and recommendation "SUBMIT" reach the **review** stage
- Human must review: Job details, AI score reasoning, Tailored resume, Tailored cover letter
- Options: **Approve & Submit**, **Reject**, or **Edit & Submit**
- This ensures AI applications are honest, clean, and appropriate

### 4. **Database Changes**

#### New Table: `DiscoveredJobURL`
```sql
CREATE TABLE discovered_job_urls (
  id SERIAL PRIMARY KEY,
  job_url VARCHAR(1000) UNIQUE NOT NULL,
  source VARCHAR(50),
  discovered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  job_id INTEGER FK -> jobs.id
)
```

#### Updated `SearchPreferences`
- `max_jobs_per_discovery_run` (default: 50)
- `skip_previously_discovered` (default: true)

#### Updated `Job` Table
- `pipeline_stage`: VARCHAR(50) - current stage of the job
- `pipeline_data`: JSON - metadata for each stage
- `enriched_at`: TIMESTAMP - when enrichment completed
- `enrichment_data`: TEXT - enrichment details

## API Endpoints

### Pipeline Visualization

**GET /api/pipeline-visualizer/jobs**
- Get jobs grouped by pipeline stage
- Query params:
  - `stage` (optional): Filter to specific stage
  - `limit_per_stage`: Max jobs per stage (default 50)
- Returns job counts and full job details by stage

**GET /api/pipeline-visualizer/stage-stats**
- Get count of jobs in each stage
- Returns: `{discovered: N, scored: N, enriched: N, prepared: N, review: N, submitted: N, skipped: N}`

**GET /api/pipeline-visualizer/stats**
- Comprehensive pipeline statistics including bottlenecks
- Returns: Total jobs, by_stage counts, bottlenecks (stages with >20 jobs)

### Review Gate

**GET /api/pipeline-visualizer/jobs-for-review**
- Get all applications awaiting human review
- Query params:
  - `skip`: Pagination offset
  - `limit`: Number of jobs (default 10, max 50)
- Returns list of jobs in "review" stage

**GET /api/pipeline-visualizer/application/{application_id}/full-review**
- Get complete application data for review
- Returns:
  ```json
  {
    "application_id": 123,
    "application_status": "ready_for_review",
    "job": {
      "id": 456,
      "title": "Backend Engineer",
      "company": "Company Name",
      "description": "Full job description",
      "requirements": "Job requirements",
      "score": 9,
      "score_reasoning": "Excellent fit because...",
      "score_strengths": ["matches skill X", "aligns with niche Y"],
      "score_concerns": []
    },
    "tailored_resume": {
      "content": "Full resume text (tailored for this job)",
      "path": "/path/to/resume"
    },
    "tailored_cover_letter": {
      "content": "Full cover letter text (tailored for this job)",
      "path": "/path/to/cover_letter"
    }
  }
  ```

**POST /api/pipeline-visualizer/application/{application_id}/approve-and-submit**
- Approve the application and submit it to the company
- Moves job from "review" to "submitted" stage
- Triggers auto-apply submission (Playwright form filling or ATS API)
- Returns: Success/failure status and submission result

**POST /api/pipeline-visualizer/application/{application_id}/reject**
- Reject the application during review
- Moves job from "review" to "skipped" stage
- Query params:
  - `rejection_reason` (optional): Why this job was rejected
- Returns: Confirmation

## Data Flow

### Discovery → Scoring → Review → Submission

```
1. Sync Jobs (max 50 new jobs per run)
   ↓
2. Mark as "discovered"
   ↓ (filtered by DiscoveredJobURL table to prevent duplicates)
   ↓
3. Score Jobs (AI scoring, 1-10 fit)
   ↓
4. Mark as "scored"
   ↓
5. Enrich Jobs (scrape additional details for score ≥ 7)
   ↓
6. Mark as "enriched"
   ↓
7. Prepare Docs (tailor resume & cover letter for score ≥ 8)
   ↓
8. Mark as "prepared"
   ↓
9. Move to "review" stage (MANDATORY human approval)
   ↓
10. Human Reviews Application
    ├─ Approve → "submitted" (auto-apply triggered)
    ├─ Reject → "skipped"
    └─ Edit & Approve → "submitted" (with edited cover letter)
```

## Configuration

### Via SearchPreferences API

**PUT /api/profile/preferences**
```json
{
  "max_jobs_per_discovery_run": 50,
  "skip_previously_discovered": true,
  "min_score_to_apply": 8,
  "auto_submit_enabled": false,
  "daily_application_limit": 10
}
```

## Frontend Integration

### Pipeline Visualizer Component
1. Display stats: Total jobs, counts by stage, bottlenecks
2. Show jobs grouped by stage with filterable cards
3. Click job card → View full details (score, reasoning, source)
4. For jobs in "review" stage: Show expandable review panel with:
   - Job details and AI scoring
   - Side-by-side resume and cover letter preview
   - Approve/Reject/Edit buttons

### Review Panel Component
1. Job title, company, score, score reasoning
2. Full job description
3. AI reasoning: Strengths, concerns, recommendation
4. Tailored resume (scrollable view)
5. Tailored cover letter (scrollable view)
6. Three action buttons:
   - **Approve & Submit** → POST approve-and-submit
   - **Reject** → POST reject (with optional reason)
   - **Edit & Submit** → Inline edit of cover letter, then approve

## Example: First Run

**Before:** User sees 125 jobs discovered, but only 50 scored (confusing)

**After:** 
1. Discovery runs and finds 100+ jobs
2. Limit respected: Only 50 added to DB
3. All 50 move to "scored" stage
4. User sees: 50 discovered, scoring in progress
5. Scoring completes: 45 scored
6. Top 10 (score ≥ 8) move to "review" stage
7. User approves 3, rejects 2, leaves 5 for later
8. 3 approved jobs go to "submitted" stage
9. Dashboard shows clear pipeline progress

## Benefits

✅ **Visibility**: See exactly where each job is in the pipeline
✅ **Control**: Human approves every application before sending
✅ **Efficiency**: Prevents re-discovering same jobs repeatedly
✅ **Safety**: Ensures AI applications are honest and appropriate
✅ **Manageable**: 50 job limit keeps backend from being overwhelmed
✅ **Flexible**: Can review/edit before submission, not locked into auto-apply

## Backend Services Modified

- `app/services/job_sources/manager.py` - Discovery limits + URL deduplication
- `app/services/job_scorer.py` - Updates pipeline_stage to "scored"
- `app/services/job_enrichment.py` - Updates pipeline_stage to "enriched"
- `app/services/pipeline.py` - All jobs go to "review" stage before submission
- `app/routers/pipeline_visualizer.py` - New endpoints for review gate + visualization

## Database Migrations

Migration: `add_pipeline_review_and_discovery_limits.py`
- Adds `DiscoveredJobURL` table
- Adds columns to `SearchPreferences`: max_jobs_per_discovery_run, skip_previously_discovered
- Adds columns to `Job`: pipeline_stage, pipeline_data, enriched_at, enrichment_data

Applied with: `alembic upgrade add_pipeline_review`

## Next Steps

1. Frontend: Build pipeline visualizer component
2. Frontend: Build review panel with job + resume + cover letter
3. Frontend: Test approve/reject/edit flows
4. Test discovery limit with real job sources
5. Monitor duplicate prevention in production
