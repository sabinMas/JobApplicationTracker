"""LinkedIn job scraper actor."""

import asyncio
import logging
from typing import Any, Dict, List
from app.services.actor_framework import Actor
from app.services.playwright_service import PlaywrightService
from app.services.ai_service import extract_job

logger = logging.getLogger(__name__)


class LinkedInActor(Actor):
    """Scrapes LinkedIn jobs for a given query."""

    name = "linkedin"

    async def run(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape LinkedIn jobs.

        Config:
        {
            "query": "software engineer",
            "location": "United States",
            "max_pages": 3,
            "experience_level": "entry"
        }
        """
        query = config.get("query", "")
        location = config.get("location", "United States")
        max_pages = config.get("max_pages", 1)

        if not query:
            raise ValueError("query is required")

        items = []
        pw = PlaywrightService()

        try:
            base_url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={query}"
                f"&location={location}"
            )

            for page in range(max_pages):
                url = f"{base_url}&start={page * 25}"
                logger.info(f"Scraping page {page + 1}: {url}")

                html = await pw.fetch_page(url, timeout=30000)
                if not html:
                    logger.warning(f"Failed to fetch page {page + 1}")
                    continue

                # Parse job listings from HTML
                job_urls = await self._extract_job_urls(html)
                logger.info(f"Found {len(job_urls)} jobs on page {page + 1}")

                for job_url in job_urls:
                    try:
                        # Rate limiting to prevent IP bans
                        await asyncio.sleep(0.5)

                        job_html = await pw.fetch_page(job_url, timeout=20000)
                        if job_html:
                            job_data = await extract_job(job_html)
                            if job_data and job_data.get("title"):
                                job_data["source"] = "linkedin"
                                job_data["source_url"] = job_url
                                items.append(job_data)
                                logger.debug(
                                    f"Extracted: {job_data.get('title')} at {job_data.get('company')}"
                                )
                    except Exception as e:
                        logger.error(f"Error scraping {job_url}: {e}")
                        continue

        finally:
            await pw.close()

        logger.info(f"LinkedIn actor scraped {len(items)} jobs")
        return items

    async def _extract_job_urls(self, html: str) -> List[str]:
        """Extract job listing URLs from LinkedIn search page HTML."""
        # Simple regex-based extraction of LinkedIn job URLs
        import re

        pattern = r"https://www\.linkedin\.com/jobs/view/\d+[/?]"
        urls = list(set(re.findall(pattern, html)))
        return urls[:10]  # Limit to first 10 per page
