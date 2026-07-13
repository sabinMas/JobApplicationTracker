"""
Full auto-apply execution: ATS routing, retries, metrics, status updates.

Extracted from the auto_apply router so it can run both from the API (inline
dev mode) and from the SQS worker (production — Playwright lives only there).
"""

import time
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..logging_config import get_logger
from ..models import Application, ApplicationMetric, Document, Job, Profile
from .ats_integration import detect_ats_from_url
from .ats_routers import route_and_submit
from .notification_service import notify_application_submitted
from .retry_service import calculate_next_retry_time, execute_with_retry

logger = get_logger(__name__)


class AutoApplyPreconditionError(Exception):
    """Application/job/profile state prevents auto-apply (HTTP 4xx territory)."""


async def _perform_auto_apply(
    application_id: int,
    job: Job,
    profile: Profile,
    app: Application,
    db: AsyncSession,
) -> dict:
    """Core auto-apply logic using intelligent ATS routing."""
    resume_path = None
    cover_letter_path = None

    if app.tailored_resume_id:
        doc = (
            await db.execute(
                select(Document).where(Document.id == app.tailored_resume_id)
            )
        ).scalar_one_or_none()
        if doc:
            resume_path = doc.file_path

    if app.tailored_cover_letter_id:
        doc = (
            await db.execute(
                select(Document).where(Document.id == app.tailored_cover_letter_id)
            )
        ).scalar_one_or_none()
        if doc:
            cover_letter_path = doc.file_path

    profile_dict = {k: v for k, v in profile.__dict__.items() if not k.startswith("_")}

    result = await route_and_submit(
        application_id=application_id,
        job_url=job.apply_url,
        profile=profile_dict,
        resume_path=resume_path or "",
        cover_letter_path=cover_letter_path or "",
    )

    if result.get("status") == "success":
        app.status = "applied"
        app.applied_date = datetime.now(timezone.utc)
        await db.commit()
        logger.info(f"Application {application_id} status updated to 'applied'")
        await notify_application_submitted(
            application_id=application_id,
            job_title=job.title,
            company=job.company,
            apply_url=job.apply_url,
            ats_platform=detect_ats_from_url(job.apply_url),
            applied_at=app.applied_date.isoformat(),
        )

    return result


async def run_full_auto_apply(db: AsyncSession, application_id: int) -> dict:
    """Execute the full auto-apply flow with retry, metrics, and error history.

    Raises AutoApplyPreconditionError when the application, job URL, profile,
    or tailored resume is missing. Returns the result dict otherwise.
    """
    logger.info(f"Starting full auto-apply for application {application_id}")
    start_time = time.time()

    app = (
        await db.execute(select(Application).where(Application.id == application_id))
    ).scalar_one_or_none()
    if not app:
        raise AutoApplyPreconditionError("Application not found.")

    job = (
        await db.execute(select(Job).where(Job.id == app.job_id))
    ).scalar_one_or_none()
    if not job or not job.apply_url:
        raise AutoApplyPreconditionError("Job has no apply URL.")

    profile = (await db.execute(select(Profile))).scalar_one_or_none()
    if not profile:
        raise AutoApplyPreconditionError("Profile not set up.")

    # Never submit an application without a tailored resume attached.
    if not app.tailored_resume_id:
        raise AutoApplyPreconditionError(
            "Application has no tailored resume. Tailor documents before auto-applying."
        )

    attempt_number = app.retry_count + 1
    metric = ApplicationMetric(
        application_id=application_id,
        attempt_number=attempt_number,
        start_time=datetime.now(timezone.utc),
        ats_platform_detected=detect_ats_from_url(job.apply_url),
    )
    db.add(metric)
    await db.commit()
    await db.refresh(metric)

    try:

        async def retry_callback(attempt, wait_time, error):
            logger.warning(
                f"Retrying auto-apply for application {application_id} "
                f"(retry {attempt}), waiting {wait_time}s: {str(error)[:100]}"
            )

        result = await execute_with_retry(
            _perform_auto_apply,
            application_id,
            job,
            profile,
            app,
            db,
            max_attempts=3,
            on_retry_callback=retry_callback,
            context_fields={"application_id": application_id},
        )

        duration_ms = int((time.time() - start_time) * 1000)
        metric.end_time = datetime.now(timezone.utc)
        metric.duration_ms = duration_ms
        metric.status = result["status"]
        metric.form_fields_detected = result.get("fields_filled", 0)
        metric.fields_filled = result.get("fields_filled", 0)
        await db.commit()

        logger.info(
            f"Auto-apply completed for application {application_id}: "
            f"{result['status']} in {duration_ms}ms"
        )
        return result

    except Exception as e:
        app.retry_count = attempt_number
        app.last_error = str(e)[:500]
        error_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)[:200],
            "attempt": attempt_number,
            "error_type": type(e).__name__,
        }
        app.error_history = list(app.error_history or []) + [error_entry]

        if attempt_number < 3:
            app.next_retry_at = calculate_next_retry_time(attempt_number - 1)
            logger.info(
                f"Application {application_id} marked for retry "
                f"(count={attempt_number}, next={app.next_retry_at})"
            )
        else:
            logger.error(
                f"Application {application_id} failed permanently after max retries: "
                f"{str(e)[:200]}"
            )
        await db.commit()

        duration_ms = int((time.time() - start_time) * 1000)
        metric.end_time = datetime.now(timezone.utc)
        metric.duration_ms = duration_ms
        metric.status = "failed"
        metric.error_message = str(e)[:500]
        await db.commit()

        return {
            "status": "error",
            "message": str(e),
            "application_id": application_id,
            "retry_count": app.retry_count,
            "error_history": app.error_history,
        }
