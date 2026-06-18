"""
Abstract base class for ATS platform routers.

Each router handles submission to a specific ATS platform or acts as a fallback.
"""

from abc import ABC, abstractmethod
from typing import Optional


class ATSRouter(ABC):
    """Base class for ATS platform handlers"""

    @abstractmethod
    async def can_handle(self, apply_url: str) -> bool:
        """
        Check if this router can handle the given apply URL.

        Args:
            apply_url: The job application URL

        Returns:
            True if this router should handle this URL, False otherwise
        """
        pass

    @abstractmethod
    async def submit_application(
        self,
        application_id: int,
        job_url: str,
        profile: dict,
        resume_path: Optional[str] = None,
        cover_letter_path: Optional[str] = None,
    ) -> dict:
        """
        Submit application using this ATS platform.

        Args:
            application_id: Database application ID for tracking
            job_url: URL of the job application page/form
            profile: User profile dict with name, email, phone, skills, etc.
            resume_path: Path to resume file (PDF)
            cover_letter_path: Path to cover letter file (PDF)

        Returns:
            {
                "status": "success" | "failed" | "submitted_unverified",
                "duration_ms": int,  # How long the submission took
                "message": str,  # Human readable result
                "ats_platform": str,  # Platform name (greenhouse, lever, etc)
                "error_message": str,  # Only if status is failed
                "form_fields_detected": int,  # Optional: # of form fields
                "fields_filled": int,  # Optional: # of fields we filled
            }
        """
        pass
