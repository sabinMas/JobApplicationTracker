"""Job enrichment pipeline API endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services.job_enrichment import enrich_high_scoring_jobs
from pydantic import BaseModel

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


class EnrichmentResult(BaseModel):
    enrichment_runs_created: int
    message: str


@router.post("/enrich-high-scoring", response_model=EnrichmentResult)
async def enrich_jobs(
    score_threshold: int = 7,
    db: AsyncSession = Depends(get_db),
) -> EnrichmentResult:
    """
    Trigger scraper runs for all jobs with score >= threshold.
    
    This endpoint finds high-quality job matches that haven't been enriched yet
    and automatically queues them for additional data gathering via the scraper
    framework.
    """
    try:
        count = await enrich_high_scoring_jobs(db, score_threshold=score_threshold)
        return EnrichmentResult(
            enrichment_runs_created=count,
            message=f"Created {count} enrichment runs for jobs scoring >= {score_threshold}"
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
