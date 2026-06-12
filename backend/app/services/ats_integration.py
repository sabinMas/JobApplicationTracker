"""
ATS Platform integrations: Greenhouse, Workday, Lever, Taleo, BambooHR, Ashby, etc.
Each platform has specific APIs and quirks for automation.
"""

import httpx
from typing import Optional


# Greenhouse Jobs API (public, no auth needed for reading)
async def get_greenhouse_board(board_slug: str) -> list[dict]:
    """Fetch jobs from a Greenhouse job board."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"https://api.greenhouse.io/v1/boards/{board_slug}/jobs?content=true",
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        data = resp.json()
        return data.get("jobs", [])


async def extract_greenhouse_apply_url(job_id: int, board_slug: str) -> Optional[str]:
    """Get the application form URL for a Greenhouse job."""
    jobs = await get_greenhouse_board(board_slug)
    for job in jobs:
        if job.get("id") == job_id:
            return job.get("absolute_url")
    return None


# Lever API integration
async def get_lever_jobs(company_handle: str) -> list[dict]:
    """Fetch jobs from a Lever company page."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            "https://api.lever.co/v0/postings?mode=json",
            params={"org": company_handle},
            timeout=10,
        )
        if resp.status_code != 200:
            return []
        return resp.json()


# LinkedIn Jobs API (if using LinkedIn Talent Solutions)
async def get_linkedin_job_apply_url(job_id: str) -> Optional[str]:
    """
    LinkedIn job apply URLs follow this pattern:
    https://www.linkedin.com/jobs/view/{job_id}/
    Some companies use LinkedIn Easy Apply, others redirect to their ATS.
    """
    return f"https://www.linkedin.com/jobs/view/{job_id}/"


# ATS Platform detection
def detect_ats_from_url(url: str) -> str:
    """Detect which ATS platform a job URL uses."""
    url_lower = url.lower()

    if "greenhouse.io" in url_lower or "apply.greenhouse.io" in url_lower:
        return "greenhouse"
    elif "lever.co" in url_lower:
        return "lever"
    elif "workday.com" in url_lower:
        return "workday"
    elif "taleo" in url_lower or "icims" in url_lower:
        return "taleo"
    elif "bamboohr" in url_lower:
        return "bamboohr"
    elif "ashby" in url_lower:
        return "ashby"
    elif "linkedin.com" in url_lower:
        return "linkedin"
    elif "indeed.com" in url_lower:
        return "indeed"
    elif "ziprecruiter.com" in url_lower:
        return "ziprecruiter"
    else:
        return "other"


def get_submit_button_selectors(ats_type: str) -> list[str]:
    """Return common selectors for submit buttons by ATS type."""
    selectors = {
        "greenhouse": [
            "button:has-text('Submit Application')",
            "button:has-text('Apply Now')",
            "button[type='submit']",
        ],
        "lever": [
            "button:has-text('Apply')",
            "button:has-text('Submit Application')",
            "[data-test='apply-button']",
        ],
        "workday": [
            "button:has-text('Submit')",
            "button:has-text('Continue')",
            "[aria-label*='Submit']",
        ],
        "default": [
            "button:has-text('Submit')",
            "button:has-text('Apply')",
            "button:has-text('Send')",
            "input[type='submit']",
            "button[type='submit']",
        ],
    }
    return selectors.get(ats_type, selectors["default"])


def get_form_field_selectors(ats_type: str) -> dict[str, list[str]]:
    """Return CSS selectors for common form fields by ATS type."""
    return {
        "email": [
            "input[type='email']",
            "input[name*='email' i]",
            "[aria-label*='email' i]",
        ],
        "phone": [
            "input[type='tel']",
            "input[name*='phone' i]",
            "[aria-label*='phone' i]",
        ],
        "name": [
            "input[name*='name' i]",
            "input[placeholder*='name' i]",
            "[aria-label*='name' i]",
        ],
        "linkedin": [
            "input[placeholder*='linkedin' i]",
            "input[name*='linkedin' i]",
            "[aria-label*='linkedin' i]",
        ],
        "resume": [
            "input[type='file']",
            "input[name*='resume' i]",
            "input[name*='cv' i]",
            "[aria-label*='resume' i]",
        ],
    }
