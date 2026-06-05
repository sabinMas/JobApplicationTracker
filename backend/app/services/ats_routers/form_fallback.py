"""
Form filler fallback router.

Generic form filler for unknown ATS platforms using Playwright.
This router always accepts requests and serves as the last resort
when no platform-specific router can handle the job URL.
"""

import time
from typing import Optional

from .base import ATSRouter
from ..playwright_service import PlaywrightService
from ..logging_config import get_logger

logger = get_logger(__name__)


class FormFillerRouter(ATSRouter):
    """Generic form filler for unknown ATS platforms"""
    
    def __init__(self):
        self.playwright_service = PlaywrightService()
    
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
        
        This implements the full form detection and filling logic
        that was previously in auto_apply.py
        """
        
        start_time = time.time()
        
        try:
            logger.info("Starting generic form filling", extra_fields={
                "application_id": application_id,
                "job_url": job_url,
            })
            
            # Use existing playwright logic
            # This delegates to the playwright_service
            result = await self.playwright_service.fill_and_submit_form(
                application_id=application_id,
                job_url=job_url,
                profile=profile,
                resume_path=resume_path,
                cover_letter_path=cover_letter_path,
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            # Add timing and ensure proper format
            result["duration_ms"] = duration_ms
            result["ats_platform"] = result.get("ats_platform", "unknown")
            
            logger.info("Form filling completed", extra_fields={
                "application_id": application_id,
                "status": result.get("status"),
                "duration_ms": duration_ms,
            })
            
            return result
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Form filling error: {e}", extra_fields={
                "application_id": application_id,
                "error": str(e),
                "duration_ms": duration_ms,
            })
            return {
                "status": "failed",
                "duration_ms": duration_ms,
                "message": f"Form filling error: {str(e)[:100]}",
                "ats_platform": "unknown",
                "error_message": str(e),
            }
