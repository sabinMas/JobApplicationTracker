from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..database import get_db
from ..models import Job, Profile
from ..schemas import TailorRequest, MapFieldsRequest
from ..services import ai_service
from ..services.tailoring_service import TailoringError, tailor_documents_for_job

router = APIRouter(prefix="/api/ai", tags=["ai"])


@router.post("/tailor")
async def tailor_documents(body: TailorRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate a tailored resume + cover letter for a given job.
    Saves both as Document records and returns their IDs.
    """
    job_result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found.")

    try:
        resume_doc, cl_doc = await tailor_documents_for_job(db, job)
    except TailoringError as e:
        raise HTTPException(400, str(e))

    return {
        "resume_document_id": resume_doc.id,
        "cover_letter_document_id": cl_doc.id,
        "resume_filename": resume_doc.filename,
        "cover_letter_filename": cl_doc.filename,
    }


@router.post("/map-fields")
async def map_fields(body: MapFieldsRequest, db: AsyncSession = Depends(get_db)):
    """Given form field labels, return AI-suggested profile→field mapping."""
    profile_result = await db.execute(select(Profile))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(400, "Profile not set up.")
    profile_dict = {k: v for k, v in profile.__dict__.items() if not k.startswith("_")}
    mapping = await ai_service.map_form_fields(body.field_labels, profile_dict)
    return {"mapping": mapping}
