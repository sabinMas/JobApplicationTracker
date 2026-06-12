"""
RSS feed job source.

Fetches jobs from RSS feeds (e.g., HackerNews jobs, WeWorkRemotely, etc.)
"""

import re
import hashlib
from typing import List, Optional
from datetime import datetime
import feedparser
import httpx

from .base import JobSource, JobListing

# Defer logger creation
_logger = None


def get_logger_instance():
    global _logger
    if _logger is None:
        from ...logging_config import get_logger as create_logger
        _logger = create_logger(__name__)
    return _logger


class RSSJobSource(JobSource):
    """RSS feed job source."""
    
    def __init__(
        self,
        feed_url: str,
        name: Optional[str] = None,
        job_title_selector: Optional[str] = None,
        job_location_selector: Optional[str] = None,
    ):
        """
        Args:
            feed_url: URL to the RSS feed
            name: Human-readable name (defaults to domain of feed_url)
            job_title_selector: CSS selector for job title in feed item
            job_location_selector: CSS selector for job location in feed item
        """
        self.feed_url = feed_url
        self.name = name or self._extract_domain(feed_url)
        self.job_title_selector = job_title_selector
        self.job_location_selector = job_location_selector
    
    async def fetch_jobs(self) -> List[JobListing]:
        """Fetch jobs from RSS feed."""
        logger = get_logger_instance()
        
        try:
            logger.info("Fetching RSS feed", extra_fields={
                "source": self.name,
                "feed_url": self.feed_url,
            })
            
            # Fetch feed with timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.feed_url)
                response.raise_for_status()
            
            # Parse RSS
            feed = feedparser.parse(response.content)
            
            if feed.bozo:
                logger.warning(f"RSS feed parse warning: {feed.bozo_exception}", extra_fields={
                    "source": self.name,
                })
            
            jobs = []
            
            # Extract jobs from feed entries
            for entry in feed.entries:
                try:
                    job = self._parse_entry(entry)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing feed entry: {e}", extra_fields={
                        "source": self.name,
                        "entry_title": entry.get("title", "unknown"),
                    })
                    continue
            
            logger.info("RSS feed fetched successfully", extra_fields={
                "source": self.name,
                "jobs_found": len(jobs),
            })
            
            return jobs
        
        except Exception as e:
            logger.error(f"Failed to fetch RSS feed: {e}", extra_fields={
                "source": self.name,
                "feed_url": self.feed_url,
                "error": str(e),
            })
            raise
    
    async def get_external_id(self, job: JobListing) -> str:
        """
        Generate unique ID based on title, company, and URL.
        
        This allows detecting duplicates across multiple feeds.
        """
        # Normalize for comparison
        id_str = f"{job.title}_{job.company}_{job.source_url}".lower()
        return hashlib.md5(id_str.encode()).hexdigest()
    
    def _parse_entry(self, entry: dict) -> Optional[JobListing]:
        """
        Parse RSS feed entry into JobListing.
        
        Supports common RSS job formats:
        - HackerNews jobs: each entry is a job post
        - WeWorkRemotely: each entry is a job with HTML description
        - Generic RSS: title + description
        """
        
        # Extract basic fields
        title = entry.get("title", "").strip()
        if not title:
            return None
        
        # Try to extract apply URL from links
        apply_url = None
        if "links" in entry:
            for link in entry.get("links", []):
                if link.get("rel") == "alternate":
                    apply_url = link.get("href")
                    break
        
        if not apply_url:
            apply_url = entry.get("link", "")
        
        if not apply_url:
            return None
        
        # Extract description
        description = entry.get("summary", "") or entry.get("description", "")
        
        # Try to extract company from title or description
        company = self._extract_company(title, description)
        
        # Try to extract location
        location = self._extract_location(title, description)
        
        # Posted date
        posted_date = None
        if "published_parsed" in entry:
            published_struct = entry.get("published_parsed")
            if published_struct:
                try:
                    dt = datetime(*published_struct[:6])
                    posted_date = dt.isoformat()
                except Exception:
                    pass
        
        return JobListing(
            title=title,
            company=company or "Unknown",
            location=location or "Not specified",
            job_type="full-time",  # Default, can be overridden
            description=description,
            source=self.name,
            source_url=apply_url,
            apply_url=apply_url,
            posted_date=posted_date,
        )
    
    def _extract_company(self, title: str, description: str) -> Optional[str]:
        """Extract company name from title or description."""
        
        # Common patterns: "Company - Job Title" or "Job Title at Company"
        patterns = [
            r"^\s*(.+?)\s*[-–]\s*(.+?)$",  # "Company - Job Title"
            r"at\s+(.+?)(?:\s|$)",  # "at Company"
        ]
        
        for pattern in patterns:
            match = re.search(pattern, title, re.IGNORECASE)
            if match:
                company = match.group(1).strip()
                # Filter out common false positives
                if company and len(company) > 2 and company.lower() not in ["job", "position"]:
                    return company
        
        return None
    
    def _extract_location(self, title: str, description: str) -> Optional[str]:
        """Extract location from title or description."""
        
        # Common patterns
        patterns = [
            r"remote|work\s+from\s+home|wfh",
            r"\b([A-Z]{2})\b",  # US state code
            r"([\w\s]+,\s*[A-Z]{2})",  # "City, State"
        ]
        
        text = f"{title} {description}".lower()
        
        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                if "remote" in match.group(0).lower():
                    return "Remote"
                return match.group(0).strip()
        
        return None
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain name from URL."""
        match = re.search(r"https?://(?:www\.)?([^/]+)", url)
        if match:
            domain = match.group(1)
            # Remove common TLDs for cleaner names
            domain = re.sub(r"\.(com|org|net|io|co)$", "", domain)
            return domain.replace("-", " ").title()
        return url
