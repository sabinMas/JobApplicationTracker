from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from datetime import datetime, timezone
from typing import List, Optional

from ..database import get_db
from ..models import Job
from ..schemas import JobCreate, JobUpdate, JobOut, ScrapeRequest
from ..services import scraper_service, cerebras_service

router = APIRouter(prefix="/api/jobs", tags=["jobs"])


@router.get("", response_model=List[JobOut])
async def list_jobs(
    status: Optional[str] = Query(None),
    source: Optional[str] = Query(None),
    db: AsyncSession = Depends(get_db),
):
    query = select(Job).order_by(Job.created_at.desc())
    if status:
        query = query.where(Job.status == status)
    if source:
        query = query.where(Job.source == source)
    result = await db.execute(query)
    return result.scalars().all()


@router.post("", response_model=JobOut)
async def create_job(data: JobCreate, db: AsyncSession = Depends(get_db)):
    job = Job(**data.model_dump())
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.post("/scrape", response_model=JobOut)
async def scrape_job(body: ScrapeRequest, db: AsyncSession = Depends(get_db)):
    """Paste any job URL → scrape page → AI extracts structured job → save to DB."""
    page_text = await scraper_service.scrape_job_page(body.url)
    extracted = await cerebras_service.extract_job(page_text)

    ats = scraper_service.detect_ats_platform(body.url)

    job = Job(
        title=extracted.get("title") or "Unknown Title",
        company=extracted.get("company") or "Unknown Company",
        location=extracted.get("location"),
        job_type=extracted.get("job_type"),
        source=ats if ats != "other" else "manual",
        source_url=body.url,
        apply_url=extracted.get("apply_url") or body.url,
        description=extracted.get("description"),
        requirements=extracted.get("requirements"),
        salary_range=extracted.get("salary_range"),
        posted_date=extracted.get("posted_date"),
        scraped_at=datetime.now(timezone.utc),
        status="discovered",
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


@router.get("/greenhouse/{company_slug}")
async def greenhouse_jobs(company_slug: str):
    """Fetch job listings from a Greenhouse company board (no auth needed)."""
    jobs = await scraper_service.fetch_greenhouse_jobs(company_slug)
    if not jobs:
        raise HTTPException(404, f"No jobs found for Greenhouse board '{company_slug}'.")
    return jobs


@router.get("/{job_id}", response_model=JobOut)
async def get_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found.")
    return job


@router.put("/{job_id}", response_model=JobOut)
async def update_job(job_id: int, data: JobUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found.")
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(job, field, value)
    await db.commit()
    await db.refresh(job)
    return job


@router.delete("/{job_id}")
async def delete_job(job_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found.")
    await db.delete(job)
    await db.commit()
    return {"ok": True}
