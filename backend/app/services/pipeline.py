"""
End-to-end daily automation pipeline.

Stages:
  1. Discover  — sync jobs from preference-derived sources
  2. Score     — AI-score new jobs against the candidate's niches
  3. Enrich    — queue scraper enrichment for promising jobs (score >= 7)
  4. Prepare   — tailor resume + cover letter for jobs above the apply threshold
  5. Submit    — enqueue auto-apply (if enabled) or mark ready_for_review

Triggered by the EventBridge daily schedule (via the Lambda handler) or by
POST /api/scheduler/run-pipeline. Every run writes a PipelineRun summary row.
"""

import json
import logging
import os
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Application, Job, PipelineRun, SearchPreferences
from . import job_scorer
from .job_enrichment import enrich_high_scoring_jobs
from .tailoring_service import TailoringError, tailor_documents_for_job

logger = logging.getLogger(__name__)

SCORING_BATCH_LIMIT = 50
APPLY_QUEUE_URL = os.getenv("SQS_QUEUE_URL", os.getenv("SCRAPER_QUEUE_URL", ""))


def _record_error(run: PipelineRun, stage: str, error: Exception) -> None:
    entries = list(run.errors or [])
    entries.append(
        {
            "stage": stage,
            "message": str(error)[:300],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
    )
    run.errors = entries


async def _stage_discover(run: PipelineRun) -> None:
    from .job_sync_scheduler import get_scheduler

    scheduler = get_scheduler()
    if not scheduler:
        raise RuntimeError("Job sync scheduler not initialized")
    result = await scheduler.sync_now()
    run.jobs_discovered = result.get("stats", {}).get("added", 0)


async def _stage_score(db: AsyncSession, run: PipelineRun) -> None:
    jobs = (
        (
            await db.execute(
                select(Job)
                .where(Job.score.is_(None), Job.status == "discovered")
                .order_by(Job.created_at.desc())
                .limit(SCORING_BATCH_LIMIT)
            )
        )
        .scalars()
        .all()
    )

    for job in jobs:
        try:
            await job_scorer.score_and_store(db, job)
            run.jobs_scored += 1
        except Exception as e:
            logger.error(f"Scoring failed for job {job.id}: {e}")
            _record_error(run, "score", e)


async def _stage_prepare_and_submit(
    db: AsyncSession, run: PipelineRun, prefs: SearchPreferences
) -> None:
    min_score = prefs.min_score_to_apply or 8
    daily_limit = prefs.daily_application_limit or 10

    jobs = (
        (
            await db.execute(
                select(Job)
                .where(
                    Job.score >= min_score,
                    Job.score_recommendation == "SUBMIT",
                    Job.status.in_(["discovered", "enriching"]),
                    Job.apply_url.isnot(None),
                )
                .order_by(Job.score.desc())
                .limit(daily_limit)
            )
        )
        .scalars()
        .all()
    )

    for job in jobs:
        try:
            existing = (
                (
                    await db.execute(
                        select(Application).where(Application.job_id == job.id)
                    )
                )
                .scalars()
                .first()
            )
            if existing:
                continue

            resume_doc, cl_doc = await tailor_documents_for_job(db, job)

            application = Application(
                job_id=job.id,
                status="ready_for_review",
                tailored_resume_id=resume_doc.id,
                tailored_cover_letter_id=cl_doc.id,
            )
            db.add(application)
            job.status = "applying"
            await db.commit()
            await db.refresh(application)
            run.applications_prepared += 1

            if prefs.auto_submit_enabled:
                # Rule: never auto-submit without a tailored resume attached.
                if not application.tailored_resume_id:
                    logger.warning(
                        f"Application {application.id} missing tailored resume, not submitting"
                    )
                    continue
                await _enqueue_auto_apply(application.id)
                application.status = "pending"
                await db.commit()
                run.applications_submitted += 1
            else:
                run.applications_queued_for_review += 1

        except TailoringError as e:
            logger.warning(f"Cannot tailor for job {job.id}: {e}")
            _record_error(run, "prepare", e)
            break  # missing profile/resume affects every job — stop the stage
        except Exception as e:
            logger.error(f"Prepare failed for job {job.id}: {e}")
            _record_error(run, "prepare", e)


async def _enqueue_auto_apply(application_id: int) -> None:
    """Send an auto-apply task to the worker queue (Playwright runs there)."""
    import aioboto3

    if not APPLY_QUEUE_URL:
        raise RuntimeError("SQS_QUEUE_URL not configured for auto-apply")

    session = aioboto3.Session()
    async with session.client(
        "sqs", region_name=os.getenv("AWS_REGION", "us-east-1")
    ) as sqs:
        await sqs.send_message(
            QueueUrl=APPLY_QUEUE_URL,
            MessageBody=json.dumps(
                {"action": "auto_apply", "application_id": application_id}
            ),
        )
    logger.info(f"Enqueued auto-apply for application {application_id}")


async def run_pipeline(db: AsyncSession, trigger: str = "manual") -> PipelineRun:
    """Execute the full pipeline and return the PipelineRun summary."""
    run = PipelineRun(trigger=trigger, status="running")
    db.add(run)
    await db.commit()
    await db.refresh(run)
    logger.info(f"Pipeline run {run.id} started (trigger={trigger})")

    prefs = (await db.execute(select(SearchPreferences))).scalar_one_or_none()

    try:
        try:
            await _stage_discover(run)
        except Exception as e:
            logger.error(f"Discovery stage failed: {e}")
            _record_error(run, "discover", e)

        await _stage_score(db, run)

        try:
            run.jobs_enriched = await enrich_high_scoring_jobs(db)
        except Exception as e:
            logger.error(f"Enrichment stage failed: {e}")
            _record_error(run, "enrich", e)

        if prefs is None:
            _record_error(
                run,
                "prepare",
                RuntimeError(
                    "SearchPreferences not configured — skipping prepare/submit. "
                    "Set preferences via PUT /api/profile/preferences."
                ),
            )
        else:
            await _stage_prepare_and_submit(db, run, prefs)

        run.status = "completed"
    except Exception as e:
        logger.error(f"Pipeline run {run.id} failed: {e}", exc_info=True)
        _record_error(run, "pipeline", e)
        run.status = "failed"
    finally:
        run.finished_at = datetime.now(timezone.utc)
        await db.commit()
        await db.refresh(run)

    logger.info(
        f"Pipeline run {run.id} {run.status}: discovered={run.jobs_discovered} "
        f"scored={run.jobs_scored} enriched={run.jobs_enriched} "
        f"prepared={run.applications_prepared} submitted={run.applications_submitted} "
        f"review={run.applications_queued_for_review}"
    )
    return run
