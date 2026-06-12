"""Indeed job scraper actor."""

import asyncio
import logging
import re
from typing import Any, Dict, List
from app.services.actor_framework import Actor
from app.services.playwright_service import PlaywrightService
from app.services.ai_service import extract_job

logger = logging.getLogger(__name__)


class IndeedActor(Actor):
    """Scrapes Indeed jobs for a given query."""

    name = "indeed"

    async def run(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Scrape Indeed jobs.

        Config:
        {
            "query": "python developer",
            "location": "united states",
            "max_results": 50,
            "experience_level": "entry"
        }
        """
        query = config.get("query", "").replace(" ", "+")
        location = config.get("location", "united states").replace(" ", "+")
        max_results = config.get("max_results", 25)

        if not query:
            raise ValueError("query is required")

        items = []
        pw = PlaywrightService()

        try:
            # Indeed search URL
            base_url = f"https://www.indeed.com/jobs?q={query}&l={location}"

            logger.info(f"Scraping Indeed: {base_url}")

            html = await pw.fetch_page(base_url, timeout=30000)
            if not html:
                logger.warning("Failed to fetch Indeed search page")
                return items

            # Extract job listing URLs
            job_urls = re.findall(
                r"https://www\.indeed\.com/rc/clk\?.*?jk=([a-f0-9]+)", html
            )[:5]  # Limit to first 5

            logger.info(f"Found {len(job_urls)} job links on Indeed")

            for job_id in job_urls:
                try:
                    # Rate limiting to prevent IP bans
                    await asyncio.sleep(0.5)

                    job_url = f"https://www.indeed.com/viewjob?jk={job_id}"
                    job_html = await pw.fetch_page(job_url, timeout=20000)

                    if job_html:
                        job_data = await extract_job(job_html)
                        if job_data and job_data.get("title"):
                            job_data["source"] = "indeed"
                            job_data["source_url"] = job_url
                            items.append(job_data)
                            logger.debug(f"Extracted: {job_data.get('title')}")

                            if len(items) >= max_results:
                                break
                except Exception as e:
                    logger.error(f"Error scraping Indeed job {job_id}: {e}")
                    continue

        finally:
            await pw.close()

        logger.info(f"Indeed actor scraped {len(items)} jobs")
        return items
