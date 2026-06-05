from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
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
    skills = Column(JSON, default=list)           # ["Python", "React", ...]
    experience = Column(JSON, default=list)       # [{company, title, start, end, bullets:[]}]
    education = Column(JSON, default=list)        # [{school, degree, field, start, end, gpa}]
    certifications = Column(JSON, default=list)   # [{name, issuer, date}]
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())


class Job(Base):
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(300), nullable=False)
    company = Column(String(300), nullable=False)
    location = Column(String(200))
    job_type = Column(String(50))   # full-time, part-time, contract, internship
    source = Column(String(50))     # linkedin, indeed, handshake, ziprecruiter, greenhouse, manual
    source_url = Column(String(1000))
    apply_url = Column(String(1000))
    description = Column(Text)
    requirements = Column(Text)
    salary_range = Column(String(200))
    posted_date = Column(String(50))
    deadline = Column(String(50))
    scraped_at = Column(DateTime(timezone=True))
    status = Column(String(50), default="discovered")  # discovered/saved/applying/applied/dropped
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    applications = relationship("Application", back_populates="job", cascade="all, delete-orphan")
    documents = relationship("Document", back_populates="job")


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, primary_key=True, autoincrement=True)
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=False)
    applied_date = Column(DateTime(timezone=True))
    status = Column(String(50), default="pending")
    # pending/applied/in_review/phone_screen/interview/offer/rejected/withdrawn
    ats_platform = Column(String(50))   # greenhouse/workday/lever/taleo/bamboohr/other
    ats_tracking_url = Column(String(1000))
    tailored_resume_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    tailored_cover_letter_id = Column(Integer, ForeignKey("documents.id"), nullable=True)
    automation_log = Column(JSON, default=list)   # [{step, status, message, timestamp}]
    
    # Retry tracking
    retry_count = Column(Integer, default=0)
    last_error = Column(Text, nullable=True)
    error_history = Column(JSON, default=list)  # [{timestamp, error, attempt, error_type}]
    last_retry_at = Column(DateTime(timezone=True), nullable=True)
    next_retry_at = Column(DateTime(timezone=True), nullable=True)
    
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    job = relationship("Job", back_populates="applications")
    tailored_resume = relationship("Document", foreign_keys=[tailored_resume_id])
    tailored_cover_letter = relationship("Document", foreign_keys=[tailored_cover_letter_id])


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    type = Column(String(50), nullable=False)     # resume / cover_letter
    variant = Column(String(50), nullable=False)  # base / tailored
    job_id = Column(Integer, ForeignKey("jobs.id"), nullable=True)
    filename = Column(String(500), nullable=False)
    file_path = Column(String(1000), nullable=False)
    content_text = Column(Text)   # extracted text for AI use
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
