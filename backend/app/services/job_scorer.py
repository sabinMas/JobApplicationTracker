"""
Job Scoring Service - Uses Cerebras AI to score job relevance

Scores jobs 1-10 based on:
- Skill match
- Salary alignment
- Company reputation
- Growth potential
- Location preference
"""

import json
import logging
from typing import Optional, Dict, Any
import httpx
import os
from datetime import datetime

logger = logging.getLogger(__name__)


class JobScorer:
    """Score jobs by relevance using Cerebras AI"""

    def __init__(self):
        self.api_key = os.getenv("CEREBRAS_API_KEY")
        self.base_url = "https://api.cerebras.ai/v1"
        self.model = "llama-3.1-70b"
        self.client = None

    async def score_job(
        self,
        job_title: str,
        company: str,
        description: str,
        salary_min: Optional[float] = None,
        salary_max: Optional[float] = None,
        location: Optional[str] = None,
        user_profile: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Score a single job for relevance

        Returns:
            {
                "score": 8.5,  # 1-10 scale
                "reasoning": "Great salary match, strong skill alignment...",
                "strengths": ["high salary", "remote", "skill match"],
                "concerns": ["small company"],
                "recommendation": "SUBMIT"  # or SKIP
            }
        """
        try:
            prompt = self._build_scoring_prompt(
                job_title,
                company,
                description,
                salary_min,
                salary_max,
                location,
                user_profile,
            )

            # Call Cerebras API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/chat/completions",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "model": self.model,
                        "messages": [{"role": "user", "content": prompt}],
                        "temperature": 0.3,  # More deterministic
                        "max_tokens": 500,
                    },
                    timeout=30.0,
                )

            if response.status_code != 200:
                logger.error(f"Cerebras API error: {response.status_code}")
                return self._default_score("API Error")

            result = response.json()
            content = result["choices"][0]["message"]["content"]

            # Parse response
            return self._parse_scoring_response(content)

        except httpx.TimeoutException:
            logger.warning(f"Timeout scoring job: {job_title}")
            return self._default_score("Timeout")
        except Exception as e:
            logger.error(f"Error scoring job {job_title}: {e}")
            return self._default_score(str(e))

    def _build_scoring_prompt(self, job_title, company, description, salary_min, salary_max, location, user_profile):
        """
        Build the prompt for Cerebras to score the job

        Scoring criteria:
        - 8-10: Excellent match (high salary, strong skills, great company)
        - 6-7: Good match (some concerns but overall positive)
        - 4-5: Moderate match (significant tradeoffs)
        - 1-3: Poor match (major concerns, likely waste of time)
        """

        salary_info = ""
        if salary_min and salary_max:
            salary_info = f"Salary range: ${salary_min:,} - ${salary_max:,}"
        elif salary_min:
            salary_info = f"Minimum salary: ${salary_min:,}"

        location_info = f"Location: {location}" if location else "Location: Remote preferred"

        user_info = ""
        if user_profile:
            user_info = f"""
User Profile:
- Target salary: ${user_profile.get('target_salary', 150000):,}
- Preferred locations: {', '.join(user_profile.get('preferred_locations', ['Remote']))}
- Skills: {', '.join(user_profile.get('skills', [])[:10])}
- Experience level: {user_profile.get('experience_level', 'Mid-level')}
            """

        prompt = f"""
Score this job on a scale of 1-10 based on how well it matches for a software engineer.

Job Details:
Title: {job_title}
Company: {company}
Description: {description[:1000]}...
{salary_info}
{location_info}

{user_info}

Scoring Criteria:
- 8-10: Excellent match (strong salary, skill alignment, growth potential)
- 6-7: Good match (most factors positive)
- 4-5: Moderate match (some concerns)
- 1-3: Poor match (major red flags)

Provide your response in this exact JSON format:
{{
    "score": <number 1-10>,
    "reasoning": "<2-3 sentence explanation>",
    "strengths": ["<strength 1>", "<strength 2>"],
    "concerns": ["<concern if any>"],
    "recommendation": "<SUBMIT or SKIP>"
}}

Respond ONLY with the JSON, no other text.
"""

        return prompt

    def _parse_scoring_response(self, content: str) -> Dict[str, Any]:
        """
        Parse Cerebras response and extract score
        """
        try:
            # Extract JSON from response
            content = content.strip()
            if content.startswith("```"):
                content = content.split("```")[1]
                if content.startswith("json"):
                    content = content[4:]

            data = json.loads(content)

            # Validate required fields
            score = float(data.get("score", 5))
            score = max(1, min(10, score))  # Clamp 1-10

            return {
                "score": score,
                "reasoning": data.get("reasoning", "N/A"),
                "strengths": data.get("strengths", []),
                "concerns": data.get("concerns", []),
                "recommendation": data.get("recommendation", "SKIP"),
                "parsed_at": datetime.utcnow().isoformat(),
            }

        except json.JSONDecodeError:
            logger.warning(f"Failed to parse JSON response: {content[:100]}")
            return self._default_score("Parse Error")
        except Exception as e:
            logger.error(f"Error parsing score response: {e}")
            return self._default_score(str(e))

    def _default_score(self, reason: str) -> Dict[str, Any]:
        """
        Return default score when API fails
        Default to 5 (medium) to avoid missing jobs
        """
        return {
            "score": 5.0,
            "reasoning": f"Could not score job: {reason}. Defaulting to 5.",
            "strengths": [],
            "concerns": [reason],
            "recommendation": "SKIP",  # Skip on error (conservative approach)
            "is_default": True,
        }

    async def score_multiple_jobs(
        self, jobs: list, user_profile: Optional[Dict[str, Any]] = None
    ) -> list:
        """
        Score multiple jobs (batch processing)
        """
        scored_jobs = []
        for job in jobs:
            try:
                score_result = await self.score_job(
                    job_title=job.get("title"),
                    company=job.get("company"),
                    description=job.get("description", ""),
                    salary_min=job.get("salary_min"),
                    salary_max=job.get("salary_max"),
                    location=job.get("location"),
                    user_profile=user_profile,
                )
                scored_jobs.append({**job, **score_result})
            except Exception as e:
                logger.error(f"Error scoring job {job.get('title')}: {e}")
                scored_jobs.append({**job, **self._default_score(str(e))})

        return scored_jobs


# Singleton instance
_scorer = None


async def get_scorer() -> JobScorer:
    """Get or create scorer instance"""
    global _scorer
    if _scorer is None:
        _scorer = JobScorer()
    return _scorer
