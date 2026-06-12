"""
GitHub Jobs API source.

Fetches jobs from GitHub Jobs API (public, no authentication required).
Note: GitHub Jobs API was deprecated by GitHub in 2024, but remains accessible.
For production, consider alternative job sources.
"""

from typing import List, Optional
import httpx

from .base import JobSource, JobListing

# Defer logger
_logger = None


def get_logger_instance():
    global _logger
    if _logger is None:
        from ...logging_config import get_logger as create_logger
        _logger = create_logger(__name__)
    return _logger


class GitHubJobSource(JobSource):
    """GitHub Jobs API source."""
    
    def __init__(self, api_url: str = "https://jobs.github.com/positions.json", access_token: Optional[str] = None):
        """
        Args:
            api_url: GitHub Jobs API endpoint
            access_token: GitHub personal access token (for authenticated requests, increases rate limits)
        """
        self.api_url = api_url
        self.name = "GitHub Jobs"
        self.access_token = access_token
    
    async def fetch_jobs(self) -> List[JobListing]:
        """
        Fetch jobs from GitHub Jobs API.
        
        Returns:
            List of JobListing objects
        """
        logger = get_logger_instance()
        
        try:
            logger.info("Fetching GitHub jobs", extra_fields={
                "source": self.name,
                "api_url": self.api_url,
            })
            
            # Setup headers
            headers = {}
            if self.access_token:
                headers["Authorization"] = f"token {self.access_token}"
            
            # Fetch with timeout
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.api_url, headers=headers)
                response.raise_for_status()
            
            jobs_data = response.json()
            jobs = []
            
            # Parse jobs
            for job_data in jobs_data:
                try:
                    job = self._parse_job(job_data)
                    if job:
                        jobs.append(job)
                except Exception as e:
                    logger.warning(f"Error parsing GitHub job: {e}", extra_fields={
                        "source": self.name,
                        "job_title": job_data.get("title", "unknown"),
                    })
                    continue
            
            logger.info("GitHub jobs fetched successfully", extra_fields={
                "source": self.name,
                "jobs_found": len(jobs),
            })
            
            return jobs
        
        except Exception as e:
            logger.error(f"Failed to fetch GitHub jobs: {e}", extra_fields={
                "source": self.name,
                "api_url": self.api_url,
                "error": str(e),
            })
            raise
    
    async def get_external_id(self, job: JobListing) -> str:
        """
        Generate unique ID based on job data.
        """
        import hashlib
        id_str = f"{job.title}_{job.company}_{job.source_url}".lower()
        return hashlib.md5(id_str.encode()).hexdigest()
    
    def _parse_job(self, job_data: dict) -> Optional[JobListing]:
        """
        Parse GitHub job API response into JobListing.
        
        GitHub Jobs API response format:
        {
            "id": "...",
            "created_at": "2024-01-01T12:00:00Z",
            "title": "Senior Python Engineer",
            "location": "Remote",
            "type": "Full Time",
            "description": "...",
            "how_to_apply": "...",
            "company": "TechCorp",
            "company_logo": "...",
            "company_url": "...",
            "url": "https://jobs.github.com/positions/..."
        }
        """
        
        title = job_data.get("title", "").strip()
        if not title:
            return None
        
        company = job_data.get("company", "Unknown").strip()
        location = job_data.get("location", "Not specified").strip()
        job_type = job_data.get("type", "full-time").strip()
        
        # GitHub provides an HTML description with "how to apply" embedded
        description = job_data.get("description", "").strip()
        
        # Extract apply URL - GitHub provides a job posting URL
        apply_url = job_data.get("url", "")
        source_url = apply_url
        
        if not apply_url:
            return None
        
        # Parse posted date
        posted_date = None
        if "created_at" in job_data:
            try:
                posted_date = job_data["created_at"]  # Already in ISO format
            except Exception:
                pass
        
        # Normalize job type
        if job_type.lower() in ["full time", "full-time", "full time.", "full-time."]:
            job_type = "full-time"
        elif job_type.lower() in ["part time", "part-time", "part time.", "part-time."]:
            job_type = "part-time"
        elif job_type.lower() in ["contract", "contractor"]:
            job_type = "contract"
        else:
            job_type = "full-time"  # Default
        
        return JobListing(
            title=title,
            company=company,
            location=location,
            job_type=job_type,
            description=description,
            source=self.name,
            source_url=source_url,
            apply_url=apply_url,
            posted_date=posted_date,
        )
