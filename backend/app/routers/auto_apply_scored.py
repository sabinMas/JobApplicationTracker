"""
Auto-Apply with AgentCore Scoring Integration

This router combines job scoring with auto-apply workflow.
Only submits applications to jobs scoring >= min_score (default 8/10).
"""

from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
import logging

from ..database import get_db
from ..models import Job
from ..services import job_scorer
from ..schemas import (
    ScoreJobsOut,
    ScoringHealthOut,
    HighScoreJobsOut,
    JobByScoreOut,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auto-apply-scored", tags=["auto-apply-scored"])


@router.post("/score-jobs", response_model=ScoreJobsOut)
async def score_all_jobs(
    min_date: str = Query(None, description="Score jobs since this date (ISO format)"),
    limit: int = Query(100, ge=1, le=500, description="Maximum jobs to score"),
    db: AsyncSession = Depends(get_db),
) -> ScoreJobsOut:
    """
    Score unscored jobs using AgentCore and store results in database.

    Args:
        min_date: ISO format date string to filter jobs
        limit: Maximum number of jobs to score (1-500)
        db: Database session

    Returns:
        ScoreJobsOut with scoring results and distribution

    Raises:
        HTTPException: On database or scoring errors
    """
    try:
        # Get unscored jobs
        query = (
            select(Job)
            .where(Job.score.is_(None))
            .order_by(Job.created_at.desc())
            .limit(limit)
        )

        if min_date:
            try:
                min_datetime = datetime.fromisoformat(min_date)
                query = query.where(Job.created_at >= min_datetime)
            except ValueError:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid date format. Use ISO format (YYYY-MM-DD)",
                )

        result = await db.execute(query)
        jobs = result.scalars().all()

        if not jobs:
            logger.info("No unscored jobs found")
            return ScoreJobsOut(
                jobs_processed=0,
                jobs_newly_scored=0,
                jobs_skipped=0,
                errors=0,
                score_distribution={},
                avg_score=None,
            )

        logger.info(
            f"Found {len(jobs)} unscored jobs to score", extra={"count": len(jobs)}
        )

        scores = []
        errors = 0

        for job in jobs:
            try:
                await job_scorer.score_and_store(db, job)
                scores.append(job.score)
                logger.debug(f"Scored job {job.id}: {job.score}/10")
            except Exception as e:
                error_msg = f"Error scoring job {job.id}: {str(e)}"
                logger.error(error_msg, extra={"job_id": job.id})
                errors += 1

        # Calculate statistics
        avg_score = sum(scores) / len(scores) if scores else None
        high_score_count = sum(1 for s in scores if s >= 8)
        medium_score_count = sum(1 for s in scores if 5 <= s < 8)
        low_score_count = sum(1 for s in scores if s < 5)

        return ScoreJobsOut(
            jobs_processed=len(jobs),
            jobs_newly_scored=len(scores),
            jobs_skipped=len(jobs) - len(scores) - errors,
            errors=errors,
            score_distribution={
                "high (8-10)": high_score_count,
                "medium (5-7)": medium_score_count,
                "low (1-4)": low_score_count,
            },
            avg_score=round(avg_score, 2) if avg_score else None,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error("Error in score_all_jobs", extra={"error": str(e)})
        raise HTTPException(status_code=500, detail="Failed to score jobs")


@router.get("/filter-high-score", response_model=HighScoreJobsOut)
async def get_high_score_jobs(
    min_score: int = Query(8, ge=1, le=10, description="Minimum score threshold"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> HighScoreJobsOut:
    """
    Get jobs that meet minimum score threshold (ready to apply).

    Args:
        min_score: Minimum score threshold (1-10)
        skip: Number of results to skip
        limit: Number of results to return (1-100)
        db: Database session

    Returns:
        HighScoreJobsOut with high-scoring jobs

    Raises:
        HTTPException: On database errors
    """
    try:
        # Get total count
        count_result = await db.execute(
            select(func.count(Job.id)).where(
                (Job.score >= min_score) & (Job.score.isnot(None))
            )
        )
        total_count = count_result.scalar() or 0

        # Get paginated results
        result = await db.execute(
            select(Job)
            .where((Job.score >= min_score) & (Job.score.isnot(None)))
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
            "Error filtering high-score jobs",
            extra={"error": str(e), "min_score": min_score},
        )
        raise HTTPException(status_code=500, detail="Failed to filter jobs")


@router.get("/scoring-stats", response_model=ScoringHealthOut)
async def get_scoring_stats(
    db: AsyncSession = Depends(get_db),
) -> ScoringHealthOut:
    """
    Get overall scoring system health and statistics.

    Args:
        db: Database session

    Returns:
        ScoringHealthOut with comprehensive scoring metrics

    Raises:
        HTTPException: On database errors
    """
    try:
        # Total jobs
        total_result = await db.execute(select(func.count(Job.id)))
        total_jobs = total_result.scalar() or 0

        # Scored jobs
        scored_result = await db.execute(
            select(func.count(Job.id)).where(Job.score.isnot(None))
        )
        scored_jobs = scored_result.scalar() or 0

        # Average score
        avg_result = await db.execute(
            select(func.avg(Job.score)).where(Job.score.isnot(None))
        )
        avg_score = float(avg_result.scalar() or 0)

        # Score distribution
        high_result = await db.execute(select(func.count(Job.id)).where(Job.score >= 8))
        high_score = high_result.scalar() or 0

        medium_result = await db.execute(
            select(func.count(Job.id)).where((Job.score >= 5) & (Job.score < 8))
        )
        medium_score = medium_result.scalar() or 0

        low_result = await db.execute(select(func.count(Job.id)).where(Job.score < 5))
        low_score = low_result.scalar() or 0

        unscored_jobs = total_jobs - scored_jobs
        percentage_scored = (scored_jobs / total_jobs * 100) if total_jobs > 0 else 0.0

        return ScoringHealthOut(
            total_jobs=total_jobs,
            scored_jobs=scored_jobs,
            unscored_jobs=unscored_jobs,
            percentage_scored=round(percentage_scored, 2),
            score_distribution={
                "high (8-10)": high_score,
                "medium (5-7)": medium_score,
                "low (1-4)": low_score,
            },
            avg_score=round(avg_score, 2) if avg_score > 0 else None,
            high_score_count=high_score,
            low_score_count=low_score,
            timestamp=datetime.utcnow(),
        )

    except Exception as e:
        logger.error("Error getting scoring statistics", extra={"error": str(e)})
        raise HTTPException(
            status_code=500, detail="Failed to retrieve scoring statistics"
        )
