"""
Form filler fallback router.

Generic form filler for unknown ATS platforms using Playwright.
This router always accepts requests and serves as the last resort
when no platform-specific router can handle the job URL.

NOTE: This is a stub implementation. The actual form filling logic
from the existing auto_apply.py will be integrated here in future updates.
"""

import time
from typing import Optional

from .base import ATSRouter

# Defer logger creation until it's actually needed
_logger = None


def get_logger():
    global _logger
    if _logger is None:
        from ...logging_config import get_logger as create_logger

        _logger = create_logger(__name__)
    return _logger


class FormFillerRouter(ATSRouter):
    """Generic form filler for unknown ATS platforms"""

    async def can_handle(self, apply_url: str) -> bool:
        """
        Generic form filler always accepts (last resort).

        This router is the fallback for all ATS platforms.
        """
        return True

    async def submit_application(
        self,
        application_id: int,
        job_url: str,
        profile: dict,
        resume_path: Optional[str] = None,
        cover_letter_path: Optional[str] = None,
    ) -> dict:
        """
        Submit application using generic form filling with Playwright.

        This is a stub implementation. The actual form detection and filling logic
        from the existing auto_apply.py will be integrated here in future updates.

        For now, returns a "not_implemented" status to indicate this handler
        exists but the full implementation is pending integration.
        """

        start_time = time.time()
        logger = get_logger()

        try:
            logger.info(
                "Form filling router invoked (stub implementation)",
                extra_fields={
                    "application_id": application_id,
                    "job_url": job_url,
                },
            )

            # TODO: Integrate actual form filling logic from auto_apply.py
            # This will include:
            # - Starting Playwright session
            # - Detecting form fields
            # - Filling fields with profile data
            # - Uploading documents
            # - Finding and clicking submit button
            # - Verifying submission success

            duration_ms = int((time.time() - start_time) * 1000)

            return {
                "status": "failed",
                "duration_ms": duration_ms,
                "message": "Form filling router not fully implemented yet",
                "ats_platform": "unknown",
                "error_message": "Form filler stub - awaiting Playwright integration",
            }

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(
                f"Form filling error: {e}",
                extra_fields={
                    "application_id": application_id,
                    "error": str(e),
                    "duration_ms": duration_ms,
                },
            )
            return {
                "status": "failed",
                "duration_ms": duration_ms,
                "message": f"Form filling error: {str(e)[:100]}",
                "ats_platform": "unknown",
                "error_message": str(e),
            }
