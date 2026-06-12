"""
Job page scraping and Greenhouse public API integration.
"""
import httpx
from bs4 import BeautifulSoup
from datetime import datetime, timezone
from typing import Optional
import asyncio


HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


async def scrape_job_page(url: str) -> str:
    """
    Fetch a job posting page and return clean text content.
    Falls back gracefully if JS-heavy (returns whatever we can get).
    """
    async with httpx.AsyncClient(headers=HEADERS, follow_redirects=True, timeout=15) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            soup = BeautifulSoup(resp.text, "html.parser")

            # Remove nav, footer, scripts, styles
            for tag in soup(["script", "style", "nav", "footer", "header", "aside"]):
                tag.decompose()

            # Try to find main content area
            main = (
                soup.find("main")
                or soup.find("article")
                or soup.find(id=lambda x: x and "job" in x.lower() if x else False)
                or soup.find(class_=lambda x: x and "job" in " ".join(x).lower() if x else False)
                or soup.body
            )
            if main:
                text = main.get_text(separator="\n", strip=True)
            else:
                text = soup.get_text(separator="\n", strip=True)

            # Clean up excessive blank lines
            lines = [l.strip() for l in text.splitlines() if l.strip()]
            return "\n".join(lines)

        except Exception as e:
            return f"Error scraping page: {str(e)}"


async def fetch_greenhouse_jobs(company_slug: str) -> list[dict]:
    """
    Fetch job listings from the Greenhouse public job board API.
    Returns a list of standardized job dicts.
    """
    url = f"https://boards.greenhouse.io/v1/boards/{company_slug}/jobs"
    async with httpx.AsyncClient(headers=HEADERS, timeout=10) as client:
        try:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            jobs = []
            for job in data.get("jobs", []):
                jobs.append({
                    "title": job.get("title", ""),
                    "company": data.get("board", {}).get("name", company_slug),
                    "location": job.get("location", {}).get("name", ""),
                    "source": "greenhouse",
                    "source_url": job.get("absolute_url", ""),
                    "apply_url": job.get("absolute_url", ""),
                    "description": job.get("content", ""),
                    "posted_date": job.get("updated_at", "")[:10] if job.get("updated_at") else None,
                    "scraped_at": datetime.now(timezone.utc).isoformat(),
                })
            return jobs
        except Exception:
            return []


def detect_ats_platform(url: str) -> str:
    """Detect ATS platform from a URL pattern."""
    url_lower = url.lower()
    if "greenhouse.io" in url_lower or "boards.greenhouse" in url_lower:
        return "greenhouse"
    elif "workday.com" in url_lower or "myworkdayjobs" in url_lower:
        return "workday"
    elif "lever.co" in url_lower:
        return "lever"
    elif "taleo" in url_lower:
        return "taleo"
    elif "bamboohr.com" in url_lower:
        return "bamboohr"
    elif "smartrecruiters" in url_lower:
        return "smartrecruiters"
    elif "jobvite" in url_lower:
        return "jobvite"
    elif "icims" in url_lower:
        return "icims"
    elif "ashbyhq" in url_lower:
        return "ashby"
    return "other"
