"""Dashboard API endpoints for metrics and analytics"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime, timedelta
import logging
from ..database import get_db
from ..models import Job, Application, ApplicationMetric
from ..schemas import (
    DashboardMetricsOut,
    HighScoreJobsOut,
    JobByScoreOut,
    HealthCheckOut,
    ApplicationTimelineResponse,
    ApplicationTimelineOut,
    StatusBreakdownResponse,
    StatusBreakdownOut,
    ScoringStats,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/dashboard", tags=["dashboard"])


@router.get("/metrics", response_model=DashboardMetricsOut)
async def get_metrics(
    days: int = Query(7, ge=1, le=90, description="Number of days to include"),
    db: AsyncSession = Depends(get_db),
) -> DashboardMetricsOut:
    """
    Get comprehensive dashboard metrics for the specified time period.

    Args:
        days: Number of days to look back (1-90)
        db: Database session

    Returns:
        DashboardMetricsOut with complete metrics

    Raises:
        HTTPException: On database errors
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        # Total jobs and applications
        jobs_result = await db.execute(
            select(func.count(Job.id)).where(Job.created_at >= start_date)
        )
        total_jobs = jobs_result.scalar() or 0

        apps_result = await db.execute(
            select(func.count(Application.id)).where(
                Application.created_at >= start_date
            )
        )
        total_apps = apps_result.scalar() or 0

        # Success/failure counts
        success_result = await db.execute(
            select(func.count(ApplicationMetric.id)).where(
                (ApplicationMetric.created_at >= start_date)
                & (ApplicationMetric.status == "success")
            )
        )
        successful = success_result.scalar() or 0

        failed_result = await db.execute(
            select(func.count(ApplicationMetric.id)).where(
                (ApplicationMetric.created_at >= start_date)
                & (ApplicationMetric.status == "failed")
            )
        )
        failed = failed_result.scalar() or 0

        success_rate = (
            successful / (successful + failed) if (successful + failed) > 0 else 0.0
        )

        # Average score
        score_result = await db.execute(
            select(func.avg(Job.score)).where(
                (Job.created_at >= start_date) & (Job.score.isnot(None))
            )
        )
        avg_score = float(score_result.scalar() or 0)

        # Score distribution
        high_score_result = await db.execute(
            select(func.count(Job.id)).where(
                (Job.created_at >= start_date) & (Job.score >= 8)
            )
        )
        high_scores = high_score_result.scalar() or 0

        medium_score_result = await db.execute(
            select(func.count(Job.id)).where(
                (Job.created_at >= start_date) & (Job.score >= 5) & (Job.score < 8)
            )
        )
        medium_scores = medium_score_result.scalar() or 0

        low_score_result = await db.execute(
            select(func.count(Job.id)).where(
                (Job.created_at >= start_date) & (Job.score < 5)
            )
        )
        low_scores = low_score_result.scalar() or 0

        # Scoring stats
        total_scored_result = await db.execute(
            select(func.count(Job.id)).where(
                (Job.created_at >= start_date) & (Job.score.isnot(None))
            )
        )
        total_scored = total_scored_result.scalar() or 0
        percentage_scored = (total_scored / total_jobs * 100) if total_jobs > 0 else 0.0

        # By ATS platform
        ats_result = await db.execute(
            select(Application.ats_platform, func.count(Application.id))
            .where(Application.created_at >= start_date)
            .group_by(Application.ats_platform)
        )
        ats_data = {k: v for k, v in ats_result.all()}

        # By job source
        source_result = await db.execute(
            select(Job.source, func.count(Job.id))
            .where(Job.created_at >= start_date)
            .group_by(Job.source)
        )
        source_data = {k: v for k, v in source_result.all()}

        # By application status
        status_result = await db.execute(
            select(Application.status, func.count(Application.id))
            .where(Application.created_at >= start_date)
            .group_by(Application.status)
        )
        status_data = {k: v for k, v in status_result.all()}

        scoring_stats = ScoringStats(
            total_jobs=total_jobs,
            total_scored=total_scored,
            percentage_scored=round(percentage_scored, 2),
            avg_score=round(avg_score, 2) if avg_score > 0 else None,
            min_score=1,
            max_score=10,
            score_distribution={
                "high (8-10)": high_scores,
                "medium (5-7)": medium_scores,
                "low (1-4)": low_scores,
            },
        )

        return DashboardMetricsOut(
            period_days=days,
            timestamp=datetime.utcnow(),
            total_jobs_discovered=total_jobs,
            jobs_by_source=source_data,
            total_applications=total_apps,
            applications_by_status=status_data,
            applications_by_ats=ats_data,
            scoring_stats=scoring_stats,
            successful_applications=successful,
            failed_applications=failed,
            success_rate=round(success_rate, 4),
            avg_time_to_apply_minutes=None,
        )

    except Exception as e:
        logger.error(
            "Error getting dashboard metrics", extra_fields={"error": str(e), "days": days}
        )
        raise HTTPException(
            status_code=500, detail="Failed to retrieve dashboard metrics"
        )


@router.get("/jobs/by-score", response_model=HighScoreJobsOut)
async def get_jobs_by_score(
    min_score: int = Query(1, ge=1, le=10),
    max_score: int = Query(10, ge=1, le=10),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> HighScoreJobsOut:
    """
    Get jobs filtered by score range with pagination.

    Args:
        min_score: Minimum score (1-10)
        max_score: Maximum score (1-10)
        skip: Number of results to skip
        limit: Number of results to return (1-100)
        db: Database session

    Returns:
        HighScoreJobsOut with matching jobs

    Raises:
        HTTPException: If min_score > max_score or database errors
    """
    if min_score > max_score:
        raise HTTPException(
            status_code=400, detail="min_score must be less than or equal to max_score"
        )

    try:
        # Get total count
        count_result = await db.execute(
            select(func.count(Job.id)).where(
                (Job.score >= min_score)
                & (Job.score <= max_score)
                & (Job.score.isnot(None))
            )
        )
        total_count = count_result.scalar() or 0

        # Get paginated results
        result = await db.execute(
            select(Job)
            .where(
                (Job.score >= min_score)
                & (Job.score <= max_score)
                & (Job.score.isnot(None))
            )
            .order_by(Job.score.desc())
            .offset(skip)
            .limit(limit)
        )
        jobs = result.scalars().all()

        jobs_out = [
            JobByScoreOut(
                id=job.id,
                title=job.title,
                company=job.company,
                location=job.location,
                score=job.score,
                score_reasoning=job.score_reasoning,
                score_strengths=job.score_strengths or [],
                score_concerns=job.score_concerns or [],
                score_recommendation=job.score_recommendation,
                apply_url=job.apply_url,
                source=job.source,
            )
            for job in jobs
        ]

        return HighScoreJobsOut(
            total_available=total_count,
            jobs=jobs_out,
            min_score_threshold=min_score,
        )

    except Exception as e:
        logger.error(
            "Error filtering jobs by score",
            extra_fields={"error": str(e), "min_score": min_score, "max_score": max_score},
        )
        raise HTTPException(status_code=500, detail="Failed to filter jobs")


@router.get("/applications/timeline", response_model=ApplicationTimelineResponse)
async def get_applications_timeline(
    days: int = Query(7, ge=1, le=90),
    db: AsyncSession = Depends(get_db),
) -> ApplicationTimelineResponse:
    """
    Get applications over time for timeline visualization.

    Args:
        days: Number of days to look back
        db: Database session

    Returns:
        ApplicationTimelineResponse with date/count data

    Raises:
        HTTPException: On database errors
    """
    try:
        start_date = datetime.utcnow() - timedelta(days=days)

        result = await db.execute(
            select(
                func.date(Application.created_at).label("date"),
                func.count(Application.id).label("count"),
            )
            .where(Application.created_at >= start_date)
            .group_by(func.date(Application.created_at))
            .order_by(func.date(Application.created_at))
        )

        timeline = [
            ApplicationTimelineOut(date=str(date), applications_count=count)
            for date, count in result.all()
        ]

        return ApplicationTimelineResponse(period_days=days, data=timeline)

    except Exception as e:
        logger.error(
            "Error getting application timeline", extra_fields={"error": str(e), "days": days}
        )
        raise HTTPException(status_code=500, detail="Failed to retrieve timeline data")


@router.get("/applications/status-breakdown", response_model=StatusBreakdownResponse)
async def get_status_breakdown(
    db: AsyncSession = Depends(get_db),
) -> StatusBreakdownResponse:
    """
    Get application status distribution.

    Args:
        db: Database session

    Returns:
        StatusBreakdownResponse with status counts

    Raises:
        HTTPException: On database errors
    """
    try:
        result = await db.execute(
            select(Application.status, func.count(Application.id)).group_by(
                Application.status
            )
        )

        total = 0
        breakdown_data = []
        status_dict = dict(result.all())

        for status, count in status_dict.items():
            total += count

        for status, count in sorted(status_dict.items()):
            percentage = (count / total * 100) if total > 0 else 0.0
            breakdown_data.append(
                StatusBreakdownOut(
                    status=status, count=count, percentage=round(percentage, 2)
                )
            )

        return StatusBreakdownResponse(
            total_applications=total, breakdown=breakdown_data
        )

    except Exception as e:
        logger.error("Error getting status breakdown", extra_fields={"error": str(e)})
        raise HTTPException(
            status_code=500, detail="Failed to retrieve status breakdown"
        )


@router.get("/health", response_model=HealthCheckOut)
async def dashboard_health() -> HealthCheckOut:
    """
    Health check for dashboard service.

    Returns:
        HealthCheckOut with service status
    """
    return HealthCheckOut(
        status="ok",
        service="dashboard",
        db_initialized=True,
        timestamp=datetime.utcnow(),
    )
