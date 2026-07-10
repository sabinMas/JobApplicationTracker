"""
Automated job application scheduler endpoint.
Allows setting up criteria for automatic applications and managing job sync schedules.
"""

import asyncio

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from datetime import datetime, timedelta, timezone

from ..database import get_db
from ..models import PipelineRun
from ..schemas import PipelineRunOut
from ..services.auto_scheduler import apply_to_matching_jobs
from ..services.job_sync_scheduler import get_scheduler
from ..services.pipeline import create_pipeline_run, run_pipeline_background
from ..logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/scheduler", tags=["scheduler"])

# Tracks the in-process background task for the currently running pipeline,
# so repeated "Run Now" clicks don't spawn overlapping runs that each hold a
# DB connection for minutes and exhaust the pool.
_pipeline_task: Optional[asyncio.Task] = None

# If a PipelineRun is still "running" past this age, treat it as orphaned
# (e.g. the process restarted mid-run) rather than blocking new runs forever.
STALE_RUN_MINUTES = 20


class JobCriteria(BaseModel):
    """Criteria for automatic job applications"""

    keywords: Optional[List[str]] = None
    location: Optional[List[str]] = None
    min_salary: Optional[int] = None
    max_salary: Optional[int] = None
    job_types: Optional[List[str]] = None
    exclude_companies: Optional[List[str]] = None


class SchedulerConfig(BaseModel):
    """Configuration for the auto-apply scheduler"""

    enabled: bool
    interval_minutes: int = 30
    criteria: JobCriteria


@router.post("/apply-now")
async def apply_to_matching_now(
    criteria: JobCriteria,
    db: AsyncSession = Depends(get_db),
):
    """
    Immediately apply to all jobs matching the given criteria.
    Useful for one-off bulk applications.
    """
    criteria_dict = criteria.model_dump(exclude_none=True)

    results = await apply_to_matching_jobs(db, criteria_dict)

    return {
        "status": "completed",
        "results": results,
        "applied_count": len(results.get("applied", [])),
        "failed_count": len(results.get("failed", [])),
    }


@router.post("/run-pipeline", response_model=PipelineRunOut)
async def trigger_pipeline(db: AsyncSession = Depends(get_db)):
    """
    Kick off the full automation pipeline now:
    discover → score → enrich → tailor → submit/queue-for-review.

    This is the same flow the daily EventBridge schedule triggers. The
    pipeline runs in the background and can take several minutes (it makes
    dozens of sequential AI calls), so this endpoint returns immediately with
    the new PipelineRun (status="running") rather than blocking until
    completion — poll GET /scheduler/pipeline-runs for progress. If a run is
    already in progress, that run is returned instead of starting another.
    """
    global _pipeline_task

    if _pipeline_task is not None and not _pipeline_task.done():
        current = (
            (
                await db.execute(
                    select(PipelineRun)
                    .where(PipelineRun.status == "running")
                    .order_by(PipelineRun.started_at.desc())
                )
            )
            .scalars()
            .first()
        )
        if current:
            return current

    # Clean up any "running" rows orphaned by a crashed/restarted process so
    # they don't block new runs forever.
    stale_cutoff = datetime.now(timezone.utc) - timedelta(minutes=STALE_RUN_MINUTES)
    stale_runs = (
        (await db.execute(select(PipelineRun).where(PipelineRun.status == "running")))
        .scalars()
        .all()
    )
    for stale in stale_runs:
        started = stale.started_at
        if started and started.tzinfo is None:
            started = started.replace(tzinfo=timezone.utc)
        if started and started < stale_cutoff:
            stale.status = "failed"
            stale.finished_at = datetime.now(timezone.utc)
            errors = list(stale.errors or [])
            errors.append(
                {
                    "stage": "pipeline",
                    "message": "Marked failed: exceeded stale-run timeout "
                    f"({STALE_RUN_MINUTES}m), likely interrupted by a restart.",
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )
            stale.errors = errors
    if stale_runs:
        await db.commit()

    run = await create_pipeline_run(trigger="manual")
    _pipeline_task = asyncio.create_task(run_pipeline_background(run.id))
    logger.info(f"Pipeline run {run.id} triggered in background")
    return run


@router.get("/pipeline-runs", response_model=List[PipelineRunOut])
async def list_pipeline_runs(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """Most recent pipeline run summaries (newest first)."""
    from sqlalchemy import select
    from ..models import PipelineRun

    result = await db.execute(
        select(PipelineRun)
        .order_by(PipelineRun.started_at.desc())
        .limit(min(limit, 50))
    )
    return result.scalars().all()


@router.post("/schedule")
async def setup_schedule(
    config: SchedulerConfig,
    db: AsyncSession = Depends(get_db),
):
    """
    Set up automatic job application on a schedule.

    Example request:
    {
        "enabled": true,
        "interval_minutes": 30,
        "criteria": {
            "keywords": ["Python", "Backend"],
            "exclude_companies": ["Company X"],
            "job_types": ["full-time"]
        }
    }
    """
    if not config.enabled:
        return {
            "status": "scheduler_disabled",
            "message": "Auto-apply scheduler is disabled",
        }

    if config.interval_minutes < 5:
        raise HTTPException(
            400,
            "Interval must be at least 5 minutes to avoid rate limiting",
        )

    # TODO: Store scheduler config in database
    # For now, this is a placeholder that returns the config

    return {
        "status": "scheduled",
        "message": "Auto-apply scheduler configured",
        "config": config.model_dump(),
        "note": "This is currently a demonstration. Persistent scheduling requires database storage.",
    }


@router.get("/status")
async def get_scheduler_status():
    """Get the current status of the auto-apply scheduler."""
    return {
        "status": "not_running",
        "message": "Scheduler not yet running. Use /schedule endpoint to configure.",
        "note": "Persistent background jobs require a task queue (e.g., Celery). For now, use /apply-now for immediate bulk applications.",
    }


@router.post("/test")
async def test_criteria(
    criteria: JobCriteria,
    db: AsyncSession = Depends(get_db),
):
    """
    Test criteria without actually applying.
    Returns list of matching jobs.
    """
    from sqlalchemy import select
    from ..models import Job

    query = select(Job).where(Job.status == "discovered")

    # Apply filters
    if criteria.keywords:
        keywords = criteria.keywords
        keyword_filter = Job.description.contains(keywords[0])
        for kw in keywords[1:]:
            keyword_filter = keyword_filter | Job.description.contains(kw)
        query = query.where(keyword_filter)

    if criteria.exclude_companies:
        for company in criteria.exclude_companies:
            query = query.where(Job.company != company)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "matching_jobs": len(jobs),
        "jobs": [
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "salary_range": job.salary_range,
            }
            for job in jobs[:10]  # Return first 10
        ],
        "preview": "Showing first 10 matches" if len(jobs) > 10 else None,
    }


# ============================================================================
# Job Sync Scheduler Endpoints
# ============================================================================


@router.post("/jobs/sync")
async def trigger_job_sync():
    """
    Manually trigger an immediate job sync from all configured sources.

    Returns sync statistics (added, duplicates, errors).
    """
    logger.info("Manual job sync triggered")

    scheduler = get_scheduler()
    if not scheduler:
        logger.warning("Job sync scheduler not initialized")
        raise HTTPException(503, "Job sync scheduler not initialized")

    try:
        result = await scheduler.sync_now()
        return result
    except Exception as e:
        logger.error(f"Job sync failed: {e}", extra_fields={"error": str(e)})
        raise HTTPException(500, f"Job sync failed: {str(e)}")


@router.get("/jobs/config")
async def get_job_sync_config():
    """
    Get current job sync scheduler configuration.

    Returns:
        Scheduler config including interval, last sync time, etc.
    """
    scheduler = get_scheduler()
    if not scheduler:
        return {
            "status": "not_initialized",
            "message": "Job sync scheduler not yet initialized",
        }

    config = scheduler.get_config()
    logger.info("Job sync config retrieved", extra_fields=config)

    return config


class JobSyncConfigUpdate(BaseModel):
    """Update job sync configuration"""

    interval_minutes: Optional[int] = None
    enabled: Optional[bool] = None


@router.put("/jobs/config")
async def update_job_sync_config(config: JobSyncConfigUpdate):
    """
    Update job sync scheduler configuration.

    Args:
        interval_minutes: Sync interval in minutes (minimum 5)
        enabled: Enable/disable scheduler
    """
    scheduler = get_scheduler()
    if not scheduler:
        raise HTTPException(503, "Job sync scheduler not initialized")

    try:
        if config.interval_minutes:
            if config.interval_minutes < 5:
                raise ValueError("Sync interval must be at least 5 minutes")
            scheduler.set_sync_interval(config.interval_minutes)
            logger.info(
                "Job sync interval updated",
                extra_fields={
                    "interval_minutes": config.interval_minutes,
                },
            )

        updated_config = scheduler.get_config()

        return {
            "status": "updated",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "config": updated_config,
        }

    except ValueError as e:
        logger.warning(f"Invalid job sync config: {e}")
        raise HTTPException(400, str(e))
    except Exception as e:
        logger.error(
            f"Failed to update job sync config: {e}", extra_fields={"error": str(e)}
        )
        raise HTTPException(500, f"Failed to update config: {str(e)}")


@router.get("/jobs/status")
async def get_job_sync_status():
    """
    Get current job sync scheduler status.

    Returns:
        Status including whether scheduler is running, last sync time, next sync time.
    """
    scheduler = get_scheduler()
    if not scheduler:
        return {
            "status": "not_initialized",
            "is_running": False,
            "message": "Job sync scheduler not yet initialized",
        }

    config = scheduler.get_config()

    return {
        "status": "ok" if scheduler.is_running else "idle",
        **config,
    }
