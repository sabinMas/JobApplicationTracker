"""
Fully automated job application endpoint.
Uses intelligent routing to select appropriate ATS handler (Greenhouse API, generic form filling, etc).
Handles automatic retry on failure with exponential backoff.
"""
import time
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from ..database import get_db
from ..models import Application, Job, Profile, Document, ApplicationMetric
from ..schemas import AutomationStartRequest
from ..services import playwright_service, auto_submit
from ..services.ats_integration import detect_ats_from_url
from ..services.ats_routers import route_and_submit
from ..services.retry_service import execute_with_retry, calculate_next_retry_time
from ..logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auto-apply", tags=["auto-apply"])


async def _perform_auto_apply(
    application_id: int,
    job: Job,
    profile: Profile,
    app: Application,
    db: AsyncSession,
) -> dict:
    """
    Core auto-apply logic using intelligent routing.
    
    Routes to appropriate ATS handler (Greenhouse API, form filling, etc).
    Returns dict with status, message, and details.
    """
    
    # Get document paths
    resume_path = None
    cover_letter_path = None

    if app.tailored_resume_id:
        doc_result = await db.execute(select(Document).where(Document.id == app.tailored_resume_id))
        doc = doc_result.scalar_one_or_none()
        if doc:
            resume_path = doc.file_path
            logger.debug("Resume document found", extra_fields={
                "application_id": application_id,
                "document_id": doc.id,
            })

    if app.tailored_cover_letter_id:
        doc_result = await db.execute(select(Document).where(Document.id == app.tailored_cover_letter_id))
        doc = doc_result.scalar_one_or_none()
        if doc:
            cover_letter_path = doc.file_path
            logger.debug("Cover letter document found", extra_fields={
                "application_id": application_id,
                "document_id": doc.id,
            })

    # Convert profile to dict for routing
    profile_dict = {k: v for k, v in profile.__dict__.items() if not k.startswith("_")}
    
    logger.debug("Routing application to appropriate handler", extra_fields={
        "application_id": application_id,
        "job_url": job.apply_url,
    })
    
    # Use intelligent routing to find appropriate handler
    result = await route_and_submit(
        application_id=application_id,
        job_url=job.apply_url,
        profile=profile_dict,
        resume_path=resume_path or "",
        cover_letter_path=cover_letter_path or "",
    )
    
    # If successful, update application status
    if result.get("status") == "success":
        app.status = "applied"
        app.applied_date = datetime.now(timezone.utc)
        await db.commit()
        
        logger.info("Application status updated to 'applied'", extra_fields={
            "application_id": application_id,
            "timestamp": app.applied_date.isoformat(),
        })
    
    return result


@router.post("/full/{application_id}")
async def full_auto_apply(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Fully automated job application with automatic retry on failure.
    
    Uses intelligent routing to select appropriate ATS handler.
    Automatically retries up to 3 times with exponential backoff on failure.
    
    Tracks metrics and error history for observability.
    """
    logger.info("Starting full auto-apply", extra_fields={"application_id": application_id})
    start_time = time.time()
    
    # Load application, job, and profile
    app_result = await db.execute(select(Application).where(Application.id == application_id))
    app = app_result.scalar_one_or_none()
    if not app:
        logger.error("Application not found", extra_fields={"application_id": application_id})
        raise HTTPException(404, "Application not found.")

    job_result = await db.execute(select(Job).where(Job.id == app.job_id))
    job = job_result.scalar_one_or_none()
    if not job or not job.apply_url:
        logger.error("Job has no apply URL", extra_fields={"application_id": application_id, "job_id": app.job_id})
        raise HTTPException(400, "Job has no apply URL.")

    profile_result = await db.execute(select(Profile))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        logger.error("Profile not set up", extra_fields={"application_id": application_id})
        raise HTTPException(400, "Profile not set up.")

    logger.info("Loading job details", extra_fields={
        "application_id": application_id,
        "job_id": job.id,
        "company": job.company,
        "title": job.title,
        "url": job.apply_url,
    })

    # Determine attempt number
    attempt_number = app.retry_count + 1
    metric = None

    try:
        # Create metric record
        metric = ApplicationMetric(
            application_id=application_id,
            attempt_number=attempt_number,
            start_time=datetime.now(timezone.utc),
            ats_platform_detected=detect_ats_from_url(job.apply_url),
        )
        db.add(metric)
        await db.commit()
        await db.refresh(metric)

        # Execute core logic with retry
        async def retry_callback(attempt, wait_time, error):
            logger.warning(
                f"Retrying auto-apply (retry {attempt}), waiting {wait_time}s",
                extra_fields={
                    "application_id": application_id,
                    "retry_attempt": attempt,
                    "wait_seconds": wait_time,
                    "error": str(error)[:100],
                }
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

        # Update metrics
        duration_ms = int((time.time() - start_time) * 1000)
        metric.end_time = datetime.now(timezone.utc)
        metric.duration_ms = duration_ms
        metric.status = result["status"]
        metric.form_fields_detected = result.get("fields_filled", 0)
        metric.fields_filled = result.get("fields_filled", 0)
        await db.commit()

        logger.info("Auto-apply completed successfully", extra_fields={
            "application_id": application_id,
            "status": result["status"],
            "duration_ms": duration_ms,
            "attempt_number": attempt_number,
        })

        return result

    except Exception as e:
        # Update application with retry info
        app.retry_count = attempt_number
        app.last_error = str(e)[:500]
        
        # Add to error history
        error_entry = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "error": str(e)[:200],
            "attempt": attempt_number,
            "error_type": type(e).__name__,
        }
        app.error_history.append(error_entry)
        
        # Set next retry time if under max attempts
        if attempt_number < 3:
            app.next_retry_at = calculate_next_retry_time(attempt_number - 1)
            logger.info(
                "Application marked for retry",
                extra_fields={
                    "application_id": application_id,
                    "retry_count": attempt_number,
                    "next_retry_at": app.next_retry_at.isoformat(),
                }
            )
        else:
            logger.error(
                "Application failed permanently after max retries",
                extra_fields={
                    "application_id": application_id,
                    "max_retries": 3,
                    "final_error": str(e)[:200],
                }
            )
        
        await db.commit()

        # Update metric
        if metric:
            duration_ms = int((time.time() - start_time) * 1000)
            metric.end_time = datetime.now(timezone.utc)
            metric.duration_ms = duration_ms
            metric.status = "failed"
            metric.error_message = str(e)[:500]
            await db.commit()

        logger.error("Exception during auto-apply", extra_fields={
            "application_id": application_id,
            "error": str(e),
            "error_type": type(e).__name__,
            "attempt": attempt_number,
        }, exc_info=True)

        return {
            "status": "error",
            "message": str(e),
            "application_id": application_id,
            "retry_count": app.retry_count,
            "error_history": app.error_history,
        }


@router.post("/detect-fields/{application_id}")
async def detect_required_fields(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Start a session and detect which fields are required on the application form.
    Useful for understanding what info is needed before full automation.
    """
    logger.info("Detecting required fields", extra_fields={"application_id": application_id})
    
    app_result = await db.execute(select(Application).where(Application.id == application_id))
    app = app_result.scalar_one_or_none()
    if not app:
        logger.error("Application not found", extra_fields={"application_id": application_id})
        raise HTTPException(404, "Application not found.")

    job_result = await db.execute(select(Job).where(Job.id == app.job_id))
    job = job_result.scalar_one_or_none()
    if not job or not job.apply_url:
        logger.error("Job has no apply URL", extra_fields={"application_id": application_id, "job_id": app.job_id})
        raise HTTPException(400, "Job has no apply URL.")

    session_id = await playwright_service.start_session(
        application_id=application_id,
        apply_url=job.apply_url,
    )
    logger.info("Browser session started for field detection", extra_fields={
        "application_id": application_id,
        "session_id": session_id,
    })

    try:
        page = playwright_service._sessions[session_id]["page"]
        form_loaded = await auto_submit.wait_for_form_load(page)

        if not form_loaded:
            logger.error("Form did not load during field detection", extra_fields={
                "application_id": application_id,
                "session_id": session_id,
            })
            raise Exception("Form did not load")

        required_fields = await auto_submit.handle_required_fields_indicator(page)
        logger.info("Required fields detected", extra_fields={
            "application_id": application_id,
            "session_id": session_id,
            "field_count": len(required_fields),
            "fields": required_fields,
        })

        return {
            "session_id": session_id,
            "required_fields": required_fields,
            "status": "ready_for_review",
        }
    except Exception as e:
        logger.error("Error detecting fields", extra_fields={
            "application_id": application_id,
            "session_id": session_id,
            "error": str(e),
        })
        await playwright_service.stop_session(session_id)
        raise HTTPException(500, f"Error detecting fields: {str(e)}")
