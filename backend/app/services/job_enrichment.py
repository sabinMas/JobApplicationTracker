"""
Automatic job enrichment pipeline.

When a job scores ≥7, trigger scrapers to gather additional details
and update the job with enriched data.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update

from app.models import Job, ScraperRun
from app.services.actor_runner import enqueue_actor_run

logger = logging.getLogger(__name__)


async def enrich_high_scoring_jobs(db: AsyncSession, score_threshold: int = 7) -> int:
    """
    Find jobs with score >= threshold that haven't been enriched yet.
    Trigger scraper runs for each.

    Returns the number of enrichment runs created.
    """
    # Query jobs with high scores that are still in 'discovered' status
    stmt = select(Job).where(
        Job.score >= score_threshold,
        Job.status == "discovered"
    ).limit(20)  # Limit to prevent overwhelming SQS

    result = await db.execute(stmt)
    jobs = result.scalars().all()

    created_count = 0
    for job in jobs:
        try:
            # Determine which scraper to use based on source
            actor_name = _get_actor_for_source(job.source)
            if not actor_name:
                logger.warning(f"No actor for source: {job.source}, skipping job {job.id}")
                continue

            # Create enrichment run
            run_id = await enqueue_actor_run(
                db,
                actor_name=actor_name,
                input_config={
                    "query": job.title,
                    "location": job.location or "United States",
                    "max_results": 5,
                    "target_job_id": job.id,
                },
                run_name=f"enrich-{job.id}-{job.title[:30]}",
                webhook_url=None,  # Could add callback URL here
            )

            # Mark job as being enriched
            stmt_update = update(Job).where(Job.id == job.id).values(
                status="enriching"
            )
            await db.execute(stmt_update)
            await db.commit()

            logger.info(f"Created enrichment run {run_id} for job {job.id}: {job.title}")
            created_count += 1

        except Exception as e:
            logger.error(f"Error enriching job {job.id}: {e}", exc_info=True)
            continue

    return created_count


async def on_scraper_complete(
    db: AsyncSession,
    run_id: int,
    items: list[Dict[str, Any]],
) -> None:
    """
    Callback when scraper run completes.
    If this was an enrichment run, update the job with the results.
    """
    try:
        # Fetch the run
        stmt = select(ScraperRun).where(ScraperRun.id == run_id)
        result = await db.execute(stmt)
        run = result.scalar_one_or_none()

        if not run:
            return

        # Check if this was an enrichment run (has target_job_id in config)
        target_job_id = run.input_config.get("target_job_id")
        if not target_job_id:
            return

        # Fetch the target job
        stmt_job = select(Job).where(Job.id == target_job_id)
        result_job = await db.execute(stmt_job)
        job = result_job.scalar_one_or_none()

        if not job or not items:
            return

        # Use the first result to enrich the job
        enrichment = items[0]
        
        # Update job with enriched data
        stmt_update = update(Job).where(Job.id == target_job_id).values(
            description=enrichment.get("description") or job.description,
            requirements=enrichment.get("requirements") or job.requirements,
            salary_range=enrichment.get("salary_range") or job.salary_range,
            status="enriched",  # Mark as enriched
        )
        await db.execute(stmt_update)
        await db.commit()

        logger.info(f"Enriched job {target_job_id} with data from run {run_id}")

    except Exception as e:
        logger.error(f"Error in enrichment callback: {e}", exc_info=True)


def _get_actor_for_source(source: str) -> Optional[str]:
    """Map job source to scraper actor name."""
    mapping = {
        "linkedin": "linkedin",
        "indeed": "indeed",
        "github": "github",
        "greenhouse": "linkedin",  # Fallback to LinkedIn
        "lever": "linkedin",
        "angellist": "angellist",
        "rss": "linkedin",
    }
    return mapping.get(source.lower())
