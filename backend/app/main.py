from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio
import os

from .logging_config import setup_logging, get_logger
from .database import init_db
from .routers import jobs, applications, profile, documents, ai, automation, auto_apply, scheduler, metrics, dashboard, auto_apply_scored
from .services.job_sources import JobSourceManager, RSSJobSource
from .services.job_sync_scheduler import JobSyncScheduler, set_scheduler

# Initialize structured logging
setup_logging(os.getenv("ENVIRONMENT", "development"))
logger = get_logger(__name__)


_db_initialized = False
_job_sync_scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB and scheduler in background without blocking startup
    global _db_initialized, _job_sync_scheduler
    asyncio.create_task(_init_db_background())
    asyncio.create_task(_init_scheduler_background())
    yield


async def _init_db_background():
    global _db_initialized
    try:
        logger.info("Initializing database...")
        await init_db()
        _db_initialized = True
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"DB init error (will retry on first request): {e}", extra_fields={"error": str(e)})


async def _init_scheduler_background():
    global _job_sync_scheduler
    try:
        logger.info("Initializing job sync scheduler...")
        
        # Create job manager
        job_manager = JobSourceManager()
        
        # Register default RSS sources (can be extended later)
        # For now, just create manager, sources are added via API
        
        # Create scheduler
        _job_sync_scheduler = JobSyncScheduler(job_manager)
        set_scheduler(_job_sync_scheduler)
        
        logger.info("Job sync scheduler initialized successfully")
    except Exception as e:
        logger.error(f"Scheduler init error: {e}", extra_fields={"error": str(e)})


app = FastAPI(
    title="Job Application Tracker API",
    version="1.0.0",
    lifespan=lifespan,
)

import os
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")
# Strip whitespace from origins
allowed_origins = [origin.strip() for origin in allowed_origins]

# For development, allow any vercel deployment
if any("vercel.app" in origin for origin in allowed_origins):
    # If any vercel.app domain is allowed, allow all vercel deployments
    allowed_origins.extend(["*"])

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
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

# WebSocket route is registered inside automation router as /api/automation/ws/{session_id}


@app.get("/health")
async def health():
    logger.debug("Health check called")
    return {"status": "ok", "service": "JobApplicationTracker", "db_initialized": _db_initialized}
