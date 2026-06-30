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

# Broad tech/dev terms always considered relevant regardless of preferences.
# Keeps the filter from being too aggressive when preferences aren't set.
_BASE_TECH_TERMS: frozenset[str] = frozenset(
    [
        "developer",
        "engineer",
        "software",
        "backend",
        "frontend",
        "full-stack",
        "fullstack",
        "full stack",
        "web dev",
        "javascript",
        "typescript",
        "python",
        "node.js",
        "nodejs",
        "react",
        "next.js",
        "vue",
        "angular",
        "llm",
        "ai trainer",
        "machine learning",
        "ml engineer",
        "data labeling",
        "geospatial",
        "gis",
        "rest api",
        "devops",
        "cloud engineer",
        "site reliability",
    ]
)

# Defer logger
_logger = None


def get_logger_instance():
    global _logger
    if _logger is None:
        get_logger_instance_actual = get_logger
        _logger = get_logger_instance_actual(__name__)
    return _logger


def _build_relevance_terms(
    must_have: list[str],
    target_roles: list[str],
) -> frozenset[str]:
    """Combine preference keywords + base tech terms into a lowercase match set."""
    terms: set[str] = set(_BASE_TECH_TERMS)
    for kw in must_have or []:
        terms.add(kw.lower())
    for role in target_roles or []:
        # "Full-Stack Web Developer" → also index each significant word individually
        terms.add(role.lower())
        for word in role.lower().split():
            if len(word) > 3:
                terms.add(word)
    return frozenset(terms)


def _is_relevant_job(
    job_listing: "JobListing",
    include_terms: frozenset[str],
    exclude_terms: frozenset[str],
) -> bool:
    """Return True if the job title matches relevance criteria.

    Checks the title only — descriptions are often HTML-heavy and unreliable for
    quick filtering. Excluded if any avoid_keyword hits; included if any
    include_term hits.
    """
    title_lower = job_listing.title.lower()
    if any(term in title_lower for term in exclude_terms):
        return False
    return any(term in title_lower for term in include_terms)


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
        Sync jobs to database with deduplication and discovery limits.

        Args:
            jobs_by_source: Dict from fetch_all()

        Returns:
            Dict with counts: {"added": X, "duplicates": Y, "errors": Z, "limited": Z}
        """
        logger = get_logger_instance()

        stats = {
            "added": 0,
            "duplicates": 0,
            "errors": 0,
            "limited": 0,
            "irrelevant": 0,  # Count of jobs skipped for not matching profile
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

        # Load preferences once for discovery limit + relevance filter
        max_discovery_limit = 50
        include_terms: frozenset[str] = _BASE_TECH_TERMS
        exclude_terms: frozenset[str] = frozenset()
        try:
            from ...models import SearchPreferences

            async with AsyncSessionLocal() as session:
                prefs = (
                    await session.execute(select(SearchPreferences))
                ).scalar_one_or_none()
                if prefs:
                    if prefs.max_jobs_per_discovery_run:
                        max_discovery_limit = prefs.max_jobs_per_discovery_run
                    include_terms = _build_relevance_terms(
                        prefs.must_have_keywords or [],
                        prefs.target_roles or [],
                    )
                    exclude_terms = frozenset(
                        kw.lower() for kw in (prefs.avoid_keywords or [])
                    )
        except Exception as e:
            logger.warning(f"Could not load preferences: {e}")

        # Get existing job URLs to detect duplicates
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(Job.apply_url))
            existing_urls = {row[0] for row in result.fetchall()}

            # Also load DiscoveredJobURL for deduplication
            from ...models import DiscoveredJobURL

            result = await session.execute(select(DiscoveredJobURL.job_url))
            discovered_urls = {row[0] for row in result.fetchall()}

        # Deduplicate and insert — each job in its own transaction to prevent
        # a single failure from aborting the entire batch (PostgreSQL behaviour).
        seen_urls: Set[str] = set()

        for source_name, job_listing in all_jobs:
            # Respect discovery limit
            if stats["added"] >= max_discovery_limit:
                stats["limited"] += 1
                continue

            # Relevance pre-filter: skip jobs that don't match the user's profile
            if not _is_relevant_job(job_listing, include_terms, exclude_terms):
                stats["irrelevant"] += 1
                logger.debug(
                    f"Skipping irrelevant job: {job_listing.title}",
                    extra_fields={"source": source_name, "title": job_listing.title},
                )
                continue

            # Check for duplicates within this sync
            if job_listing.apply_url in seen_urls:
                stats["duplicates"] += 1
                continue

            # Check for existing jobs in database or discovered URLs
            if (
                job_listing.apply_url in existing_urls
                or job_listing.apply_url in discovered_urls
            ):
                stats["duplicates"] += 1
                logger.debug(
                    f"Job already exists: {job_listing.title}",
                    extra_fields={"source": source_name, "url": job_listing.apply_url},
                )
                continue

            seen_urls.add(job_listing.apply_url)

            try:
                async with AsyncSessionLocal() as session:
                    job_dict = job_listing.to_dict()
                    job_dict["source"] = source_name

                    job = Job(**job_dict)
                    session.add(job)
                    await session.flush()

                    from ...models import DiscoveredJobURL

                    session.add(
                        DiscoveredJobURL(
                            job_url=job_listing.apply_url,
                            source=source_name,
                            job_id=job.id,
                        )
                    )
                    await session.commit()

                stats["added"] += 1
                # Update in-memory sets so later iterations see the new URL
                existing_urls.add(job_listing.apply_url)
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
                    f"Error adding job '{job_listing.title}': {e}",
                    extra_fields={
                        "source": source_name,
                        "job_title": job_listing.title,
                        "error": str(e),
                    },
                )

        logger.info(
            "Synced jobs to database",
            extra_fields={
                "added": stats["added"],
                "duplicates": stats["duplicates"],
                "errors": stats["errors"],
                "limited": stats["limited"],
                "irrelevant": stats["irrelevant"],
            },
        )

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
