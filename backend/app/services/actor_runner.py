"""Run scraper actors and manage execution lifecycle."""

import asyncio
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import aioboto3
import httpx

from app.models import ScraperRun, Dataset, Actor as ActorModel
from app.services.actor_framework import actor_registry
from app.services.s3_service import s3_service

logger = logging.getLogger(__name__)

_boto_session = aioboto3.Session()


async def enqueue_actor_run(
    db: AsyncSession,
    actor_name: str,
    input_config: Dict[str, Any],
    run_name: Optional[str] = None,
    webhook_url: Optional[str] = None,
) -> int:
    """
    Create and enqueue a scraper run.

    Returns the run_id.
    """
    # Validate actor exists
    if not actor_registry.has(actor_name):
        raise ValueError(f"Actor '{actor_name}' not found")

    # Create run record
    run = ScraperRun(
        actor_name=actor_name,
        run_name=run_name or f"{actor_name}-{datetime.utcnow().isoformat()}",
        input_config=input_config,
        status="pending",
        webhook_url=webhook_url,
    )
    db.add(run)
    await db.flush()
    run_id = run.id
    await db.commit()

    logger.info(f"Created run {run_id}: {actor_name}")

    # Enqueue to SQS for worker to pick up
    queue_url = get_scraper_queue_url()
    message = {
        "run_id": run_id,
        "actor_name": actor_name,
        "input_config": input_config,
    }
    import os
    async with _boto_session.client(
        "sqs", region_name=os.getenv("AWS_REGION", "us-east-1")
    ) as sqs:
        await sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(message))

    logger.info(f"Enqueued run {run_id} to SQS")
    return run_id


async def execute_actor_run(
    db: AsyncSession,
    run_id: int,
) -> bool:
    """
    Execute a scraper run. Called by ECS worker.

    Returns True if successful, False otherwise.
    """
    # Fetch run
    stmt = select(ScraperRun).where(ScraperRun.id == run_id)
    result = await db.execute(stmt)
    run = result.scalar_one_or_none()

    if not run:
        logger.error(f"Run {run_id} not found")
        return False

    try:
        logger.info(f"Starting run {run_id}: {run.actor_name}")
        run.status = "running"
        run.started_at = datetime.utcnow()
        await db.commit()

        # Get actor
        actor = actor_registry.get(run.actor_name)
        if not actor:
            raise ValueError(f"Actor '{run.actor_name}' not registered")

        # Validate input
        if not await actor.validate_input(run.input_config):
            raise ValueError(f"Invalid input for {run.actor_name}")

        # Run actor
        items = await actor.run(run.input_config)

        # Store results to S3
        s3_key = f"runs/{run.actor_name}/{run_id}/results.jsonl"
        await s3_service.write_jsonl(s3_key, items)

        # Create dataset record
        dataset = Dataset(
            s3_bucket=s3_service.bucket_name,
            s3_key=s3_key,
            item_count=len(items),
            item_schema=items[0] if items else {},
        )
        db.add(dataset)
        await db.flush()  # assign dataset.id before linking the run

        # Mark run complete
        run.status = "success"
        run.finished_at = datetime.utcnow()
        run.items_scraped = len(items)
        run.dataset_id = dataset.id
        await db.commit()

        logger.info(f"Completed run {run_id}: {len(items)} items")

        # Call hook
        await actor.on_success(run_id, items)

        # Webhook
        if run.webhook_url:
            await _call_webhook(run.webhook_url, {"run_id": run_id, "status": "success", "items_count": len(items)})

        return True

    except Exception as e:
        logger.error(f"Error in run {run_id}: {e}", exc_info=True)
        run.status = "failed"
        run.error_message = str(e)
        run.finished_at = datetime.utcnow()
        await db.commit()

        # Call error hook
        actor = actor_registry.get(run.actor_name)
        if actor:
            await actor.on_error(run_id, e)

        # Webhook
        if run.webhook_url:
            await _call_webhook(run.webhook_url, {"run_id": run_id, "status": "failed", "error": str(e)})

        return False


async def _call_webhook(url: str, payload: Dict[str, Any]) -> None:
    """POST to webhook with run result."""
    try:
        async with httpx.AsyncClient() as client:
            await client.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.warning(f"Failed to call webhook {url}: {e}")


def get_scraper_queue_url() -> str:
    """Get the SQS queue URL for scraper tasks."""
    import os
    url = os.getenv("SQS_QUEUE_URL", os.getenv("SCRAPER_QUEUE_URL", ""))
    if not url:
        raise RuntimeError("SQS_QUEUE_URL not configured")
    return url
