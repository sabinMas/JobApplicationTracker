"""
Lever ATS platform router.

Uses Lever API for direct submission when available.
Falls back to form filling if API is not accessible.

Lever API docs: https://api.lever.co/v0/applications
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


class LeverRouter(ATSRouter):
    """Lever ATS direct API submission"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("LEVER_API_KEY")
        self.base_url = "https://api.lever.co/v0"
    
    async def can_handle(self, apply_url: str) -> bool:
        """Check if this is a Lever URL"""
        return "lever.co" in apply_url.lower()
    
    async def submit_application(
        self,
        application_id: int,
        job_url: str,
        profile: dict,
        resume_path: Optional[str] = None,
        cover_letter_path: Optional[str] = None,
    ) -> dict:
        """Submit application via Lever API"""
        
        start_time = time.time()
        logger = get_logger()
        
        try:
            # Extract posting ID from URL
            posting_id = self._extract_posting_id(job_url)
            if not posting_id:
                logger.error("Could not extract posting ID from URL", extra_fields={
                    "application_id": application_id,
                    "url": job_url,
                })
                return {
                    "status": "failed",
                    "duration_ms": int((time.time() - start_time) * 1000),
                    "message": "Could not extract Lever posting ID from URL",
                    "ats_platform": "lever",
                    "error_message": "Invalid URL format",
                }
            
            # Build form data for API
            data = {
                "name": profile.get("full_name", ""),
                "email": profile.get("email", ""),
                "phone": profile.get("phone", ""),
                "resume": None,
                "cover_letter": None,
                "urls": [],
                "comments": "",
            }
            
            # Add optional fields if available
            if profile.get("linkedin_url"):
                data["urls"].append({"label": "LinkedIn", "url": profile.get("linkedin_url")})
            
            if profile.get("portfolio_url"):
                data["urls"].append({"label": "Portfolio", "url": profile.get("portfolio_url")})
            
            if profile.get("github_url"):
                data["urls"].append({"label": "GitHub", "url": profile.get("github_url")})
            
            # Remove empty urls list if no URLs provided
            if not data["urls"]:
                del data["urls"]
            
            # Prepare files
            files = {}
            
            # Attach resume if provided
            if resume_path and os.path.exists(resume_path):
                with open(resume_path, "rb") as f:
                    resume_content = f.read()
                    data["resume"] = resume_content.hex()  # Lever expects base64-encoded resume
                    files["resume"] = ("resume.pdf", resume_content, "application/pdf")
            
            # Attach cover letter if provided
            if cover_letter_path and os.path.exists(cover_letter_path):
                with open(cover_letter_path, "rb") as f:
                    cover_letter_content = f.read()
                    data["cover_letter"] = cover_letter_content.hex()
                    files["cover_letter"] = ("cover_letter.pdf", cover_letter_content, "application/pdf")
            
            # Submit via Lever API
            logger.info("Submitting to Lever API", extra_fields={
                "application_id": application_id,
                "posting_id": posting_id,
            })
            
            headers = {
                "Authorization": f"Basic {self.api_key}" if self.api_key else "",
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.base_url}/applications",
                    json=data,
                    headers=headers,
                )
            
            duration_ms = int((time.time() - start_time) * 1000)
            
            if resp.status_code in [200, 201, 204]:
                logger.info("Lever submission successful", extra_fields={
                    "application_id": application_id,
                    "status_code": resp.status_code,
                    "duration_ms": duration_ms,
                })
                return {
                    "status": "success",
                    "duration_ms": duration_ms,
                    "message": "Application submitted via Lever API",
                    "ats_platform": "lever",
                }
            else:
                error_msg = f"Lever API error {resp.status_code}"
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
                    "ats_platform": "lever",
                    "error_message": f"API returned {resp.status_code}",
                }
        
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            logger.error(f"Lever submission error: {e}", extra_fields={
                "application_id": application_id,
                "error": str(e),
                "duration_ms": duration_ms,
            })
            return {
                "status": "failed",
                "duration_ms": duration_ms,
                "message": f"Lever API error: {str(e)[:100]}",
                "ats_platform": "lever",
                "error_message": str(e),
            }
    
    def _extract_posting_id(self, url: str) -> str:
        """
        Extract Lever posting ID from URL.
        
        Expected format: https://company.lever.co/apply/posting-id
        Also handles: https://company.lever.co/apply/posting-id?...
        Also handles: https://jobs.company.com/apply/posting-id (Lever-hosted custom domain)
        """
        # Try to match /apply/[posting-id] pattern
        match = re.search(r'/apply/([a-zA-Z0-9\-]+)', url)
        return match.group(1) if match else ""
