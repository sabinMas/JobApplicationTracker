from pydantic import BaseModel, HttpUrl
from typing import Optional, List, Any
from datetime import datetime


# ─── Profile ────────────────────────────────────────────────────────────────

class ProfileUpdate(BaseModel):
    full_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    summary: Optional[str] = None
    skills: Optional[List[str]] = None
    experience: Optional[List[dict]] = None
    education: Optional[List[dict]] = None
    certifications: Optional[List[dict]] = None


class ProfileOut(ProfileUpdate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Job ─────────────────────────────────────────────────────────────────────

class JobCreate(BaseModel):
    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    source: Optional[str] = "manual"
    source_url: Optional[str] = None
    apply_url: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_range: Optional[str] = None
    posted_date: Optional[str] = None
    deadline: Optional[str] = None
    notes: Optional[str] = None


class JobUpdate(BaseModel):
    title: Optional[str] = None
    company: Optional[str] = None
    location: Optional[str] = None
    job_type: Optional[str] = None
    source: Optional[str] = None
    source_url: Optional[str] = None
    apply_url: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_range: Optional[str] = None
    posted_date: Optional[str] = None
    deadline: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None


class JobOut(JobCreate):
    id: int
    status: str = "discovered"
    scraped_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ScrapeRequest(BaseModel):
    url: str


# ─── Application ─────────────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    job_id: int
    notes: Optional[str] = None


class ApplicationUpdate(BaseModel):
    status: Optional[str] = None
    ats_platform: Optional[str] = None
    ats_tracking_url: Optional[str] = None
    tailored_resume_id: Optional[int] = None
    tailored_cover_letter_id: Optional[int] = None
    notes: Optional[str] = None


class ApplicationOut(BaseModel):
    id: int
    job_id: int
    applied_date: Optional[datetime] = None
    status: str
    ats_platform: Optional[str] = None
    ats_tracking_url: Optional[str] = None
    tailored_resume_id: Optional[int] = None
    tailored_cover_letter_id: Optional[int] = None
    automation_log: Optional[List[dict]] = None
    notes: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Document ────────────────────────────────────────────────────────────────

class DocumentOut(BaseModel):
    id: int
    type: str
    variant: str
    job_id: Optional[int] = None
    filename: str
    file_path: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TailorRequest(BaseModel):
    job_id: int


class MapFieldsRequest(BaseModel):
    field_labels: List[str]


# ─── Automation ──────────────────────────────────────────────────────────────

class AutomationStartRequest(BaseModel):
    application_id: int


class AutomationSessionOut(BaseModel):
    session_id: str
    status: str
    message: str


# ─── WebSocket event ─────────────────────────────────────────────────────────

class WSEvent(BaseModel):
    session_id: str
    step: str
    status: str   # running / paused / done / error
    message: str
    screenshot_b64: Optional[str] = None
    timestamp: Optional[datetime] = None
