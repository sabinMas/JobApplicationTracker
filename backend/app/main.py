from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import asyncio

from .database import init_db
from .routers import jobs, applications, profile, documents, ai, automation, auto_apply, scheduler


_db_initialized = False

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize DB in background without blocking startup
    global _db_initialized
    asyncio.create_task(_init_db_background())
    yield


async def _init_db_background():
    global _db_initialized
    try:
        await init_db()
        _db_initialized = True
    except Exception as e:
        print(f"DB init error (will retry on first request): {e}")


app = FastAPI(
    title="Job Application Tracker API",
    version="1.0.0",
    lifespan=lifespan,
)

import os
allowed_origins = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173").split(",")

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

# WebSocket route is registered inside automation router as /api/automation/ws/{session_id}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "JobApplicationTracker"}
