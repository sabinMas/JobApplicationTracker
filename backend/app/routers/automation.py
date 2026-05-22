from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Application, Job, Document, Profile
from ..schemas import AutomationStartRequest, AutomationSessionOut
from ..services import playwright_service
from ..services.websocket_manager import ws_manager

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
