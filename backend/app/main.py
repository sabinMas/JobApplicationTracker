from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from .database import init_db
from .routers import jobs, applications, profile, documents, ai, automation, auto_apply, scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield


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
