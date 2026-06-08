"""
Auto-Apply with AgentCore Scoring

Integrates job scoring into the auto-apply workflow.
Only submits applications to jobs scoring >= min_score (default 8/10).
"""

import logging
from typing import Optional, Dict, Any
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from ..models import Job, Application
from .job_scorer import get_scorer

logger = logging.getLogger(__name__)


class ScoringFilter:
    """Filter jobs by score before auto-applying"""

    def __init__(self, min_score: int = 8):
        """Initialize filter with minimum score threshold (1-10)"""
        self.min_score = max(1, min(10, min_score))  # Clamp 1-10

    async def should_apply_to_job(self, job: Job, user_profile: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Determine if we should apply to this job based on score

        Returns:
            {
                "should_apply": True/False,
                "score": 8.5,
                "reason": "Score meets threshold" or "Score too low",
                "skip_reason": optional reason if skipped
            }
        """
        try:
            # If job already scored, use existing score
            if job.score is not None:
                should_apply = job.score >= self.min_score
                reason = (
                    f"Score {job.score}/10 meets threshold {self.min_score}/10"
                    if should_apply
                    else f"Score {job.score}/10 below threshold {self.min_score}/10"
                )
                return {
                    "should_apply": should_apply,
                    "score": job.score,
                    "reason": reason,
                    "skip_reason": None if should_apply else "Low score",
                }

            # Score job if not already scored
            logger.info(f"Scoring job: {job.title}", extra_fields={"job_id": job.id})
            scorer = await get_scorer()
            score_result = await scorer.score_job(
                job_title=job.title,
                company=job.company,
                description=job.description or "",
                location=job.location,
                user_profile=user_profile,
            )

            # Check if score meets threshold
            score = score_result["score"]
            should_apply = score >= self.min_score

            return {
                "should_apply": should_apply,
                "score": score,
                "reason": (
                    f"Score {score}/10 meets threshold {self.min_score}/10"
                    if should_apply
                    else f"Score {score}/10 below threshold {self.min_score}/10"
                ),
                "skip_reason": None if should_apply else "Low score",
                "score_details": score_result,  # Additional scoring info
            }

        except Exception as e:
            logger.warning(
                f"Error evaluating score for job {job.id}: {e}",
                extra_fields={"job_id": job.id, "error": str(e)},
            )
            # On error, default to apply (conservative approach)
            return {
                "should_apply": True,
                "score": 5.0,  # Neutral score
                "reason": "Could not score, defaulting to apply",
                "skip_reason": None,
            }

    async def score_and_store(self, job: Job, db: AsyncSession) -> Dict[str, Any]:
        """
        Score a job and store the score in database
        """
        try:
            if job.score is not None:
                # Already scored
                return {
                    "already_scored": True,
                    "score": job.score,
                    "scored_at": job.scored_at,
                }

            logger.info(f"Scoring and storing job: {job.title}", extra_fields={"job_id": job.id})

            scorer = await get_scorer()
            score_result = await scorer.score_job(
                job_title=job.title,
                company=job.company,
                description=job.description or "",
                location=job.location,
            )

            # Store score in database
            job.score = int(score_result["score"])
            job.score_reasoning = score_result.get("reasoning", "")
            job.score_strengths = score_result.get("strengths", [])
            job.score_concerns = score_result.get("concerns", [])
            job.score_recommendation = score_result.get("recommendation", "SKIP")
            job.scored_at = datetime.utcnow()

            await db.commit()
            logger.info(
                f"Job scored and stored: {job.title}",
                extra_fields={"job_id": job.id, "score": job.score},
            )

            return {
                "scored": True,
                "score": job.score,
                "reasoning": job.score_reasoning,
                "strengths": job.score_strengths,
                "concerns": job.score_concerns,
                "recommendation": job.score_recommendation,
            }

        except Exception as e:
            logger.error(
                f"Error scoring job {job.id}: {e}",
                extra_fields={"job_id": job.id, "error": str(e)},
            )
            raise


# Singleton instance
_scoring_filter = None


async def get_scoring_filter(min_score: int = 8) -> ScoringFilter:
    """Get or create scoring filter instance"""
    global _scoring_filter
    if _scoring_filter is None:
        _scoring_filter = ScoringFilter(min_score)
    return _scoring_filter
