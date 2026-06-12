"""
LinkedIn Job API source.

LinkedIn API integration for fetching jobs.
Requires OAuth 2.0 credentials (Client ID, Secret).
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


class LinkedInJobSource(JobSource):
    """LinkedIn Jobs API source."""

    def __init__(
        self,
        client_id: Optional[str] = None,
        client_secret: Optional[str] = None,
        access_token: Optional[str] = None,
    ):
        """
        Args:
            client_id: LinkedIn OAuth client ID
            client_secret: LinkedIn OAuth client secret
            access_token: Cached access token (for subsequent requests)
        """
        self.name = "LinkedIn"
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token = access_token
        self.is_configured = bool(client_id and client_secret)

        # LinkedIn API endpoints
        self.auth_url = "https://www.linkedin.com/oauth/v2/accessToken"
        self.api_base = "https://api.linkedin.com/v2"

    async def _get_access_token(self) -> Optional[str]:
        """Get OAuth 2.0 access token using client credentials."""
        logger = get_logger_instance()

        if self.access_token:
            return self.access_token

        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.auth_url,
                    data={
                        "grant_type": "client_credentials",
                        "client_id": self.client_id,
                        "client_secret": self.client_secret,
                    },
                )
                response.raise_for_status()

                data = response.json()
                self.access_token = data.get("access_token")

                logger.info(
                    "LinkedIn access token obtained",
                    extra_fields={
                        "source": self.name,
                        "expires_in": data.get("expires_in"),
                    },
                )

                return self.access_token

        except Exception as e:
            logger.error(
                f"Failed to get LinkedIn access token: {e}",
                extra_fields={
                    "source": self.name,
                    "error": str(e),
                },
            )
            return None

    async def fetch_jobs(self) -> List[JobListing]:
        """
        Fetch jobs from LinkedIn API.

        Note: LinkedIn's official jobs API has limitations. This implementation
        demonstrates the integration pattern. For production use, consider:
        - LinkedIn Recruiter API (requires special access)
        - LinkedIn Jobs data feeds (if available to your account)
        - Web scraping with Playwright (as fallback)

        Returns:
            List of JobListing objects
        """
        logger = get_logger_instance()

        if not self.is_configured:
            logger.warning(
                "LinkedIn source not configured",
                extra_fields={
                    "source": self.name,
                    "reason": "Missing client_id or client_secret",
                },
            )
            return []

        try:
            logger.info(
                "Fetching LinkedIn jobs",
                extra_fields={
                    "source": self.name,
                },
            )

            access_token = await self._get_access_token()
            if not access_token:
                logger.error(
                    "Failed to authenticate with LinkedIn",
                    extra_fields={
                        "source": self.name,
                    },
                )
                return []

            # Note: LinkedIn's standard API doesn't provide a direct jobs endpoint
            # This is a placeholder for the integration pattern
            # In production, you would use:
            # 1. LinkedIn Recruiter API (requires special partnership)
            # 2. Job posting data feeds (if available to your account)
            # 3. Web scraping for authenticated user jobs (see playwright_service)

            logger.info(
                "LinkedIn jobs API integration ready",
                extra_fields={
                    "source": self.name,
                    "status": "awaiting_api_endpoint",
                    "note": "LinkedIn standard API does not provide job search endpoint",
                },
            )

            # Return empty list - LinkedIn API doesn't expose job search
            # This is expected behavior. Use Recruiter API or scraping instead.
            return []

        except Exception as e:
            logger.error(
                f"Failed to fetch LinkedIn jobs: {e}",
                extra_fields={
                    "source": self.name,
                    "error": str(e),
                },
            )
            return []

    async def get_external_id(self, job: JobListing) -> str:
        """Generate unique ID for job."""
        import hashlib

        id_str = f"{job.title}_{job.company}_{job.source_url}".lower()
        return hashlib.md5(id_str.encode()).hexdigest()
