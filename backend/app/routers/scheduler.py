"""
Automated job application scheduler endpoint.
Allows setting up criteria for automatic applications.
"""
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List

from ..database import get_db
from ..services.auto_scheduler import apply_to_matching_jobs

router = APIRouter(prefix="/api/scheduler", tags=["scheduler"])


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
