"""
Metrics and analytics endpoints for JobApplicationTracker.

Provides real-time and historical metrics on application submissions,
success rates, performance, and platform-specific analytics.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime, timedelta, timezone

from ..database import get_db
from ..models import ApplicationMetric, Application
from ..logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/metrics", tags=["metrics"])


@router.get("/dashboard")
async def get_metrics_dashboard(
    days: int = 7,
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive metrics dashboard for the last N days.
    
    Returns:
    - Summary statistics
    - Daily timeseries data
    - Breakdown by ATS platform
    - Today's progress
    """
    logger.info("Fetching metrics dashboard", extra_fields={"days": days})
    
    now = datetime.now(timezone.utc)
    start_date = now - timedelta(days=days)
    
    # Overall stats
    total_result = await db.execute(
        select(func.count(ApplicationMetric.id)).where(
            ApplicationMetric.created_at >= start_date
        )
    )
    total_attempts = total_result.scalar() or 0
    
    # Success rate
    success_result = await db.execute(
        select(func.count(ApplicationMetric.id)).where(
            and_(
                ApplicationMetric.created_at >= start_date,
                ApplicationMetric.status == "success",
            )
        )
    )
    successful = success_result.scalar() or 0
    success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0
    
    # Average duration
    duration_result = await db.execute(
        select(func.avg(ApplicationMetric.duration_ms)).where(
            ApplicationMetric.created_at >= start_date
        )
    )
    avg_duration_ms = duration_result.scalar() or 0
    
    # By ATS platform
    ats_result = await db.execute(
        select(
            ApplicationMetric.ats_platform_detected,
            func.count(ApplicationMetric.id).label("attempts"),
            func.sum(func.cast(
                (ApplicationMetric.status == "success"),
                type_=int
            )).label("successful"),
        ).where(ApplicationMetric.created_at >= start_date)
        .group_by(ApplicationMetric.ats_platform_detected)
        .order_by(func.count(ApplicationMetric.id).desc())
    )
    ats_breakdown = [
        {
            "platform": row[0] or "unknown",
            "attempts": row[1],
            "successful": row[2] or 0,
            "success_rate": ((row[2] or 0) / row[1] * 100) if row[1] > 0 else 0,
        }
        for row in ats_result.all()
    ]
    
    # Daily timeseries (for chart)
    daily_result = await db.execute(
        select(
            func.date(ApplicationMetric.created_at).label("date"),
            func.count(ApplicationMetric.id).label("attempts"),
            func.sum(func.cast(
                (ApplicationMetric.status == "success"),
                type_=int
            )).label("successful"),
        ).where(ApplicationMetric.created_at >= start_date)
        .group_by(func.date(ApplicationMetric.created_at))
        .order_by(func.date(ApplicationMetric.created_at))
    )
    daily_data = [
        {
            "date": str(row[0]),
            "attempts": row[1],
            "successful": row[2] or 0,
            "success_rate": ((row[2] or 0) / row[1] * 100) if row[1] > 0 else 0,
        }
        for row in daily_result.all()
    ]
    
    # Today's stats
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_result = await db.execute(
        select(
            func.count(ApplicationMetric.id),
            func.sum(func.cast(
                (ApplicationMetric.status == "success"),
                type_=int
            )),
        ).where(ApplicationMetric.created_at >= today_start)
    )
    today_row = today_result.first()
    today_attempts = today_row[0] if today_row else 0
    today_successful = today_row[1] or 0 if today_row else 0
    today_success_rate = (today_successful / today_attempts * 100) if today_attempts > 0 else 0
    
    logger.info("Metrics dashboard retrieved", extra_fields={
        "total_attempts": total_attempts,
        "success_rate": success_rate,
        "period_days": days,
    })
    
    return {
        "period": {
            "start": start_date.isoformat(),
            "end": now.isoformat(),
            "days": days,
        },
        "summary": {
            "total_attempts": total_attempts,
            "successful": successful,
            "success_rate_pct": round(success_rate, 1),
            "avg_duration_ms": round(avg_duration_ms, 0),
        },
        "by_ats_platform": ats_breakdown,
        "daily_timeseries": daily_data,
        "today": {
            "attempts": today_attempts,
            "successful": today_successful,
            "success_rate": round(today_success_rate, 1),
        },
    }


@router.get("/errors")
async def get_recent_errors(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Get recent application errors for debugging.
    
    Returns the N most recent failed submission attempts.
    """
    logger.info("Fetching recent errors", extra_fields={"limit": limit})
    
    result = await db.execute(
        select(ApplicationMetric).where(
            ApplicationMetric.status == "failed"
        ).order_by(ApplicationMetric.created_at.desc())
        .limit(limit)
    )
    errors = result.scalars().all()
    
    return {
        "total_errors": len(errors),
        "errors": [
            {
                "metric_id": e.id,
                "application_id": e.application_id,
                "attempt_number": e.attempt_number,
                "error_message": e.error_message,
                "ats_platform": e.ats_platform_detected,
                "timestamp": e.created_at.isoformat(),
                "duration_ms": e.duration_ms,
            }
            for e in errors
        ],
    }


@router.get("/applications/{application_id}")
async def get_application_metrics(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Get metrics for a specific application (all retry attempts).
    
    Useful for debugging why an application failed.
    """
    logger.info("Fetching metrics for application", extra_fields={"application_id": application_id})
    
    # Get application
    app_result = await db.execute(
        select(Application).where(Application.id == application_id)
    )
    app = app_result.scalar_one_or_none()
    
    if not app:
        return {"error": "Application not found"}
    
    # Get all metrics for this application
    metrics_result = await db.execute(
        select(ApplicationMetric).where(
            ApplicationMetric.application_id == application_id
        ).order_by(ApplicationMetric.created_at)
    )
    metrics = metrics_result.scalars().all()
    
    # Compute statistics
    attempts = len(metrics)
    successful_attempts = sum(1 for m in metrics if m.status == "success")
    failed_attempts = sum(1 for m in metrics if m.status == "failed")
    avg_duration = sum(m.duration_ms or 0 for m in metrics) / attempts if attempts > 0 else 0
    
    return {
        "application_id": application_id,
        "job_id": app.job_id,
        "total_attempts": attempts,
        "successful": successful_attempts,
        "failed": failed_attempts,
        "status": app.status,
        "retry_count": app.retry_count,
        "last_error": app.last_error,
        "error_history": app.error_history,
        "avg_duration_ms": round(avg_duration, 0),
        "metrics": [
            {
                "attempt": m.attempt_number,
                "status": m.status,
                "duration_ms": m.duration_ms,
                "error": m.error_message,
                "ats_platform": m.ats_platform_detected,
                "fields_detected": m.form_fields_detected,
                "fields_filled": m.fields_filled,
                "timestamp": m.created_at.isoformat(),
            }
            for m in metrics
        ],
    }


@router.get("/summary")
async def get_metrics_summary(
    db: AsyncSession = Depends(get_db),
):
    """
    Get quick summary statistics (last 24 hours).
    
    Useful for dashboard widgets or quick status checks.
    """
    logger.info("Fetching metrics summary")
    
    now = datetime.now(timezone.utc)
    today_start = now - timedelta(hours=24)
    
    # Count applications by status
    all_statuses_result = await db.execute(
        select(
            Application.status,
            func.count(Application.id),
        ).group_by(Application.status)
    )
    
    status_counts = {}
    for status, count in all_statuses_result.all():
        status_counts[status] = count
    
    # Metrics for last 24 hours
    metrics_result = await db.execute(
        select(ApplicationMetric).where(
            ApplicationMetric.created_at >= today_start
        )
    )
    metrics = metrics_result.scalars().all()
    
    success_count = sum(1 for m in metrics if m.status == "success")
    fail_count = sum(1 for m in metrics if m.status == "failed")
    
    return {
        "period_hours": 24,
        "applications_by_status": status_counts,
        "last_24_hours": {
            "submissions_attempted": len(metrics),
            "successful": success_count,
            "failed": fail_count,
            "success_rate": (success_count / len(metrics) * 100) if metrics else 0,
        },
    }


@router.get("/retry-candidates")
async def get_retry_candidates(
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Get applications ready for retry.
    
    Returns failed applications whose next_retry_at is in the past.
    """
    logger.info("Fetching retry candidates", extra_fields={"limit": limit})
    
    now = datetime.now(timezone.utc)
    
    result = await db.execute(
        select(Application).where(
            and_(
                Application.retry_count < 3,
                or_(
                    Application.next_retry_at.is_(None),
                    Application.next_retry_at <= now,
                )
            )
        ).order_by(Application.next_retry_at)
        .limit(limit)
    )
    candidates = result.scalars().all()
    
    return {
        "total_candidates": len(candidates),
        "candidates": [
            {
                "application_id": app.id,
                "job_id": app.job_id,
                "retry_count": app.retry_count,
                "last_error": app.last_error,
                "next_retry_at": app.next_retry_at.isoformat() if app.next_retry_at else None,
                "error_history_count": len(app.error_history or []),
            }
            for app in candidates
        ],
    }
