"""
Abstract base class for job sources.

Job sources fetch job listings from various platforms (LinkedIn, GitHub, RSS, etc.)
and normalize them to a common format for storage and processing.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime, timezone


class JobListing:
    """Normalized job listing from any source."""

    def __init__(
        self,
        title: str,
        company: str,
        location: str,
        job_type: str,
        description: str,
        source: str,
        source_url: str,
        apply_url: str,
        requirements: Optional[str] = None,
        salary_range: Optional[str] = None,
        posted_date: Optional[str] = None,
        external_id: Optional[str] = None,
    ):
        """
        Args:
            title: Job title
            company: Company name
            location: Job location (can be "Remote")
            job_type: "full-time", "part-time", "contract", "temporary"
            description: Full job description text
            source: Source platform ("linkedin", "github", "angel_list", "rss", etc.)
            source_url: URL where job was found
            apply_url: Direct URL to apply/application form
            requirements: Required qualifications (optional)
            salary_range: Salary range if listed (optional)
            posted_date: When job was posted (ISO format)
            external_id: External unique ID from source (for deduplication)
        """
        self.title = title
        self.company = company
        self.location = location
        self.job_type = job_type
        self.description = description
        self.source = source
        self.source_url = source_url
        self.apply_url = apply_url
        self.requirements = requirements
        self.salary_range = salary_range
        self.posted_date = posted_date
        self.external_id = external_id
        self.discovered_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage."""
        return {
            "title": self.title,
            "company": self.company,
            "location": self.location,
            "job_type": self.job_type,
            "description": self.description,
            "source": self.source,
            "source_url": self.source_url,
            "apply_url": self.apply_url,
            "requirements": self.requirements,
            "salary_range": self.salary_range,
            "posted_date": self.posted_date,
        }


class JobSource(ABC):
    """Base class for job sources."""

    def __init__(self, name: str):
        """
        Args:
            name: Human-readable name of this source (e.g., "LinkedIn", "GitHub", "HackerNews RSS")
        """
        self.name = name

    @abstractmethod
    async def fetch_jobs(self) -> List[JobListing]:
        """
        Fetch job listings from this source.

        Returns:
            List of normalized JobListing objects

        Raises:
            Exception with descriptive message if fetch fails
        """
        pass

    @abstractmethod
    async def get_external_id(self, job: JobListing) -> str:
        """
        Generate a unique external ID for deduplication.

        This allows detecting when the same job appears from multiple sources.

        Args:
            job: JobListing object

        Returns:
            Unique identifier (e.g., "{source}_{job_id}" or hash of title+company)
        """
        pass
