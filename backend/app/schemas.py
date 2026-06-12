from pydantic import BaseModel
from typing import Optional, List
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


# ─── Search Preferences ──────────────────────────────────────────────────────

class SearchPreferencesUpdate(BaseModel):
    target_roles: Optional[List[str]] = None
    niches: Optional[List[str]] = None
    must_have_keywords: Optional[List[str]] = None
    avoid_keywords: Optional[List[str]] = None
    salary_floor: Optional[int] = None
    locations: Optional[List[str]] = None
    remote_ok: Optional[bool] = None
    seniority: Optional[str] = None
    job_types: Optional[List[str]] = None
    min_score_to_apply: Optional[int] = None
    auto_submit_enabled: Optional[bool] = None
    daily_application_limit: Optional[int] = None


class SearchPreferencesOut(SearchPreferencesUpdate):
    id: int
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


# ─── Pipeline ────────────────────────────────────────────────────────────────

class PipelineRunOut(BaseModel):
    id: int
    trigger: str
    status: str
    started_at: Optional[datetime] = None
    finished_at: Optional[datetime] = None
    jobs_discovered: int
    jobs_scored: int
    jobs_enriched: int
    applications_prepared: int
    applications_submitted: int
    applications_queued_for_review: int
    errors: Optional[List[dict]] = None

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


# ─── Phase 4: Dashboard & Scoring ────────────────────────────────────────────

class ScoringStats(BaseModel):
    """Job scoring statistics"""
    total_jobs: int
    total_scored: int
    percentage_scored: float
    avg_score: Optional[float] = None
    min_score: Optional[int] = None
    max_score: Optional[int] = None
    score_distribution: dict  # {score: count, ...}


class JobByScoreOut(BaseModel):
    """Job with scoring details"""
    id: int
    title: str
    company: str
    location: Optional[str] = None
    score: Optional[int] = None
    score_reasoning: Optional[str] = None
    score_strengths: Optional[List[str]] = None
    score_concerns: Optional[List[str]] = None
    score_recommendation: Optional[str] = None
    apply_url: Optional[str] = None
    source: str


class HighScoreJobsOut(BaseModel):
    """Response for high-scoring jobs filter"""
    total_available: int
    jobs: List[JobByScoreOut]
    min_score_threshold: int


class DashboardMetricsOut(BaseModel):
    """Comprehensive dashboard metrics"""
    period_days: int
    timestamp: datetime
    
    # Job discovery metrics
    total_jobs_discovered: int
    jobs_by_source: dict
    
    # Application metrics
    total_applications: int
    applications_by_status: dict
    applications_by_ats: dict
    
    # Scoring metrics
    scoring_stats: ScoringStats
    
    # Performance metrics
    successful_applications: int
    failed_applications: int
    success_rate: float
    
    # Timing metrics
    avg_time_to_apply_minutes: Optional[float] = None


class ScoringHealthOut(BaseModel):
    """Scoring system health and status"""
    total_jobs: int
    scored_jobs: int
    unscored_jobs: int
    percentage_scored: float
    score_distribution: dict
    avg_score: Optional[float] = None
    high_score_count: int  # score >= 8
    low_score_count: int   # score <= 4
    timestamp: datetime


class ScoreJobsRequest(BaseModel):
    """Request to score unscored jobs"""
    min_date: Optional[datetime] = None
    limit: int = 100
    status: Optional[str] = None


class ScoreJobsOut(BaseModel):
    """Response from batch scoring operation"""
    jobs_processed: int
    jobs_newly_scored: int
    jobs_skipped: int
    errors: int
    score_distribution: dict
    avg_score: Optional[float] = None


class HighScoreFilterRequest(BaseModel):
    """Request to filter high-score jobs"""
    min_score: int = 8
    skip: int = 0
    limit: int = 100


class ApplicationTimelineOut(BaseModel):
    """Time-series application data"""
    date: str
    applications_count: int
    successful_count: Optional[int] = None
    failed_count: Optional[int] = None


class ApplicationTimelineResponse(BaseModel):
    """Response with timeline data"""
    period_days: int
    data: List[ApplicationTimelineOut]


class StatusBreakdownOut(BaseModel):
    """Application status distribution"""
    status: str
    count: int
    percentage: float


class StatusBreakdownResponse(BaseModel):
    """Response with status breakdown"""
    total_applications: int
    breakdown: List[StatusBreakdownOut]


class HealthCheckOut(BaseModel):
    """Health check response"""
    status: str
    service: str
    db_initialized: bool
    timestamp: datetime

