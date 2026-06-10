"""
Score-gated auto-apply decisions.

Only applications to jobs scoring >= min_score proceed. On scoring failure the
job is SKIPPED — never auto-applied blind.
"""

import logging
from typing import Any, Dict

from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Job
from . import job_scorer

logger = logging.getLogger(__name__)


class ScoringFilter:
    """Filter jobs by score before auto-applying."""

    def __init__(self, min_score: int = 8):
        self.min_score = max(1, min(10, min_score))

    async def should_apply_to_job(self, job: Job, db: AsyncSession) -> Dict[str, Any]:
        """Decide whether to apply to this job based on its (possibly fresh) score.

        Returns {should_apply, score, reason, skip_reason}.
        """
        try:
            result = await job_scorer.score_and_store(db, job)
            score = result["score"]
        except Exception as e:
            # Safety: a job we could not evaluate is never auto-applied.
            logger.warning(
                f"Error scoring job {job.id}, skipping: {e}",
                extra={"job_id": job.id, "error": str(e)},
            )
            return {
                "should_apply": False,
                "score": None,
                "reason": f"Scoring failed: {e}",
                "skip_reason": "Scoring error",
            }

        should_apply = (
            score >= self.min_score
            and result.get("recommendation", "SKIP") != "SKIP"
        )
        reason = (
            f"Score {score}/10 meets threshold {self.min_score}/10"
            if score >= self.min_score
            else f"Score {score}/10 below threshold {self.min_score}/10"
        )
        if score >= self.min_score and not should_apply:
            reason += " but recommendation is SKIP"

        return {
            "should_apply": should_apply,
            "score": score,
            "reason": reason,
            "skip_reason": None if should_apply else "Low score or SKIP recommendation",
        }


def get_scoring_filter(min_score: int = 8) -> ScoringFilter:
    """Create a scoring filter with the given threshold."""
    return ScoringFilter(min_score)
