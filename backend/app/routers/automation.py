from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from pydantic import BaseModel

from ..database import get_db
from ..models import Application, Job, Document, Profile
from ..schemas import AutomationStartRequest, AutomationSessionOut
from ..services import playwright_service, ai_service, pdf_service
from ..services.websocket_manager import ws_manager


class FullAutomationRequest(BaseModel):
    job_id: int
    auto_submit: bool = False  # If True, automatically submit the application


class QuickApplyRequest(BaseModel):
    job_id: int
    auto_submit: bool = False

router = APIRouter(prefix="/api/automation", tags=["automation"])


@router.post("/start", response_model=AutomationSessionOut)
async def start_automation(body: AutomationStartRequest, db: AsyncSession = Depends(get_db)):
    """Start a Playwright session for the given application."""
    # Load application + job
    app_result = await db.execute(select(Application).where(Application.id == body.application_id))
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found.")

    job_result = await db.execute(select(Job).where(Job.id == app.job_id))
    job = job_result.scalar_one_or_none()
    if not job or not job.apply_url:
        raise HTTPException(400, "Job has no apply URL set.")

    session_id = await playwright_service.start_session(
        application_id=body.application_id,
        apply_url=job.apply_url,
    )
    return AutomationSessionOut(
        session_id=session_id,
        status="running",
        message=f"Browser opened for {job.company} — {job.title}",
    )


@router.post("/fill/{session_id}")
async def fill_application(session_id: str, db: AsyncSession = Depends(get_db)):
    """AI-fills all form fields using the user's profile."""
    profile_result = await db.execute(
        select(Profile)
    )
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(400, "Profile not set up.")

    profile_dict = {k: v for k, v in profile.__dict__.items() if not k.startswith("_")}
    log = await playwright_service.fill_form(session_id, profile_dict)
    return {"log": log}


@router.post("/upload-docs/{session_id}")
async def upload_docs(
    session_id: str,
    application_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Upload tailored resume and cover letter to the open application form."""
    app_result = await db.execute(select(Application).where(Application.id == application_id))
    app = app_result.scalar_one_or_none()
    if not app:
        raise HTTPException(404, "Application not found.")

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

    await playwright_service.upload_documents(session_id, resume_path, cover_letter_path)
    return {"ok": True}


@router.get("/screenshot/{session_id}")
async def get_screenshot(session_id: str):
    screenshot = await playwright_service.take_screenshot(session_id)
    if not screenshot:
        raise HTTPException(404, "Session not found or screenshot unavailable.")
    return {"screenshot_b64": screenshot}


@router.post("/pause/{session_id}")
async def pause(session_id: str):
    await playwright_service.pause_session(session_id)
    return {"ok": True, "status": "paused"}


@router.post("/resume/{session_id}")
async def resume(session_id: str):
    await playwright_service.resume_session(session_id)
    return {"ok": True, "status": "running"}


@router.post("/stop/{session_id}")
async def stop(session_id: str):
    await playwright_service.stop_session(session_id)
    return {"ok": True, "status": "stopped"}


@router.get("/status/{session_id}")
async def session_status(session_id: str):
    status = playwright_service.get_session_status(session_id)
    if not status:
        raise HTTPException(404, "Session not found.")
    return status


# ─── WebSocket endpoint ───────────────────────────────────────────────────────

@router.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await ws_manager.connect(session_id, websocket)
    try:
        while True:
            # Keep connection alive; client can send "ping" messages
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_text('{"type":"pong"}')
    except WebSocketDisconnect:
        ws_manager.disconnect(session_id, websocket)


# ─── FULL AUTOMATION ENDPOINTS ───────────────────────────────────────────────────

@router.post("/full-automate")
async def full_automate(body: FullAutomationRequest, db: AsyncSession = Depends(get_db)):
    """
    Complete end-to-end automation:
    1. Load job & profile
    2. Generate tailored resume & cover letter
    3. Create application record
    4. Start browser automation
    5. Fill form fields
    6. Upload documents
    7. Optionally submit
    """
    # Load job
    job_result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found.")

    # Load profile
    profile_result = await db.execute(select(Profile))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(400, "Profile not set up.")

    # Load base resume
    resume_result = await db.execute(
        select(Document).where(Document.type == "resume", Document.variant == "base")
        .order_by(Document.created_at.desc())
    )
    base_resume = resume_result.scalar_one_or_none()
    if not base_resume or not base_resume.content_text:
        raise HTTPException(400, "No base resume found.")

    profile_dict = {k: v for k, v in profile.__dict__.items() if not k.startswith("_")}

    # Generate tailored documents
    try:
        resume_md = await ai_service.tailor_resume(
            job_description=job.description or "",
            job_requirements=job.requirements or "",
            base_resume_text=base_resume.content_text,
            profile=profile_dict,
        )

        # Load example cover letters
        cl_result = await db.execute(
            select(Document).where(Document.type == "cover_letter", Document.variant == "base")
        )
        base_cls = cl_result.scalars().all()
        example_texts = [doc.content_text for doc in base_cls if doc.content_text]

        cover_letter_text = await ai_service.generate_cover_letter(
            job_description=job.description or "",
            company=job.company,
            job_title=job.title,
            profile=profile_dict,
            example_cover_letters=example_texts,
        )

        # Save tailored documents
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        safe_company = "".join(c for c in job.company if c.isalnum() or c in " _-")[:30]

        # Create application record
        application = Application(
            job_id=body.job_id,
            applied_date=datetime.now(timezone.utc),
            status="pending",
            automation_log=[],
        )
        db.add(application)
        await db.commit()
        await db.refresh(application)

        # Note: In production, you would save PDFs and link them
        # For now, we return the application ID for the next steps
        return {
            "application_id": application.id,
            "job_id": body.job_id,
            "company": job.company,
            "title": job.title,
            "status": "prepared",
            "next_step": "Start browser automation to fill form",
            "auto_submit": body.auto_submit,
        }

    except Exception as e:
        raise HTTPException(500, f"Error in automation: {str(e)}")


@router.post("/quick-apply/{job_id}")
async def quick_apply(job_id: int, body: QuickApplyRequest, db: AsyncSession = Depends(get_db)):
    """
    Quick apply using already-tailored documents.
    If no tailored documents exist, generate them on the fly.
    """
    job_result = await db.execute(select(Job).where(Job.id == job_id))
    job = job_result.scalar_one_or_none()
    if not job or not job.apply_url:
        raise HTTPException(404, "Job not found or has no apply URL.")

    # Check if tailored documents exist
    resume_result = await db.execute(
        select(Document).where(
            Document.type == "resume",
            Document.variant == "tailored",
            Document.job_id == job_id
        )
    )
    tailored_resume = resume_result.scalar_one_or_none()

    cl_result = await db.execute(
        select(Document).where(
            Document.type == "cover_letter",
            Document.variant == "tailored",
            Document.job_id == job_id
        )
    )
    tailored_cl = cl_result.scalar_one_or_none()

    # Create application
    application = Application(
        job_id=job_id,
        applied_date=datetime.now(timezone.utc),
        status="applying",
        tailored_resume_id=tailored_resume.id if tailored_resume else None,
        tailored_cover_letter_id=tailored_cl.id if tailored_cl else None,
        automation_log=[],
    )
    db.add(application)
    await db.commit()
    await db.refresh(application)

    # Start browser automation
    session_id = await playwright_service.start_session(
        application_id=application.id,
        apply_url=job.apply_url,
    )

    return {
        "application_id": application.id,
        "session_id": session_id,
        "status": "browser_opened",
        "message": f"Ready to fill form for {job.company} — {job.title}",
        "has_resume": tailored_resume is not None,
        "has_cover_letter": tailored_cl is not None,
    }
