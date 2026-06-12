"""
Job source module for fetching jobs from multiple platforms.

Supported sources:
- RSS feeds (HackerNews jobs, WeWorkRemotely, etc.)
- GitHub Jobs (no auth required)
- LinkedIn (when credentials provided)
- Angel List (when credentials provided)

Usage:
    from app.services.job_sources import JobSourceManager, RSSJobSource, GitHubJobSource

    manager = JobSourceManager()
    manager.add_source(RSSJobSource("https://news.ycombinator.com/rss"))
    manager.add_source(GitHubJobSource())

    stats = await manager.sync()  # Fetch and save to database
"""

from .base import JobSource, JobListing
from .rss_source import RSSJobSource
from .github_source import GitHubJobSource
from .linkedin_source import LinkedInJobSource
from .angellist_source import AngelListJobSource
from .manager import JobSourceManager

__all__ = [
    "JobSource",
    "JobListing",
    "RSSJobSource",
    "GitHubJobSource",
    "LinkedInJobSource",
    "AngelListJobSource",
    "JobSourceManager",
]
