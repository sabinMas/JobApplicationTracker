"""GitHub Jobs scraper actor."""

import asyncio
import logging
from typing import Any, Dict, List
from app.services.actor_framework import Actor
from app.services.playwright_service import PlaywrightService
from app.services.ai_service import extract_job

logger = logging.getLogger(__name__)


class GitHubActor(Actor):
    """Scrapes GitHub Jobs listings."""

    name = "github"

    async def run(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape GitHub Jobs.

        Config:
        {
            "query": "python developer",
            "location": "san francisco",
            "max_results": 25
        }
        """
        query = config.get("query", "").replace(" ", "+")
        location = config.get("location", "").replace(" ", "+")
        max_results = config.get("max_results", 25)

        if not query:
            raise ValueError("query is required")

        items = []
        pw = PlaywrightService()

        try:
            # GitHub Jobs search URL
            url = f"https://jobs.github.com/positions?description={query}"
            if location:
                url += f"&location={location}"

            logger.info(f"Scraping GitHub Jobs: {url}")

            html = await pw.fetch_page(url, timeout=30000)
            if not html:
                logger.warning("Failed to fetch GitHub Jobs page")
                return items

            # Extract job listings from the page
            # GitHub Jobs shows job IDs as links in the page
            import re
            job_links = re.findall(
                r'href="(/positions/([a-f0-9\-]+))"',
                html
            )[:5]  # Limit to first 5

            logger.info(f"Found {len(job_links)} job links on GitHub Jobs")

            for job_path, job_id in job_links:
                try:
                    # Rate limiting
                    await asyncio.sleep(0.5)

                    job_url = f"https://jobs.github.com{job_path}"
                    job_html = await pw.fetch_page(job_url, timeout=20000)

                    if job_html:
                        job_data = await extract_job(job_html)
                        if job_data and job_data.get("title"):
                            job_data["source"] = "github"
                            job_data["source_url"] = job_url
                            items.append(job_data)
                            logger.debug(f"Extracted: {job_data.get('title')}")

                            if len(items) >= max_results:
                                break
                except Exception as e:
                    logger.error(f"Error scraping GitHub job {job_id}: {e}")
                    continue

        finally:
            await pw.close()

        logger.info(f"GitHub actor scraped {len(items)} jobs")
        return items
