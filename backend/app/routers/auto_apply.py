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
    # Load application, job, and profile
    app_result = await db.execute(select(Application).where(Application.id == application_id))
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found.")

    job_result = await db.execute(select(Job).where(Job.id == app.job_id))
    job = job_result.scalar_one_or_none()
    if not job or not job.apply_url:
        raise HTTPException(400, "Job has no apply URL.")

    profile_result = await db.execute(select(Profile))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(400, "Profile not set up.")

    # Start automation session
    session_id = await playwright_service.start_session(
        application_id=application_id,
        apply_url=job.apply_url,
    )

    try:
        # Step 1: Wait for form to load
        page = playwright_service._sessions[session_id]["page"]
        form_loaded = await auto_submit.wait_for_form_load(page)

        if not form_loaded:
            raise Exception("Form did not load")

        # Step 2: Detect ATS platform
        ats_type = detect_ats_from_url(job.apply_url)

        # Step 3: Detect and fill form fields
        profile_dict = {k: v for k, v in profile.__dict__.items() if not k.startswith("_")}
        filled_fields = await auto_submit.detect_and_fill_required_fields(page, profile_dict)

        # Step 4: Upload documents if available
        resume_path = None
        cover_letter_path = None

        if app.tailored_resume_id:
            doc_result = await db.execute(select(Document).where(Document.id == app.tailored_resume_id))
            doc = doc_result.scalar_one_or_none()
            if doc:
                resume_path = doc.file_path

        if app.tailored_cover_letter_id:
            doc_result = await db.execute(select(Document).where(Document.id == app.tailored_cover_letter_id))
            doc = doc_result.scalar_one_or_none()
            if doc:
                cover_letter_path = doc.file_path

        if resume_path or cover_letter_path:
            await playwright_service.upload_documents(session_id, resume_path, cover_letter_path)

        # Step 5: Submit application
        submission_success = await auto_submit.find_and_click_submit(page, ats_type)

        if submission_success:
            # Step 6: Verify submission
            verified = await auto_submit.detect_submission_success(page)

            if verified:
                # Update application status
                app.status = "applied"
                app.applied_date = datetime.now(timezone.utc)
                await db.commit()

                await playwright_service.stop_session(session_id)

                return {
                    "status": "success",
                    "message": "Application submitted successfully!",
                    "application_id": application_id,
                }
            else:
                # Submission button clicked but success not verified - manual review needed
                return {
                    "status": "submitted_unverified",
                    "message": "Submission button clicked. Please verify in browser.",
                    "session_id": session_id,
                    "manual_review_required": True,
                }
        else:
            # Could not find or click submit button
            return {
                "status": "pending_submission",
                "message": "Form filled but submit button not found. Manual review needed.",
                "session_id": session_id,
                "manual_review_required": True,
                "filled_fields": filled_fields,
            }

    except Exception as e:
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
        await playwright_service.stop_session(session_id)
        raise HTTPException(500, f"Error detecting fields: {str(e)}")
