"""
ATS Router module for intelligent application submission routing.

This module provides an abstraction layer that routes job applications
to platform-specific submission handlers:

- GreenhouseRouter: Uses Greenhouse API for direct submission
- LeverRouter: Could use Lever API (future)
- LinkedInRouter: Could use LinkedIn API (future)
- FormFillerRouter: Fallback generic form filling (always last)

Usage:
    from app.services.ats_routers import route_and_submit
    
    result = await route_and_submit(
        application_id=123,
        job_url="https://company.greenhouse.io/jobs/456",
        profile={...},
        resume_path="/path/to/resume.pdf",
        cover_letter_path="/path/to/cover_letter.pdf",
    )
"""

from .form_fallback import FormFillerRouter
from .greenhouse import GreenhouseRouter
from ..logging_config import get_logger

logger = get_logger(__name__)

# Router instances (order matters - checked in order)
_routers = [
    GreenhouseRouter(),
    FormFillerRouter(),  # Always last (fallback)
]


async def route_and_submit(
    application_id: int,
    job_url: str,
    profile: dict,
    resume_path: str,
    cover_letter_path: str,
) -> dict:
    """
    Route application to appropriate handler and submit.
    
    Args:
        application_id: Database application ID for tracking
        job_url: URL of the job application
        profile: User profile dict
        resume_path: Path to resume file
        cover_letter_path: Path to cover letter file
    
    Returns:
        Result dict with status, message, platform, etc.
    """
    
    # Try each router in order
    for router in _routers:
        if await router.can_handle(job_url):
            router_name = router.__class__.__name__
            logger.info(f"Routing to {router_name}", extra_fields={
                "application_id": application_id,
                "router": router_name,
            })
            return await router.submit_application(
                application_id=application_id,
                job_url=job_url,
                profile=profile,
                resume_path=resume_path,
                cover_letter_path=cover_letter_path,
            )
    
    # Should never reach here (FormFillerRouter accepts everything)
    error_msg = "No suitable router found"
    logger.error(error_msg, extra_fields={
        "application_id": application_id,
    })
    return {
        "status": "failed",
        "duration_ms": 0,
        "message": error_msg,
        "ats_platform": "unknown",
        "error_message": "No router available",
    }


__all__ = [
    "route_and_submit",
    "FormFillerRouter",
    "GreenhouseRouter",
]
