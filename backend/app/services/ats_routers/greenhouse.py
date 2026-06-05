"""
Greenhouse ATS platform router.

Uses Greenhouse API for direct submission when available.
Falls back to form filling if API is not accessible.
"""

import os
import re
import time
from typing import Optional
import httpx

from .base import ATSRouter

# Defer logger creation until it's actually needed
_logger = None


def get_logger():
    global _logger
    if _logger is None:
        from ...logging_config import get_logger as create_logger
        _logger = create_logger(__name__)
    return _logger


class GreenhouseRouter(ATSRouter):
    """Greenhouse ATS direct API submission"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GREENHOUSE_API_KEY")
        self.base_url = "https://api.greenhouse.io/v1"
    
    async def can_handle(self, apply_url: str) -> bool:
        """Check if this is a Greenhouse URL"""
        return "greenhouse" in apply_url.lower()
    
    async def submit_application(
        self,
        application_id: int,
        job_url: str,
        profile: dict,
        resume_path: Optional[str] = None,
        cover_letter_path: Optional[str] = None,
    ) -> dict:
        """Submit application via Greenhouse API"""
        
        start_time = time.time()
        logger = get_logger()
        
        try:
            # Extract job ID from URL
            job_id = self._extract_job_id(job_url)
            if not job_id:
                logger.error("Could not extract job ID from URL", extra_fields={
                    "application_id": application_id,
                    "url": job_url,
                })
                return {
                    "status": "failed",
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "message": "Could not extract Greenhouse job ID from URL",
                    "ats_platform": "greenhouse",
                    "error_message": "Invalid URL format",
                }
            
            # Build form data for API
            files = {}
            data = {
                "first_name": profile.get("full_name", "").split()[0] if profile.get("full_name") else "",
                "last_name": " ".join(profile.get("full_name", "").split()[1:]) if profile.get("full_name") else "",
                "email": profile.get("email", ""),
                "phone": profile.get("phone", ""),
            }
            
            # Attach resume if provided
            if resume_path and os.path.exists(resume_path):
                with open(resume_path, "rb") as f:
                    files["resume"] = ("resume.pdf", f.read(), "application/pdf")
            
            # Attach cover letter if provided
            if cover_letter_path and os.path.exists(cover_letter_path):
                with open(cover_letter_path, "rb") as f:
                    files["cover_letter"] = ("cover_letter.pdf", f.read(), "application/pdf")
            
            # Submit via Greenhouse API
            logger.info("Submitting to Greenhouse API", extra_fields={
                "application_id": application_id,
                "job_id": job_id,
            })
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/jobs/{job_id}/applications",
                    data=data,
                    files=files if files else None,
                    auth=("", self.api_key) if self.api_key else None,
                )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if resp.status_code in [200, 201]:
                logger.info("Greenhouse submission successful", extra_fields={
                    "application_id": application_id,
                    "status_code": resp.status_code,
                    "duration_ms": duration_ms,
                })
                return {
                    "status": "success",
                    "duration_ms": duration_ms,
                    "message": "Application submitted via Greenhouse API",
                    "ats_platform": "greenhouse",
                }
            else:
                error_msg = f"Greenhouse API error {resp.status_code}"
                logger.warning(error_msg, extra_fields={
                    "application_id": application_id,
                    "status_code": resp.status_code,
                    "response": resp.text[:500],
                    "duration_ms": duration_ms,
                })
                return {
                    "status": "failed",
                    "duration_ms": duration_ms,
                    "message": error_msg,
                    "ats_platform": "greenhouse",
                    "error_message": f"API returned {resp.status_code}",
                }
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Greenhouse submission error: {e}", extra_fields={
                "application_id": application_id,
                "error": str(e),
                "duration_ms": duration_ms,
            })
            return {
                "status": "failed",
                "duration_ms": duration_ms,
                "message": f"Greenhouse API error: {str(e)[:100]}",
                "ats_platform": "greenhouse",
                "error_message": str(e),
            }
    
    def _extract_job_id(self, url: str) -> str:
        """
        Extract Greenhouse job ID from URL.
        
        Expected format: https://company.greenhouse.io/jobs/123456
        Also handles: https://company.greenhouse.io/jobs/123456?...
        """
        # Try to match /jobs/XXXXXXXX pattern
        match = re.search(r'/jobs/(\d+)', url)
        return match.group(1) if match else ""
