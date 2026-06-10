"""
ECS Fargate Worker: Polls SQS for job scraping and actor runs.

This worker:
1. Polls SQS for two message types:
   a) Job scraping tasks (legacy): Scrape job boards, extract with Cerebras, store as Job records
   b) Actor runs (Phase 5): Execute registered actors (scrapers) with custom configs
2. Handles lifecycle: processing, retries, error logging
3. Marks tasks complete in SQS
"""

import asyncio
import json
import logging
import os
from datetime import datetime
import boto3
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker

# Configure logging
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# AWS clients
sqs = boto3.client('sqs', region_name='us-east-1')
s3 = boto3.client('s3', region_name='us-east-1')

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///../data/app.db")
engine = create_async_engine(DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

# SQS queue URL
QUEUE_URL = os.getenv("SQS_QUEUE_URL")
S3_BUCKET = os.getenv("S3_BUCKET", "jobtracker-documents-245091941294")

# Import app models and services
from app.models import Job, Application
from app.services.scraper_service import scrape_job_url
from app.services.playwright_service import PlaywrightService
from app.services.ai_service import extract_job
from app.services.actor_framework import actor_registry
from app.services.actor_runner import execute_actor_run
from app.scrapers.test_actor import TestActor
from app.scrapers.linkedin_actor import LinkedInActor
from app.scrapers.indeed_actor import IndeedActor
from app.scrapers.github_actor import GitHubActor
from app.scrapers.agentic_actor import AgenticScraperActor


def _register_actors() -> None:
    """Actors must be registered in this process — the API's registry doesn't
    carry over to the worker."""
    for actor in (TestActor(), LinkedInActor(), IndeedActor(), GitHubActor(), AgenticScraperActor()):
        actor_registry.register(actor)


async def process_scraping_task(task: dict, db: AsyncSession) -> bool:
    """
    Process a single scraping task from SQS.

    Task format:
    {
        "task_id": "uuid",
        "job_url": "https://...",
        "source": "linkedin|indeed|greenhouse|...",
        "company": "Company Name",
        "title": "Job Title"
    }
    """
    task_id = task.get("task_id")
    job_url = task.get("job_url")
    source = task.get("source")

    try:
        logger.info(f"Starting scrape task {task_id}: {job_url}")

        # Check if job already exists
        from sqlalchemy import select
        stmt = select(Job).where(Job.source_url == job_url)
        result = await db.execute(stmt)
        existing = result.scalar_one_or_none()

        if existing:
            logger.info(f"Job already exists: {job_url}")
            return True

        # Scrape job page with Playwright
        pw_service = PlaywrightService()
        page_html = await pw_service.fetch_page(job_url, timeout=30000)

        if not page_html:
            logger.warning(f"Failed to fetch page: {job_url}")
            return False

        # Extract job details with Cerebras AI
        job_data = await extract_job(page_html)

        if not job_data or not job_data.get("title"):
            logger.warning(f"Failed to extract job data: {job_url}")
            return False

        # Store job in database
        job = Job(
            title=job_data.get("title"),
            company=job_data.get("company"),
            location=job_data.get("location"),
            job_type=job_data.get("job_type"),
            source=source,
            source_url=job_url,
            apply_url=job_data.get("apply_url"),
            description=job_data.get("description"),
            requirements=job_data.get("requirements"),
            salary_range=job_data.get("salary_range"),
            status="discovered"
        )
        db.add(job)
        await db.commit()

        logger.info(f"Successfully scraped job {task_id}: {job.title} at {job.company}")
        return True

    except Exception as e:
        logger.error(f"Error processing task {task_id}: {e}", exc_info=True)
        return False
    finally:
        await pw_service.close() if 'pw_service' in locals() else None


async def process_auto_apply_task(message: dict, db: AsyncSession) -> bool:
    """Execute a full auto-apply for an application (Playwright lives here)."""
    from app.services.auto_apply_service import (
        AutoApplyPreconditionError,
        run_full_auto_apply,
    )

    application_id = message.get("application_id")
    try:
        result = await run_full_auto_apply(db, application_id)
        logger.info(f"Auto-apply for application {application_id}: {result.get('status')}")
        # error status still counts as processed — retries are handled by the
        # application-level retry tracking, not by SQS redelivery
        return True
    except AutoApplyPreconditionError as e:
        logger.error(f"Auto-apply precondition failed for {application_id}: {e}")
        return True  # retrying won't fix a missing resume/profile — drop it
    except Exception as e:
        logger.error(f"Auto-apply crashed for {application_id}: {e}", exc_info=True)
        return False


async def dispatch_message(message: dict, db: AsyncSession) -> bool:
    """
    Dispatch a message to the appropriate handler based on type.

    Returns True if processed successfully, False otherwise.
    """
    # Determine message type
    if message.get("action") == "auto_apply":
        logger.info("Dispatching to auto-apply handler")
        return await process_auto_apply_task(message, db)
    elif "run_id" in message:
        # Actor run message (Phase 5: Mini-Apify)
        run_id = message.get("run_id")
        logger.info(f"Dispatching to actor runner: run_id={run_id}")
        return await execute_actor_run(db, run_id)
    elif "job_url" in message:
        # Job scraping message (legacy)
        logger.info(f"Dispatching to job scraper")
        return await process_scraping_task(message, db)
    else:
        logger.warning(f"Unknown message type: {message}")
        return False


async def poll_sqs_queue():
    """
    Poll SQS queue for job scraping and actor run tasks.

    Runs continuously, processing one task at a time.
    Supports:
    - Job scraping: {job_url, source, company, title}
    - Actor runs: {run_id, actor_name, input_config}
    """
    if not QUEUE_URL:
        logger.error("SQS_QUEUE_URL not set")
        return

    logger.info(f"Starting worker, polling {QUEUE_URL}")
    logger.info(f"Available actors: {actor_registry.list()}")
    consecutive_empty_polls = 0
    max_empty_polls = 10  # Exit after 10 empty polls (5 minutes of inactivity)

    async with AsyncSessionLocal() as db:
        while True:
            try:
                # Poll for messages
                response = sqs.receive_message(
                    QueueUrl=QUEUE_URL,
                    MaxNumberOfMessages=1,
                    WaitTimeSeconds=30,  # Long polling
                    VisibilityTimeout=300  # 5 minutes to process
                )

                messages = response.get('Messages', [])

                if not messages:
                    consecutive_empty_polls += 1
                    logger.debug(f"No messages (empty polls: {consecutive_empty_polls}/{max_empty_polls})")

                    # Exit if queue is empty for too long (worker auto-scaling down)
                    if consecutive_empty_polls >= max_empty_polls:
                        logger.info("No messages for 5 minutes, exiting worker")
                        break
                    continue

                consecutive_empty_polls = 0

                for message in messages:
                    try:
                        # Parse task
                        task = json.loads(message['Body'])
                        task_id = message['MessageId']

                        logger.info(f"Received message {task_id}")

                        # Dispatch to appropriate handler
                        success = await dispatch_message(task, db)

                        if success:
                            # Delete from queue
                            sqs.delete_message(
                                QueueUrl=QUEUE_URL,
                                ReceiptHandle=message['ReceiptHandle']
                            )
                            logger.info(f"Message {task_id} completed successfully")
                        else:
                            # Leave in queue for retry
                            logger.warning(f"Message {task_id} failed, will retry")

                    except json.JSONDecodeError as e:
                        logger.error(f"Invalid message JSON: {e}")
                        # Delete invalid message to avoid infinite loops
                        sqs.delete_message(
                            QueueUrl=QUEUE_URL,
                            ReceiptHandle=message['ReceiptHandle']
                        )

                    except Exception as e:
                        logger.error(f"Error processing message: {e}", exc_info=True)

            except Exception as e:
                logger.error(f"Error polling SQS: {e}", exc_info=True)
                await asyncio.sleep(5)  # Wait before retrying


def main():
    """Entry point for ECS worker."""
    logger.info("Starting ECS Fargate worker")
    _register_actors()
    asyncio.run(poll_sqs_queue())


if __name__ == "__main__":
    main()
