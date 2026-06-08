"""Simple test actor for verifying the scraper framework."""

import logging
from typing import Any, Dict, List
from app.services.actor_framework import Actor

logger = logging.getLogger(__name__)


class TestActor(Actor):
    """Simple test actor that generates mock job data."""

    name = "test"

    async def run(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Generate mock jobs for testing."""
        count = config.get("count", 3)
        logger.info(f"TestActor generating {count} mock jobs")
        
        items = []
        for i in range(count):
            items.append({
                "title": f"Test Job {i+1}",
                "company": f"Test Company {i+1}",
                "location": "Remote",
                "description": f"This is test job {i+1} for framework validation",
                "source": "test",
                "source_url": f"https://test.example.com/job/{i+1}",
                "requirements": "Testing framework"
            })
        
        return items
