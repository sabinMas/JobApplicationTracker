"""
Job source manager.

Orchestrates fetching jobs from multiple sources, deduplication, and storage.
"""

from typing import List, Dict, Set
import asyncio
from sqlalchemy import select

from .base import JobSource, JobListing
from ...models import Job
from ...database import AsyncSessionLocal
from ...logging_config import get_logger

# Defer logger
_logger = None


def get_logger_instance():
    global _logger
    if _logger is None:
        get_logger_instance_actual = get_logger
        _logger = get_logger_instance_actual(__name__)
    return _logger


class JobSourceManager:
    """Manages multiple job sources and deduplication."""

    def __init__(self):
        """Initialize manager with no sources."""
        self.sources: Dict[str, JobSource] = {}

    def add_source(self, source: JobSource) -> None:
        """
        Register a job source.

        Args:
            source: JobSource instance
        """
        self.sources[source.name] = source
        get_logger_instance().info(f"Registered job source: {source.name}")

    async def fetch_all(self) -> Dict[str, List[JobListing]]:
        """
        Fetch jobs from all registered sources in parallel.

        Returns:
            Dict mapping source name to list of JobListings
        """
        logger = get_logger_instance()

        logger.info(
            "Fetching jobs from all sources",
            extra_fields={
                "source_count": len(self.sources),
            },
        )

        # Fetch from all sources in parallel
        results = {}
        tasks = []
        source_names = []

        for source_name, source in self.sources.items():
            tasks.append(source.fetch_jobs())
            source_names.append(source_name)

        # Run all fetches concurrently
        if tasks:
            fetches = await asyncio.gather(*tasks, return_exceptions=True)

            for source_name, fetch_result in zip(source_names, fetches):
                if isinstance(fetch_result, Exception):
                    logger.warning(
                        f"Failed to fetch from {source_name}: {fetch_result}",
                        extra_fields={"source": source_name},
                    )
                    results[source_name] = []
                else:
                    results[source_name] = fetch_result
                    logger.info(
                        f"Fetched {len(fetch_result)} jobs from {source_name}",
                        extra_fields={
                            "source": source_name,
                            "count": len(fetch_result),
                        },
                    )

        return results

    async def sync_to_database(
        self, jobs_by_source: Dict[str, List[JobListing]]
    ) -> Dict[str, int]:
        """
        Sync jobs to database with deduplication.

        Args:
            jobs_by_source: Dict from fetch_all()

        Returns:
            Dict with counts: {"added": X, "duplicates": Y, "errors": Z}
        """
        logger = get_logger_instance()

        stats = {
            "added": 0,
            "duplicates": 0,
            "errors": 0,
        }

        # Collect all jobs with their source
        all_jobs = []
        for source_name, jobs in jobs_by_source.items():
            for job in jobs:
                all_jobs.append((source_name, job))

        logger.info(
            "Syncing jobs to database",
            extra_fields={
                "total_jobs": len(all_jobs),
            },
        )

        # Get existing job URLs to detect duplicates
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Job.apply_url))
            existing_urls = {row[0] for row in result.fetchall()}

        # Deduplicate and insert
        seen_urls: Set[str] = set()

        async with AsyncSessionLocal() as session:
            for source_name, job_listing in all_jobs:
                try:
                    # Check for duplicates within this sync
                    if job_listing.apply_url in seen_urls:
                        stats["duplicates"] += 1
                        continue

                    # Check for existing jobs in database
                    if job_listing.apply_url in existing_urls:
                        stats["duplicates"] += 1
                        logger.debug(
                            f"Job already exists: {job_listing.title}",
                            extra_fields={
                                "source": source_name,
                                "url": job_listing.apply_url,
                            },
                        )
                        continue

                    seen_urls.add(job_listing.apply_url)

                    # Create new job record
                    job_dict = job_listing.to_dict()
                    job_dict["source"] = source_name

                    job = Job(**job_dict)
                    session.add(job)

                    stats["added"] += 1

                    logger.debug(
                        f"Added job: {job_listing.title}",
                        extra_fields={
                            "source": source_name,
                            "company": job_listing.company,
                        },
                    )

                except Exception as e:
                    stats["errors"] += 1
                    logger.error(
                        f"Error adding job: {e}",
                        extra_fields={
                            "source": source_name,
                            "job_title": job_listing.title,
                            "error": str(e),
                        },
                    )
                    continue

            # Commit all changes
            try:
                await session.commit()
                logger.info(
                    "Synced jobs to database",
                    extra_fields={
                        "added": stats["added"],
                        "duplicates": stats["duplicates"],
                        "errors": stats["errors"],
                    },
                )
            except Exception as e:
                logger.error(
                    f"Failed to commit jobs: {e}",
                    extra_fields={
                        "error": str(e),
                    },
                )
                stats["errors"] += stats["added"]
                stats["added"] = 0

        return stats

    async def sync(self) -> Dict[str, int]:
        """
        Perform full sync: fetch from all sources and update database.

        Returns:
            Sync statistics
        """
        logger = get_logger_instance()

        try:
            # Fetch all jobs
            jobs_by_source = await self.fetch_all()

            # Sync to database
            stats = await self.sync_to_database(jobs_by_source)

            logger.info("Sync completed successfully", extra_fields=stats)

            return stats

        except Exception as e:
            logger.error(
                f"Sync failed: {e}",
                extra_fields={
                    "error": str(e),
                },
            )
            raise
