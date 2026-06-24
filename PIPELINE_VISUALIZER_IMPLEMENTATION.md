# Pipeline Visualizer & Review Gate Implementation

## Overview

This implementation adds three critical features to the Job Application Tracker:

1. **Real-time Pipeline Visualizer** - See jobs moving through each stage (discovered → scored → enriched → prepared → review → submitted)
2. **Mandatory Human Review Gate** - Jobs pause before submission, requiring your approval with your resume and cover letter visible
3. **Discovery Limits** - Configurable limits to prevent timeouts and manage workload

## Changes Made

### Backend

#### Database Models (`backend/app/models.py`)

**Job Model - Pipeline Stage Tracking:**
```python
pipeline_stage: String(50)  # discovered/scored/enriched/prepared/review/submitted/skipped
pipeline_data: JSON  # {generated_cover_letter, enrichment_notes, etc}
enriched_at: DateTime
enrichment_data: Text
```

**SearchPreferences Model - Discovery Limits:**
```python
max_jobs_per_discovery_run: Integer = 25  # Stop discovery after N jobs found
max_jobs_to_score_per_run: Integer = 25   # Max scoring batch size
score_batch_size: Integer = 5             # Concurrent scoring limit
```

#### New Router (`backend/app/routers/pipeline_visualizer.py`)

Provides endpoints for:

- **`GET /pipeline-visualizer/jobs`** - Get pipeline visualization with job counts by stage
  - Returns: Job counts per stage + paginated jobs organized by stage
  - Filter by stage if needed
  
- **`GET /pipeline-visualizer/jobs-for-review`** - Get jobs awaiting human review
  - Returns: List of jobs in "review" stage, sorted by score
  - Pagination support (skip, limit)

- **`POST /pipeline-visualizer/review-job`** - Human review action
  - Actions: "approve" (move to submitted), "reject" (move to skipped), "edit" (save edited cover letter, move to prepared)
  - Body: `{ job_id, action, edited_cover_letter? }`

- **`POST /pipeline-visualizer/update-stage/{job_id}`** - Update job pipeline stage
  - Used by automation service to move jobs through stages
  - Can include pipeline_data updates

- **`GET /pipeline-visualizer/stats`** - Pipeline health metrics
  - Returns stage counts and bottleneck analysis

#### Database Migration

New migration file: `backend/alembic/versions/add_pipeline_stage_tracking.py`
- Adds pipeline_stage, pipeline_data, enriched_at, enrichment_data to jobs table
- Adds discovery limit fields to search_preferences table
- Creates index on pipeline_stage for fast queries

#### Updated Main App (`backend/app/main.py`)

- Imported and registered new pipeline_visualizer router

### Frontend

#### New Components

**`frontend/src/components/PipelineVisualizer.tsx`**

Displays real-time job pipeline visualization:
- Grid showing job counts by stage (discovery, scoring, enrichment, preparation, review, submitted)
- Expandable stage cards showing jobs in each stage
- Job detail modal with:
  - Score analysis (reasoning, strengths, concerns)
  - Enrichment notes
  - Source and location info
  - Link to job posting
- Real-time updates via React Query (refetch every 5 seconds)

**`frontend/src/components/JobReviewGate.tsx`**

Mandatory review gate for jobs before submission:
- Progress bar showing current job vs total
- Large card with job title, company, location, score
- Two-column layout showing:
  - Left: Job details, enrichment notes, link to posting
  - Right: Your application materials (resume + generated cover letter)
- Three action buttons:
  - **Skip** - Reject job, move to skipped stage
  - **Review & Edit** - Toggle edit mode for cover letter
  - **Approve & Submit** or **Submit with Changes** - Approve for submission
- Edit mode allows inline cover letter editing
- Real-time updates to show new jobs for review (5-second refetch)

#### Updated Pages

**`frontend/src/pages/Pipeline.tsx`**

Complete redesign with tabbed interface:
- **Review Gate Tab** (default focused) - Shows JobReviewGate component
- **Pipeline Visualizer Tab** - Shows PipelineVisualizer component
- **Run History Tab** - Shows pipeline run history (original functionality)

Features:
- "Run Now" button to trigger pipeline execution
- Real-time job count indicators in tab headers
- Latest run summary card
- Full run history with error details

#### Updated Preferences

**`frontend/src/pages/Preferences.tsx`**

New "Discovery Limits" section:
- **Max Jobs Per Discovery Run** (default: 25) - Stop discovering after this many jobs
- **Max Jobs to Score Per Run** (default: 25) - Max scoring batch size
- **Scoring Batch Size** (default: 5) - Concurrent scoring limit

Includes helpful tooltip:
> Pro Tip: Lower limits = slower but more stable. Start with 25 jobs per discovery and 5 concurrent scoring to avoid timeouts.

#### Updated API

**`frontend/src/api/pipeline.ts`**

New endpoints:
```typescript
getPipelineJobs(stage?: string) // Get pipeline visualization
getJobsForReview(skip = 0, limit = 10) // Get jobs for review
reviewJob(jobId, action, editedCoverLetter?) // Submit review action
getPipelineStats() // Get pipeline health metrics
```

**`frontend/src/api/preferences.ts`**

Updated SearchPreferences interface with discovery limit fields.

**`frontend/src/api/client.ts`**

Added helper:
```typescript
getDocumentContent(id: number) // Get document content
```

#### Updated Schemas

**`backend/app/schemas.py`**

New schemas:
```python
PipelineJobOut  # Job with pipeline stage and review information
PipelineStageUpdate  # Update job pipeline stage
JobReviewRequest  # Review action request
PipelineVisualizerOut  # Pipeline visualization response
SearchPreferencesUpdate  # Added discovery limit fields
```

## Data Flow

### Job Through Pipeline

1. **Discovered** - Job found by scraper/discovery service
2. **Scored** - AI scores job 1-10
3. **Enriched** - AI enriches with analysis/details
4. **Prepared** - Documents tailored for application
5. **Review** ← **YOU REVIEW HERE** - Human approval gate (your resume + auto-generated cover letter shown)
6. **Submitted** - Application submitted to job posting
7. **Skipped** - Job rejected by human or doesn't meet criteria

### Discovery Limits Flow

When running pipeline:
1. Discovery service respects `max_jobs_per_discovery_run` limit
2. Scoring service batches jobs with `max_jobs_to_score_per_run` and `score_batch_size`
3. Jobs in "review" stage pause - waiting for human approval
4. Human reviews job with your resume and generated cover letter visible
5. Can approve, reject, or edit cover letter before approval
6. After approval, submitted to ATS

## Configuration

### Settings → Search Preferences

Users can now configure:
- Discovery limits (prevents timeouts)
- Scoring batch sizes (prevents overwhelming APIs)
- Min score threshold for auto-apply
- Daily application limits

**Recommended defaults:**
- Max jobs per discovery: 25
- Max jobs to score: 25
- Scoring batch size: 5

## Real-time Updates

Both components use React Query with `refetchInterval: 5000` for real-time updates:
- Pipeline visualizer updates every 5 seconds
- Review gate shows new jobs as they become available

## Testing

Frontend compiles without errors:
```
✓ TypeScript: No errors
✓ Pipeline.tsx, PipelineVisualizer.tsx, JobReviewGate.tsx all type-safe
```

Backend code:
```
✓ Python: Syntax valid
✓ Router registered in main.py
✓ Schemas updated
✓ Migration file created
```

## Next Steps

To deploy:

1. **Run database migration:**
   ```bash
   cd backend
   alembic upgrade head
   ```

2. **Test the new endpoints:**
   ```bash
   # Get pipeline visualization
   curl http://localhost:8000/api/pipeline-visualizer/jobs
   
   # Get jobs for review
   curl http://localhost:8000/api/pipeline-visualizer/jobs-for-review
   ```

3. **Update your discovery service** to:
   - Respect `max_jobs_per_discovery_run` limit
   - Move jobs to "scored" stage after scoring
   - Move jobs to "enriched" stage after enrichment
   - Move jobs to "prepared" stage after document generation
   - Move jobs to "review" stage (instead of "submitted")

4. **Update your submission service** to:
   - Only process jobs in "submitted" stage (not "review")
   - Jobs only move to "submitted" when user approves via review gate

## Key Improvements

1. **Visibility** - See exactly which jobs are at which stage
2. **Control** - Human approval before any submission
3. **Confidence** - Review job description + your materials before applying
4. **Stability** - Discovery limits prevent timeouts
5. **Efficiency** - Batch size controls prevent API overwhelm
6. **Transparency** - AI reasoning visible (score, concerns, strengths)

## Human-in-the-Loop

The review gate enforces human oversight at the critical moment - before application submission. This ensures:
- No accidental applications
- Chance to review AI reasoning
- Ability to edit cover letters
- Complete transparency into process
