"""
Fully automated job application endpoint.
Handles end-to-end automation: form filling, document upload, submission, and status tracking.
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone

from ..database import get_db
from ..models import Application, Job, Profile, Document
from ..schemas import AutomationStartRequest
from ..services import playwright_service, auto_submit
from ..services.ats_integration import detect_ats_from_url
from ..logging_config import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/api/auto-apply", tags=["auto-apply"])


@router.post("/full/{application_id}")
async def full_auto_apply(
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """
    Fully automated job application:
    1. Start browser session
    2. Generate tailored documents
    3. Fill all form fields
    4. Upload documents
    5. Submit application
    6. Update status
    """
    logger.info("Starting full auto-apply", extra_fields={"application_id": application_id})
    
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

    # Start automation session
    session_id = await playwright_service.start_session(
        application_id=application_id,
        apply_url=job.apply_url,
    )
    logger.info("Browser session started", extra_fields={
        "application_id": application_id,
        "session_id": session_id,
    })

    try:
        # Step 1: Wait for form to load
        page = playwright_service._sessions[session_id]["page"]
        logger.debug("Waiting for form to load", extra_fields={"application_id": application_id, "session_id": session_id})
        form_loaded = await auto_submit.wait_for_form_load(page)

        if not form_loaded:
            logger.error("Form did not load", extra_fields={"application_id": application_id, "session_id": session_id})
            raise Exception("Form did not load")

        logger.info("Form loaded successfully", extra_fields={"application_id": application_id, "session_id": session_id})

        # Step 2: Detect ATS platform
        ats_type = detect_ats_from_url(job.apply_url)
        logger.info("ATS platform detected", extra_fields={
            "application_id": application_id,
            "session_id": session_id,
            "ats_platform": ats_type,
        })

        # Step 3: Detect and fill form fields
        profile_dict = {k: v for k, v in profile.__dict__.items() if not k.startswith("_")}
        logger.debug("Filling form fields", extra_fields={"application_id": application_id, "session_id": session_id})
        filled_fields = await auto_submit.detect_and_fill_required_fields(page, profile_dict)
        logger.info("Form fields filled", extra_fields={
            "application_id": application_id,
            "session_id": session_id,
            "fields_filled": len(filled_fields),
        })

        # Step 4: Upload documents if available
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
                    "file_path": resume_path,
                })

        if app.tailored_cover_letter_id:
            doc_result = await db.execute(select(Document).where(Document.id == app.tailored_cover_letter_id))
            doc = doc_result.scalar_one_or_none()
            if doc:
                cover_letter_path = doc.file_path
                logger.debug("Cover letter document found", extra_fields={
                    "application_id": application_id,
                    "document_id": doc.id,
                    "file_path": cover_letter_path,
                })

        if resume_path or cover_letter_path:
            logger.info("Uploading documents", extra_fields={
                "application_id": application_id,
                "session_id": session_id,
                "resume": bool(resume_path),
                "cover_letter": bool(cover_letter_path),
            })
            await playwright_service.upload_documents(session_id, resume_path, cover_letter_path)

        # Step 5: Submit application
        logger.debug("Finding and clicking submit button", extra_fields={
            "application_id": application_id,
            "session_id": session_id,
        })
        submission_success = await auto_submit.find_and_click_submit(page, ats_type)

        if submission_success:
            logger.info("Submit button clicked", extra_fields={"application_id": application_id, "session_id": session_id})
            
            # Step 6: Verify submission
            verified = await auto_submit.detect_submission_success(page)

            if verified:
                logger.info("Submission verified as successful", extra_fields={"application_id": application_id})
                
                # Update application status
                app.status = "applied"
                app.applied_date = datetime.now(timezone.utc)
                await db.commit()

                await playwright_service.stop_session(session_id)

                logger.info("Application status updated to 'applied'", extra_fields={
                    "application_id": application_id,
                    "timestamp": app.applied_date.isoformat(),
                })

                return {
                    "status": "success",
                    "message": "Application submitted successfully!",
                    "application_id": application_id,
                }
            else:
                logger.warning("Submission button clicked but success not verified", extra_fields={
                    "application_id": application_id,
                    "session_id": session_id,
                })
                # Submission button clicked but success not verified - manual review needed
                return {
                    "status": "submitted_unverified",
                    "message": "Submission button clicked. Please verify in browser.",
                    "session_id": session_id,
                    "manual_review_required": True,
                }
        else:
            logger.warning("Submit button not found", extra_fields={
                "application_id": application_id,
                "session_id": session_id,
            })
            # Could not find or click submit button
            return {
                "status": "pending_submission",
                "message": "Form filled but submit button not found. Manual review needed.",
                "session_id": session_id,
                "manual_review_required": True,
                "filled_fields": filled_fields,
            }

    except Exception as e:
        logger.error("Exception during auto-apply", extra_fields={
            "application_id": application_id,
            "session_id": session_id,
            "error": str(e),
            "error_type": type(e).__name__,
        }, exc_info=True)
        
        await playwright_service.stop_session(session_id)
        return {
            "status": "error",
            "message": str(e),
            "application_id": application_id,
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
