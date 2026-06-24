from sqlalchemy import (
    Boolean,
    Column,
    Integer,
    String,
    Text,
    DateTime,
    ForeignKey,
    JSON,
    Index,
)
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from .database import Base


class Profile(Base):
    __tablename__ = "profile"

    id = Column(Integer, primary_key=True, default=1)
    full_name = Column(String(200))
    email = Column(String(200))
    phone = Column(String(50))
    location = Column(String(200))
    linkedin_url = Column(String(500))
    github_url = Column(String(500))
    portfolio_url = Column(String(500))
    summary = Column(Text)
    skills = Column(JSON, default=list)  # ["Python", "React", ...]
    experience = Column(
        JSON, default=list
    )  # [{company, title, start, end, bullets:[]}]
    education = Column(JSON, default=list)  # [{school, degree, field, start, end, gpa}]
    certifications = Column(JSON, default=list)  # [{name, issuer, date}]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class SearchPreferences(Base):
    """Single-row (id=1) job search preferences — the definition of what a
    'good fit' means. Used by job discovery (query generation) and scoring."""

    __tablename__ = "search_preferences"

    id = Column(Integer, primary_key=True, default=1)
    target_roles = Column(
        JSON, default=list
    )  # ["Backend Engineer", "Platform Engineer"]
    niches = Column(JSON, default=list)  # ["ML infra", "browser automation"]
    must_have_keywords = Column(JSON, default=list)  # job must mention at least one
    avoid_keywords = Column(JSON, default=list)  # hard-reject if present
    salary_floor = Column(Integer, nullable=True)  # USD/year
    locations = Column(JSON, default=list)  # ["Remote", "New York, NY"]
    remote_ok = Column(Boolean, default=True)
    seniority = Column(String(50), nullable=True)  # entry/mid/senior/staff
    job_types = Column(JSON, default=list)  # ["full-time", "contract"]
    min_score_to_apply = Column(Integer, default=8)  # 1-10
    auto_submit_enabled = Column(Boolean, default=False)  # False = queue for review
    daily_application_limit = Column(Integer, default=10)
    max_jobs_per_discovery_run = Column(Integer, default=50)  # Prevent discovery flooding
    skip_previously_discovered = Column(Boolean, default=True)  # Skip duplicate URLs


class DiscoveredJobURL(Base):
    """Track job URLs we've already discovered to prevent duplicates."""

    __tablename__ = "discovered_job_urls"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_url = Column(String(1000), nullable=False, unique=True)  # URL hash for deduplication
    source = Column(String(50))  # linkedin, indeed, etc.
    discovered_at = Column(DateTime(timezone=True), server_default=func.now())
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)  # Reference to Job if created
    
    # Discovery Limits (to prevent timeouts and manage workload)
    max_jobs_per_discovery_run = Column(Integer, default=25)  # Stop discovery after N jobs found
    max_jobs_to_score_per_run = Column(Integer, default=25)  # Max scoring batch size
    score_batch_size = Column(Integer, default=5)  # Concurrent scoring limit
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class PipelineRun(Base):
    """Summary of one daily automation pipeline execution."""

    __tablename__ = "pipeline_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    trigger = Column(String(50), default="manual")  # manual / scheduled
    status = Column(String(50), default="running")  # running / completed / failed
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    finished_at = Column(DateTime(timezone=True), nullable=True)

    jobs_discovered = Column(Integer, default=0)
    jobs_scored = Column(Integer, default=0)
    jobs_enriched = Column(Integer, default=0)
    applications_prepared = Column(Integer, default=0)  # tailored docs created
    applications_submitted = Column(Integer, default=0)
    applications_queued_for_review = Column(Integer, default=0)
    errors = Column(JSON, default=list)  # [{stage, message, timestamp}]


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    company = Column(String(300), nullable=False)
    location = Column(String(200))
    job_type = Column(String(50))  # full-time, part-time, contract, internship
    source = Column(
        String(50)
    )  # linkedin, indeed, handshake, ziprecruiter, greenhouse, manual
    source_url = Column(String(1000))
    apply_url = Column(String(1000))
    description = Column(Text)
    requirements = Column(Text)
    salary_range = Column(String(200))
    posted_date = Column(String(50))
    deadline = Column(String(50))
    scraped_at = Column(DateTime(timezone=True))
    status = Column(
        String(50), default="discovered"
    )  # discovered/saved/applying/applied/dropped
    notes = Column(Text)

    # AgentCore Scoring (Phase 4)
    score = Column(Integer, nullable=True)  # 1-10 relevance score
    score_reasoning = Column(Text, nullable=True)  # Why job got this score
    score_strengths = Column(JSON, default=list)  # Positive factors
    score_concerns = Column(JSON, default=list)  # Concerns/red flags
    score_recommendation = Column(String(50), nullable=True)  # SUBMIT or SKIP
    scored_at = Column(DateTime(timezone=True), nullable=True)  # When it was scored

    # Pipeline Stage Tracking
    pipeline_stage = Column(
        String(50), 
        default="discovered"
    )  # discovered/scored/enriched/prepared/review/submitted/skipped
    pipeline_data = Column(JSON, default=dict)  # {generated_cover_letter, enrichment_notes, etc}
    enriched_at = Column(DateTime(timezone=True), nullable=True)
    enrichment_data = Column(Text, nullable=True)  # AI enrichment analysis

    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Performance indexes for Phase 4 dashboard queries
    __table_args__ = (
        Index("idx_score", score),  # Fast filtering by score range
        Index("idx_scored_at", scored_at),  # Fast filtering by when scored
        Index("idx_score_recommendation", score_recommendation),  # SUBMIT vs SKIP
        Index("idx_created_at", created_at),  # Time-based queries
        Index("idx_source", source),  # Filter by job source
        Index("idx_status", status),  # Filter by application status
        Index(
            "idx_score_created", score, created_at
        ),  # Combined for recent high-score jobs
    )

    applications = relationship(
        "Application", back_populates="job", cascade="all, delete-orphan"
    )
    documents = relationship("Document", back_populates="job")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    applied_date = Column(DateTime(timezone=True))
    status = Column(String(50), default="pending")
    # pending/applied/in_review/phone_screen/interview/offer/rejected/withdrawn
    ats_platform = Column(String(50))  # greenhouse/workday/lever/taleo/bamboohr/other
    ats_tracking_url = Column(String(1000))
    tailored_resume_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    tailored_cover_letter_id = Column(
        Integer, ForeignKey("documents.id"), nullable=True
    )
    automation_log = Column(JSON, default=list)  # [{step, status, message, timestamp}]

    # Retry tracking
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    error_history = Column(
        JSON, default=list
    )  # [{timestamp, error, attempt, error_type}]
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    job = relationship("Job", back_populates="applications")
    tailored_resume = relationship("Document", foreign_keys=[tailored_resume_id])
    tailored_cover_letter = relationship(
        "Document", foreign_keys=[tailored_cover_letter_id]
    )


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False)  # resume / cover_letter
    variant = Column(String(50), nullable=False)  # base / tailored
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    content_text = Column(Text)  # extracted text for AI use
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    job = relationship("Job", back_populates="documents")


class ApplicationMetric(Base):
    """Track each application submission attempt for analytics."""

    __tablename__ = "application_metrics"

    id = Column(Integer, primary_key=True, autoincrement=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False)
    attempt_number = Column(Integer, default=1)  # Retry count

    # Timing
    start_time = Column(DateTime(timezone=True), server_default=func.now())
    end_time = Column(DateTime(timezone=True), nullable=True)
    duration_ms = Column(Integer, nullable=True)

    # Status
    status = Column(String(50))  # success / failed / pending / submitted_unverified
    error_message = Column(Text, nullable=True)
    ats_platform_detected = Column(String(50))

    # AI metrics
    form_fields_detected = Column(Integer, nullable=True)
    fields_filled = Column(Integer, nullable=True)

    # Debug
    log_entries = Column(JSON, default=list)  # [{timestamp, step, message}]

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Dataset(Base):
    """Storage reference for results from a scraper run."""

    __tablename__ = "datasets"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # Storage
    s3_bucket = Column(String(200), nullable=False)  # jobtracker-documents-*
    s3_key = Column(
        String(500), nullable=False
    )  # runs/linkedin/2026-06-08-12345/results.jsonl
    item_count = Column(Integer, default=0)

    # Schema info
    item_schema = Column(JSON, nullable=True)  # Sample item structure

    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ScraperRun(Base):
    """Track an execution of a named actor with a config."""

    __tablename__ = "scraper_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    actor_name = Column(
        String(100), nullable=False
    )  # "linkedin", "indeed", "greenhouse"
    run_name = Column(String(200), nullable=True)  # User-friendly name
    status = Column(
        String(50), default="pending"
    )  # pending/running/success/failed/cancelled

    # Configuration
    input_config = Column(
        JSON, nullable=False
    )  # Actor-specific input (query, filters, etc.)

    # Execution
    started_at = Column(DateTime(timezone=True), nullable=True)
    finished_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, nullable=True)

    # Results
    items_scraped = Column(Integer, default=0)
    dataset_id = Column(
        Integer,
        ForeignKey("datasets.id", name="fk_scraper_run_dataset", ondelete="SET NULL"),
        nullable=True,
    )
    error_message = Column(Text, nullable=True)
    log_entries = Column(JSON, default=list)  # [{timestamp, level, message}]

    # Meta
    webhook_url = Column(String(1000), nullable=True)  # POST when done
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (Index("idx_actor_status", actor_name, status),)


class Actor(Base):
    """Registry of available actors (scrapers)."""

    __tablename__ = "actors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), unique=True, nullable=False)  # "linkedin", "indeed"
    display_name = Column(String(200))  # "LinkedIn Job Scraper"
    description = Column(Text)
    module_path = Column(String(500), nullable=False)  # "app.scrapers.linkedin"
    input_schema = Column(JSON)  # JSON schema of input_config
    output_schema = Column(JSON)  # JSON schema of scraped items
    is_enabled = Column(Integer, default=1)  # Boolean flag

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
