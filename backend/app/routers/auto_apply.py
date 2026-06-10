"""
Fully automated job application endpoints.

In production (AUTO_APPLY_MODE=queue, the Lambda API) submissions are enqueued
to SQS and executed by the ECS worker, where Playwright lives. In development
(AUTO_APPLY_MODE=inline, the default) they run in-process.
"""
import os

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Application, Job
from ..services import auto_submit, playwright_service
from ..services.auto_apply_service import (
    AutoApplyPreconditionError,
    run_full_auto_apply,
)
from ..logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auto-apply", tags=["auto-apply"])

AUTO_APPLY_MODE = os.getenv("AUTO_APPLY_MODE", "inline")  # inline | queue


@router.post("/full/{application_id}")
async def full_auto_apply(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Fully automated job application with automatic retry on failure.

    queue mode: enqueues the task for the ECS worker and returns immediately.
    inline mode: runs the submission in-process (development only).
    """
    if AUTO_APPLY_MODE == "queue":
        app = (
            await db.execute(select(Application).where(Application.id == application_id))
        ).scalar_one_or_none()
        if not app:
            raise HTTPException(404, "Application not found.")
        if not app.tailored_resume_id:
            raise HTTPException(
                400, "Application has no tailored resume. Tailor documents first."
            )

        from ..services.pipeline import _enqueue_auto_apply

        await _enqueue_auto_apply(application_id)
        return {
            "status": "queued",
            "message": "Auto-apply task enqueued; the worker will process it shortly.",
            "application_id": application_id,
        }

    try:
        return await run_full_auto_apply(db, application_id)
    except AutoApplyPreconditionError as e:
        status = 404 if "not found" in str(e).lower() else 400
        raise HTTPException(status, str(e))


@router.post("/detect-fields/{application_id}")
async def detect_required_fields(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a session and detect which fields are required on the application form.
    Useful for understanding what info is needed before full automation.
    """
    logger.info(f"Detecting required fields for application {application_id}")

    app_result = await db.execute(select(Application).where(Application.id == application_id))
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found.")

    job_result = await db.execute(select(Job).where(Job.id == app.job_id))
    job = job_result.scalar_one_or_none()
    if not job or not job.apply_url:
        raise HTTPException(400, "Job has no apply URL.")

    session_id = await playwright_service.start_session(
        application_id=application_id,
        apply_url=job.apply_url,
    )

    try:
        page = playwright_service._sessions[session_id]["page"]
        form_loaded = await auto_submit.wait_for_form_load(page)
        if not form_loaded:
            raise Exception("Form did not load")

        required_fields = await auto_submit.handle_required_fields_indicator(page)
        return {
            "session_id": session_id,
            "required_fields": required_fields,
            "status": "ready_for_review",
        }
    except Exception as e:
        logger.error(f"Error detecting fields for application {application_id}: {e}")
        await playwright_service.stop_session(session_id)
        raise HTTPException(500, f"Error detecting fields: {str(e)}")
