"""
Tailored-document generation for a job: resume + cover letter.

Extracted from the ai router so both the API endpoint and the automation
pipeline can use it.
"""

import os
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Document, Job, Profile
from . import ai_service, pdf_service

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent.parent.parent.parent / "data"))


class TailoringError(Exception):
    """Raised when prerequisites for tailoring are missing."""


def profile_to_dict(profile: Profile) -> dict:
    return {
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


async def tailor_documents_for_job(db: AsyncSession, job: Job) -> tuple[Document, Document]:
    """Generate a tailored resume and cover letter for the job, persist both as
    Document records, and return (resume_doc, cover_letter_doc).

    Raises TailoringError when the profile or base resume is missing.
    """
    profile = (await db.execute(select(Profile))).scalar_one_or_none()
    if not profile:
        raise TailoringError("Profile not set up.")
    profile_dict = profile_to_dict(profile)

    base_resume = (
        await db.execute(
            select(Document)
            .where(Document.type == "resume", Document.variant == "base")
            .order_by(Document.created_at.desc())
        )
    ).scalars().first()
    if not base_resume or not base_resume.content_text:
        raise TailoringError("No base resume found.")

    base_cls = (
        await db.execute(
            select(Document).where(
                Document.type == "cover_letter", Document.variant == "base"
            )
        )
    ).scalars().all()
    example_texts = [doc.content_text for doc in base_cls if doc.content_text]

    resume_md = await ai_service.tailor_resume(
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

    cover_letter_text = await ai_service.generate_cover_letter(
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
    return resume_doc, cl_doc
