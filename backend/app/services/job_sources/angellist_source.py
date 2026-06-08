"""
Angel List (Wellfound) Job API source (stub).

Angel List API integration for fetching startup jobs.
Requires Angel List API key.

This is a stub implementation. API key and configuration will be provided later.
"""

from typing import List, Optional

from .base import JobSource, JobListing
from ...logging_config import get_logger

# Defer logger
_logger = None


def get_logger_instance():
    global _logger
    if _logger is None:
        from ...logging_config import get_logger as create_logger
        _logger = create_logger(__name__)
    return _logger


class AngelListJobSource(JobSource):
    """Angel List Jobs API source (stub)."""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_base_url: str = "https://api.wellfound.com/1",
    ):
        """
        Args:
            api_key: Angel List / Wellfound API key
            api_base_url: API base URL (default is Wellfound)
        """
        self.name = "Angel List"
        self.api_key = api_key
        self.api_base_url = api_base_url
        self.is_configured = bool(api_key)
    
    async def fetch_jobs(self) -> List[JobListing]:
        """
        Fetch jobs from Angel List API.
        
        Returns:
            Empty list (stub). Will be implemented when credentials provided.
        """
        logger = get_logger_instance()
        
        if not self.is_configured:
            logger.warning("Angel List source not configured", extra_fields={
                "source": self.name,
                "reason": "Missing API key",
            })
            return []
        
        logger.info("Angel List job fetch stub (not yet implemented)", extra_fields={
            "source": self.name,
            "status": "awaiting_configuration",
        })
        
        # TODO: Implement Angel List API integration
        # 1. Use api_key to authenticate
        # 2. Query startup jobs by skills, location, etc.
        # 3. Parse results and return JobListing objects
        # API reference: https://wellfound.com/api/docs
        
        return []
    
    async def get_external_id(self, job: JobListing) -> str:
        """Generate unique ID for job."""
        import hashlib
        id_str = f"{job.title}_{job.company}_{job.source_url}".lower()
        return hashlib.md5(id_str.encode()).hexdigest()
