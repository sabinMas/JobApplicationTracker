"""
Fire-and-forget webhook notifications for application lifecycle events.

Posts to the Keystroke automation project (see keystroke-agents/), which
emails a confirmation. Never raises — a notification failure must not affect
the auto-apply flow that triggered it.
"""

import os

import httpx

from ..logging_config import get_logger

logger = get_logger(__name__)


async def notify_application_submitted(
    application_id: int,
    job_title: str,
    company: str,
    apply_url: str | None,
    ats_platform: str | None,
    applied_at: str,
) -> None:
    """POST an application-submitted event to the configured webhook, if any."""
    webhook_url = os.getenv("KEYSTROKE_APPLICATION_WEBHOOK_URL")
    if not webhook_url:
        return

    payload = {
        "applicationId": application_id,
        "jobTitle": job_title,
        "company": company,
        "applyUrl": apply_url,
        "atsPlatform": ats_platform,
        "appliedAt": applied_at,
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(webhook_url, json=payload)
            response.raise_for_status()
    except Exception as exc:
        logger.warning(
            "application-submitted webhook notification failed",
            extra_fields={"application_id": application_id, "error": str(exc)},
        )
