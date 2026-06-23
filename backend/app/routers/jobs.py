"""
Jobs management endpoints.

- GET /api/jobs: List jobs
- POST /api/jobs/sync: Sync jobs from all sources
- GET /api/jobs/sources: List configured sources
- POST /api/jobs/sources: Add new job source
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, desc, func
from datetime import datetime, timezone
from typing import Optional

from ..database import get_db
from ..models import Job
from ..services.job_sources import JobSourceManager, RSSJobSource
from ..logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/jobs", tags=["jobs"])

# Global job source manager
job_manager = JobSourceManager()


@router.get("/debug-error", include_in_schema=False)
async def debug_list_jobs_error(
    db: AsyncSession = Depends(get_db),
):
    """Temporary: catch and return the list_jobs exception for remote diagnosis."""
    import traceback as tb_mod

    try:
        result = await list_jobs(skip=0, limit=1, source=None, status=None, db=db)
        return {"ok": True, "sample": result}
    except Exception as e:
        return {
            "error": type(e).__name__,
            "message": str(e),
            "traceback": tb_mod.format_exc(),
        }


@router.get("", include_in_schema=False)
@router.get("/")
async def list_jobs(
    skip: int = 0,
    limit: int = 20,
    source: str = None,
    status: str = None,
    db: AsyncSession = Depends(get_db),
):
    """
    List jobs with pagination and filtering.

    Args:
        skip: Number of jobs to skip
        limit: Maximum number of jobs to return
        source: Filter by job source
        status: Filter by status (discovered, applied, rejected)
    """
    logger.info(
        "Listing jobs",
        extra_fields={
            "skip": skip,
            "limit": limit,
            "source": source,
            "status": status,
        },
    )

    query = select(Job)

    if source:
        query = query.where(Job.source == source)

    if status:
        query = query.where(Job.status == status)

    # Order by created_at descending
    query = query.order_by(desc(Job.created_at))

    # Apply pagination
    query = query.offset(skip).limit(limit)

    result = await db.execute(query)
    jobs = result.scalars().all()

    return {
        "total": len(jobs),
        "skip": skip,
        "limit": limit,
        "jobs": [
            {
                "id": job.id,
                "title": job.title,
                "company": job.company,
                "location": job.location,
                "job_type": job.job_type,
                "source": job.source,
                "status": job.status,
                "apply_url": job.apply_url,
                "posted_date": job.posted_date,
                "created_at": job.created_at.isoformat() if job.created_at else None,
            }
            for job in jobs
        ],
    }


@router.post("/sync")
async def sync_jobs(
    db: AsyncSession = Depends(get_db),
):
    """
    Sync jobs from all configured sources.

    This endpoint:
    1. Fetches jobs from all registered sources in parallel
    2. Deduplicates against existing jobs
    3. Stores new jobs in database

    Returns sync statistics (added, duplicates, errors)
    """
    logger.info("Starting job sync")

    try:
        stats = await job_manager.sync()

        logger.info("Job sync completed", extra_fields=stats)

        return {
            "status": "success",
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "stats": stats,
        }

    except Exception as e:
        logger.error(f"Job sync failed: {e}", extra_fields={"error": str(e)})
        raise HTTPException(500, f"Job sync failed: {str(e)}")


@router.get("/sources")
async def list_sources():
    """List all configured job sources."""
    logger.info("Listing job sources")

    return {
        "sources": [
            {
                "name": name,
                "type": source.__class__.__name__,
            }
            for name, source in job_manager.sources.items()
        ],
        "count": len(job_manager.sources),
    }


@router.post("/sources/rss")
async def add_rss_source(
    feed_url: str,
    name: str = None,
):
    """
    Add a new RSS feed job source.

    Args:
        feed_url: URL to RSS feed
        name: Optional display name (defaults to domain)
    """
    logger.info(
        "Adding RSS job source",
        extra_fields={
            "feed_url": feed_url,
            "name": name,
        },
    )

    try:
        source = RSSJobSource(feed_url, name=name)
        job_manager.add_source(source)

        return {
            "status": "success",
            "source": {
                "name": source.name,
                "feed_url": feed_url,
                "type": "RSS",
            },
        }

    except Exception as e:
        logger.error(f"Failed to add RSS source: {e}", extra_fields={"error": str(e)})
        raise HTTPException(400, f"Failed to add RSS source: {str(e)}")


@router.get("/stats")
async def get_job_stats(
    db: AsyncSession = Depends(get_db),
):
    """Get job statistics by source and status."""
    logger.info("Getting job statistics")

    # Get counts by source
    source_result = await db.execute(
        select(Job.source, func.count(Job.id)).group_by(Job.source)
    )
    by_source = {row[0]: row[1] for row in source_result.fetchall()}

    # Get counts by status
    status_result = await db.execute(
        select(Job.status, func.count(Job.id)).group_by(Job.status)
    )
    by_status = {row[0]: row[1] for row in status_result.fetchall()}

    # Total count
    total_result = await db.execute(select(func.count(Job.id)))
    total = total_result.scalar()

    return {
        "total": total,
        "by_source": by_source,
        "by_status": by_status,
    }


@router.get("/{job_id}")
async def get_job(
    job_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Get details of a specific job."""
    logger.info("Getting job details", extra_fields={"job_id": job_id})

    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()

    if not job:
        logger.warning("Job not found", extra_fields={"job_id": job_id})
        raise HTTPException(404, "Job not found")

    return {
        "id": job.id,
        "title": job.title,
        "company": job.company,
        "location": job.location,
        "job_type": job.job_type,
        "description": job.description,
        "requirements": job.requirements,
        "salary_range": job.salary_range,
        "source": job.source,
        "source_url": job.source_url,
        "apply_url": job.apply_url,
        "posted_date": job.posted_date,
        "status": job.status,
        "notes": job.notes,
        "created_at": job.created_at.isoformat() if job.created_at else None,
    }


@router.post("/sources/github")
async def add_github_source(
    access_token: Optional[str] = None,
):
    """
    Add GitHub Jobs API source (no authentication required, but optional for rate limit increases).

    Args:
        access_token: Optional GitHub personal access token (for authenticated requests)

    Returns:
        Confirmation that GitHub source was added
    """
    logger.info(
        "Adding GitHub Jobs source",
        extra_fields={
            "has_token": access_token is not None,
        },
    )

    try:
        from ..services.job_sources import GitHubJobSource

        source = GitHubJobSource(access_token=access_token)
        job_manager.add_source(source)

        logger.info(
            "GitHub source configured",
            extra_fields={
                "source": "GitHub Jobs",
                "authenticated": access_token is not None,
            },
        )

        return {
            "status": "success",
            "source": {
                "name": source.name,
                "type": "GitHub Jobs API",
                "authenticated": access_token is not None,
                "api_url": source.api_url,
                "note": "GitHub Jobs API is deprecated but still functional",
            },
        }

    except Exception as e:
        logger.error(
            f"Failed to add GitHub source: {e}", extra_fields={"error": str(e)}
        )
        raise HTTPException(400, f"Failed to add GitHub source: {str(e)}")


@router.post("/sources/linkedin")
async def add_linkedin_source(
    client_id: str,
    client_secret: str,
):
    """
    Add LinkedIn API job source.

    Requires OAuth 2.0 credentials:
    - client_id: LinkedIn app client ID
    - client_secret: LinkedIn app client secret

    Args:
        client_id: LinkedIn OAuth client ID
        client_secret: LinkedIn OAuth client secret

    Returns:
        Confirmation that LinkedIn source was added
    """
    logger.info(
        "Adding LinkedIn job source",
        extra_fields={
            "client_id_prefix": client_id[:8] if client_id else None,
        },
    )

    try:
        from ..services.job_sources import LinkedInJobSource

        if not client_id or not client_secret:
            raise ValueError("client_id and client_secret are required")

        source = LinkedInJobSource(
            client_id=client_id,
            client_secret=client_secret,
        )
        job_manager.add_source(source)

        logger.info(
            "LinkedIn source configured",
            extra_fields={
                "source": "LinkedIn",
                "configured": source.is_configured,
            },
        )

        return {
            "status": "success",
            "source": {
                "name": source.name,
                "type": "LinkedIn API",
                "configured": source.is_configured,
                "message": "LinkedIn source added. Note: LinkedIn standard API has limitations. Consider using Recruiter API or web scraping.",
            },
        }

    except Exception as e:
        logger.error(
            f"Failed to add LinkedIn source: {e}", extra_fields={"error": str(e)}
        )
        raise HTTPException(400, f"Failed to add LinkedIn source: {str(e)}")


@router.post("/sources/angellist")
async def add_angellist_source(
    api_key: str,
):
    """
    Add Angel List (Wellfound) API job source.

    Requires:
    - api_key: Angel List / Wellfound API key

    Args:
        api_key: Angel List API key

    Returns:
        Confirmation that Angel List source was added
    """
    logger.info("Adding Angel List job source")

    try:
        from ..services.job_sources import AngelListJobSource

        if not api_key:
            raise ValueError("api_key is required")

        source = AngelListJobSource(api_key=api_key)
        job_manager.add_source(source)

        return {
            "status": "success",
            "source": {
                "name": source.name,
                "type": "Angel List API",
                "configured": source.is_configured,
            },
        }

    except Exception as e:
        logger.error(
            f"Failed to add Angel List source: {e}", extra_fields={"error": str(e)}
        )
        raise HTTPException(400, f"Failed to add Angel List source: {str(e)}")


@router.post("/sources/lever")
async def add_lever_source(
    api_key: str,
):
    """
    Add Lever API job source for direct application submission.

    Requires:
    - api_key: Lever API key (for direct job posting API, not recruitment)

    Args:
        api_key: Lever API key

    Returns:
        Confirmation that Lever source was added
    """
    logger.info("Adding Lever job source")

    try:
        # Note: This would require a LeverJobSource class if implementing job scraping
        # For now, Lever is primarily used for application routing, not job discovery
        # This endpoint is for future expansion if Lever job scraping is added

        # Store in environment or config
        import os

        os.environ["LEVER_API_KEY"] = api_key

        return {
            "status": "success",
            "source": {
                "name": "Lever API",
                "type": "Lever ATS",
                "note": "Lever credentials stored for application submission routing",
                "use_case": "Direct application submission to Lever-based ATSs",
            },
        }

    except Exception as e:
        logger.error(
            f"Failed to configure Lever source: {e}", extra_fields={"error": str(e)}
        )
        raise HTTPException(400, f"Failed to configure Lever source: {str(e)}")
