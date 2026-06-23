from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import os

from .logging_config import setup_logging, get_logger
from .database import init_db
from .routers import (
    jobs,
    applications,
    profile,
    documents,
    ai,
    automation,
    auto_apply,
    scheduler,
    metrics,
    dashboard,
    auto_apply_scored,
    scraper,
    job_enrichment,
)
from .services.job_sources import JobSourceManager
from .services.job_sync_scheduler import (
    JobSyncScheduler,
    seed_sources_from_preferences,
    set_scheduler,
)
from .services.actor_framework import actor_registry
from .scrapers.test_actor import TestActor
from .scrapers.linkedin_actor import LinkedInActor
from .scrapers.indeed_actor import IndeedActor
from .scrapers.github_actor import GitHubActor
from .scrapers.agentic_actor import AgenticScraperActor

# Initialize structured logging
setup_logging(os.getenv("ENVIRONMENT", "development"))
logger = get_logger(__name__)


_db_initialized = False
_job_sync_scheduler = None


def _init_actors():
    """Register all available actors."""
    try:
        actor_registry.register(TestActor())
        actor_registry.register(LinkedInActor())
        actor_registry.register(IndeedActor())
        actor_registry.register(GitHubActor())
        actor_registry.register(AgenticScraperActor())
        logger.info("Actors initialized successfully")
    except Exception as e:
        logger.error(
            f"Actor init error: {e}", extra={"extra_fields": {"error": str(e)}}
        )


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize actors and DB first
    global _db_initialized, _job_sync_scheduler
    _init_actors()

    # Initialize DB before scheduler (scheduler needs DB for preferences)
    try:
        logger.info("Initializing database...")
        await init_db()
        _db_initialized = True
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"DB init error: {e}", extra={"extra_fields": {"error": str(e)}})

    # Initialize scheduler after DB is ready
    try:
        logger.info("Initializing job sync scheduler...")
        job_manager = JobSourceManager()
        try:
            await seed_sources_from_preferences(job_manager)
        except Exception as e:
            logger.warning(
                f"Could not seed job sources from preferences: {e}",
                extra_fields={"error": str(e)},
            )
        # Always create scheduler, even if seeding failed (sources can be empty initially)
        _job_sync_scheduler = JobSyncScheduler(job_manager)
        set_scheduler(_job_sync_scheduler)
        logger.info(
            "Job sync scheduler initialized",
            extra_fields={"sources": len(job_manager.sources)},
        )
    except Exception as e:
        logger.error(
            f"Critical scheduler init error: {e}", extra_fields={"error": str(e)}
        )
        raise  # Fail startup if scheduler creation itself fails

    yield


app = FastAPI(
    title="Job Application Tracker API",
    version="1.0.0",
    lifespan=lifespan,
    redirect_slashes=False,  # Prevent 307 redirects that strip CORS headers
)

# CORS configuration — explicit origins + regex for Vercel preview deploys
_allowed_origins = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=_allowed_origins,
    allow_origin_regex=r"https://.*\.vercel\.app",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include all routers
app.include_router(jobs.router)
app.include_router(applications.router)
app.include_router(profile.router)
app.include_router(documents.router)
app.include_router(ai.router)
app.include_router(automation.router)
app.include_router(auto_apply.router)
app.include_router(scheduler.router)
app.include_router(metrics.router)
app.include_router(dashboard.router)  # Phase 4: Dashboard API
app.include_router(auto_apply_scored.router)  # Phase 4: Scoring integration
app.include_router(scraper.router)  # Actor-based scraper framework
app.include_router(job_enrichment.router)  # Phase 5: Job enrichment pipeline

# WebSocket route is registered inside automation router as /api/automation/ws/{session_id}


@app.get("/health")
async def health():
    logger.debug("Health check called")
    return {
        "status": "ok",
        "service": "JobApplicationTracker",
        "db_initialized": _db_initialized,
    }
