"""Scraper actor management API."""

from typing import Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import get_db
from app.models import ScraperRun, Dataset
from app.services.actor_framework import actor_registry
from app.services.actor_runner import enqueue_actor_run
from pydantic import BaseModel

router = APIRouter(prefix="/scraper", tags=["scraper"])


class RunInput(BaseModel):
    actor_name: str
    run_name: Optional[str] = None
    input_config: Dict[str, Any]
    webhook_url: Optional[str] = None


class RunResponse(BaseModel):
    id: int
    actor_name: str
    run_name: str
    status: str
    items_scraped: int
    created_at: str

    class Config:
        from_attributes = True


class RunDetailResponse(RunResponse):
    input_config: Dict[str, Any]
    error_message: Optional[str] = None
    started_at: Optional[str] = None
    finished_at: Optional[str] = None
    dataset_id: Optional[int] = None


class ActorListResponse(BaseModel):
    name: str
    display_name: Optional[str] = None
    description: Optional[str] = None
    input_schema: Optional[Dict[str, Any]] = None


@router.post("/run")
async def create_run(
    payload: RunInput,
    db: AsyncSession = Depends(get_db),
) -> RunResponse:
    """Start a scraper run."""
    try:
        run_id = await enqueue_actor_run(
            db,
            actor_name=payload.actor_name,
            input_config=payload.input_config,
            run_name=payload.run_name,
            webhook_url=payload.webhook_url,
        )
        stmt = select(ScraperRun).where(ScraperRun.id == run_id)
        result = await db.execute(stmt)
        run = result.scalar_one()
        return RunResponse.model_validate(run)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/run/{run_id}")
async def get_run(
    run_id: int,
    db: AsyncSession = Depends(get_db),
) -> RunDetailResponse:
    """Get run details and status."""
    stmt = select(ScraperRun).where(ScraperRun.id == run_id)
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    return RunDetailResponse.model_validate(run)


@router.get("/runs")
async def list_runs(
    actor_name: Optional[str] = None,
    status: Optional[str] = None,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
) -> list[RunResponse]:
    """List scraper runs with optional filtering."""
    stmt = select(ScraperRun)

    if actor_name:
        stmt = stmt.where(ScraperRun.actor_name == actor_name)
    if status:
        stmt = stmt.where(ScraperRun.status == status)

    stmt = stmt.order_by(ScraperRun.created_at.desc()).limit(limit)
    result = await db.execute(stmt)
    runs = result.scalars().all()

    return [RunResponse.model_validate(r) for r in runs]


@router.get("/actors")
async def list_actors() -> list[ActorListResponse]:
    """List all registered actors."""
    actors = []
    for name in actor_registry.list():
        actors.append(
            ActorListResponse(
                name=name,
                display_name=name.title(),
                description=f"Scrapes {name} for jobs",
                input_schema={},
            )
        )
    return actors


@router.get("/dataset/{dataset_id}")
async def get_dataset(
    dataset_id: int,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """Get dataset metadata and S3 location."""
    stmt = select(Dataset).where(Dataset.id == dataset_id)
    result = await db.execute(stmt)
    dataset = result.scalar_one_or_none()

    if not dataset:
        raise HTTPException(status_code=404, detail="Dataset not found")

    return {
        "id": dataset.id,
        "s3_bucket": dataset.s3_bucket,
        "s3_key": dataset.s3_key,
        "item_count": dataset.item_count,
        "s3_url": f"s3://{dataset.s3_bucket}/{dataset.s3_key}",
    }
