from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pathlib import Path
import os
from datetime import datetime, timezone

from ..database import get_db
from ..models import Job, Document, Profile, Application
from ..schemas import TailorRequest, MapFieldsRequest
from ..services import cerebras_service, pdf_service

router = APIRouter(prefix="/api/ai", tags=["ai"])

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent.parent.parent.parent / "data"))


@router.post("/tailor")
async def tailor_documents(body: TailorRequest, db: AsyncSession = Depends(get_db)):
    """
    Generate a tailored resume + cover letter for a given job.
    Saves both as Document records and returns their IDs.
    """
    # Load job
    job_result = await db.execute(select(Job).where(Job.id == body.job_id))
    job = job_result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found.")

    # Load user profile
    profile_result = await db.execute(select(Profile))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(400, "Profile not set up. Please complete your profile first.")

    profile_dict = {
        "full_name": profile.full_name,
        "email": profile.email,
        "phone": profile.phone,
        "location": profile.location,
        "linkedin_url": profile.linkedin_url,
        "github_url": profile.github_url,
        "portfolio_url": profile.portfolio_url,
        "summary": profile.summary,
        "skills": profile.skills or [],
        "experience": profile.experience or [],
        "education": profile.education or [],
        "certifications": profile.certifications or [],
    }

    # Load base resume text
    resume_result = await db.execute(
        select(Document).where(Document.type == "resume", Document.variant == "base")
        .order_by(Document.created_at.desc())
    )
    base_resume = resume_result.scalar_one_or_none()
    if not base_resume or not base_resume.content_text:
        raise HTTPException(400, "No base resume found. Please upload your resume in Documents.")

    # Load example cover letters
    cl_result = await db.execute(
        select(Document).where(Document.type == "cover_letter", Document.variant == "base")
    )
    base_cls = cl_result.scalars().all()
    example_texts = [doc.content_text for doc in base_cls if doc.content_text]

    # --- Generate tailored resume ---
    resume_md = await cerebras_service.tailor_resume(
        job_description=job.description or "",
        job_requirements=job.requirements or "",
        base_resume_text=base_resume.content_text,
        profile=profile_dict,
    )

    ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    safe_company = "".join(c for c in job.company if c.isalnum() or c in " _-")[:30]
    resume_filename = f"resume_{safe_company}_{ts}.pdf"
    resume_path = DATA_DIR / "generated" / "tailored_resumes" / resume_filename
    pdf_service.markdown_to_pdf(resume_md, str(resume_path), doc_type="resume")

    resume_doc = Document(
        type="resume",
        variant="tailored",
        job_id=job.id,
        filename=resume_filename,
        file_path=str(resume_path),
        content_text=resume_md,
    )
    db.add(resume_doc)

    # --- Generate tailored cover letter ---
    cover_letter_text = await cerebras_service.generate_cover_letter(
        job_description=job.description or "",
        company=job.company,
        job_title=job.title,
        profile=profile_dict,
        example_cover_letters=example_texts,
    )

    cl_filename = f"coverletter_{safe_company}_{ts}.pdf"
    cl_path = DATA_DIR / "generated" / "tailored_cover_letters" / cl_filename
    pdf_service.markdown_to_pdf(cover_letter_text, str(cl_path), doc_type="cover_letter")

    cl_doc = Document(
        type="cover_letter",
        variant="tailored",
        job_id=job.id,
        filename=cl_filename,
        file_path=str(cl_path),
        content_text=cover_letter_text,
    )
    db.add(cl_doc)
    await db.commit()
    await db.refresh(resume_doc)
    await db.refresh(cl_doc)

    return {
        "resume_document_id": resume_doc.id,
        "cover_letter_document_id": cl_doc.id,
        "resume_filename": resume_filename,
        "cover_letter_filename": cl_filename,
    }


@router.post("/map-fields")
async def map_fields(body: MapFieldsRequest, db: AsyncSession = Depends(get_db)):
    """Given form field labels, return AI-suggested profile→field mapping."""
    profile_result = await db.execute(select(Profile))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        raise HTTPException(400, "Profile not set up.")
    profile_dict = {k: v for k, v in profile.__dict__.items() if not k.startswith("_")}
    mapping = await cerebras_service.map_form_fields(body.field_labels, profile_dict)
    return {"mapping": mapping}
