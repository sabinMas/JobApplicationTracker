"""
Agentic scraper: an AI agent that drives a real browser through MCP tools.

Instead of per-site CSS selectors, a Bedrock Claude agent is given the
Playwright MCP browser tools plus a `submit_jobs` finishing tool. It navigates
the board, reads accessibility snapshots, paginates if needed, and submits
structured job postings. New job boards work without writing a new scraper.

Budget caps: MAX_TOOL_CALLS browser actions per run, bounded output tokens,
and a short pause between actions (rate-limit etiquette).
"""

import asyncio
import logging
import os
from typing import Any, Dict, List, Optional

import aioboto3
from pydantic import BaseModel, ValidationError

from app.services.actor_framework import Actor

# MCPBrowser is only available in the worker container (requires 'mcp' package)
MCPBrowser = None
try:
    from app.services.mcp_browser import MCPBrowser
except ImportError:
    pass

logger = logging.getLogger(__name__)

MAX_TOOL_CALLS = 15
ACTION_DELAY_SECONDS = 0.4
MODEL_ID = os.getenv("BEDROCK_FAST_MODEL", "anthropic.claude-3-haiku-20240307-v1:0")


class ScrapedJob(BaseModel):
    """Validation schema for jobs the agent submits."""

    title: str
    company: str
    location: Optional[str] = None
    job_type: Optional[str] = None
    apply_url: Optional[str] = None
    description: Optional[str] = None
    requirements: Optional[str] = None
    salary_range: Optional[str] = None


_SUBMIT_TOOL = {
    "toolSpec": {
        "name": "submit_jobs",
        "description": (
            "Submit the structured job postings you found. Call this exactly once "
            "when done (or when you've hit a dead end — submit an empty list)."
        ),
        "inputSchema": {
            "json": {
                "type": "object",
                "properties": {
                    "jobs": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "title": {"type": "string"},
                                "company": {"type": "string"},
                                "location": {"type": ["string", "null"]},
                                "job_type": {"type": ["string", "null"]},
                                "apply_url": {"type": ["string", "null"]},
                                "description": {"type": ["string", "null"]},
                                "requirements": {"type": ["string", "null"]},
                                "salary_range": {"type": ["string", "null"]},
                            },
                            "required": ["title", "company"],
                        },
                    }
                },
                "required": ["jobs"],
            }
        },
    }
}


class AgenticScraperActor(Actor):
    """AI-driven browser scraper for arbitrary job boards."""

    name = "agentic"
    version = "1.0.0"

    async def validate_input(self, config: Dict[str, Any]) -> bool:
        return bool(config.get("board_url") or config.get("query"))

    async def run(self, config: Dict[str, Any]) -> List[Dict[str, Any]]:
        board_url = config.get("board_url")
        query = config.get("query", "")
        location = config.get("location", "")
        max_results = int(config.get("max_results", 10))

        if not board_url:
            # No board given — fall back to a general search engine pass.
            board_url = "https://duckduckgo.com/"

        task = (
            f"Find up to {max_results} job postings"
            + (f" matching '{query}'" if query else "")
            + (f" near '{location}'" if location else "")
            + f". Start at {board_url}. "
            "Use browser_navigate first, then browser_snapshot to read pages. "
            "Open individual postings when needed to capture description, "
            "requirements, salary, and the direct apply URL. When finished, call "
            "submit_jobs with everything you found. Do not log in, do not fill "
            "any forms, and do not apply to anything."
        )

        async with MCPBrowser() as browser:  # type: ignore[misc]
            tools = browser.bedrock_tool_config() + [_SUBMIT_TOOL]
            return await self._agent_loop(task, tools, browser, max_results)

    async def _agent_loop(
        self,
        task: str,
        tools: list[dict[str, Any]],
        browser: MCPBrowser,
        max_results: int,
    ) -> List[Dict[str, Any]]:
        session = aioboto3.Session()
        messages: list[dict[str, Any]] = [
            {"role": "user", "content": [{"text": task}]}
        ]
        system = [
            {
                "text": (
                    "You are a careful web-scraping agent. You only read public job "
                    "boards. Be efficient: every browser action costs budget, and you "
                    f"have at most {MAX_TOOL_CALLS} tool calls."
                )
            }
        ]

        tool_calls = 0
        async with session.client(
            "bedrock-runtime", region_name=os.getenv("AWS_REGION", "us-east-1")
        ) as bedrock:
            while tool_calls < MAX_TOOL_CALLS:
                response = await bedrock.converse(
                    modelId=MODEL_ID,
                    system=system,
                    messages=messages,
                    toolConfig={"tools": tools},
                    inferenceConfig={"temperature": 0.1, "maxTokens": 4096},
                )
                message = response["output"]["message"]
                messages.append(message)

                if response.get("stopReason") != "tool_use":
                    logger.warning("Agent stopped without calling submit_jobs")
                    return []

                tool_results: list[dict[str, Any]] = []
                for block in message["content"]:
                    tool_use = block.get("toolUse")
                    if not tool_use:
                        continue

                    if tool_use["name"] == "submit_jobs":
                        return self._validate_jobs(
                            tool_use["input"].get("jobs", []), max_results
                        )

                    tool_calls += 1
                    if tool_calls >= MAX_TOOL_CALLS:
                        result_text = (
                            "Tool budget exhausted. Call submit_jobs now with "
                            "whatever you have collected."
                        )
                    else:
                        await asyncio.sleep(ACTION_DELAY_SECONDS)
                        try:
                            result_text = await browser.call_tool(
                                tool_use["name"], tool_use.get("input", {})
                            )
                        except Exception as e:
                            result_text = f"Tool error: {e}"

                    tool_results.append(
                        {
                            "toolResult": {
                                "toolUseId": tool_use["toolUseId"],
                                "content": [{"text": result_text}],
                            }
                        }
                    )

                if tool_results:
                    messages.append({"role": "user", "content": tool_results})

        logger.warning("Agent loop ended without submit_jobs")
        return []

    def _validate_jobs(
        self, raw_jobs: list[dict[str, Any]], max_results: int
    ) -> List[Dict[str, Any]]:
        validated: List[Dict[str, Any]] = []
        for raw in raw_jobs[:max_results]:
            try:
                validated.append(ScrapedJob(**raw).model_dump())
            except ValidationError as e:
                logger.warning(f"Dropping invalid scraped job: {e}")
        logger.info(f"Agentic scraper returning {len(validated)} validated jobs")
        return validated
