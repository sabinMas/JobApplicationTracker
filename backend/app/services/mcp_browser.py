"""
MCP browser client.

Launches Microsoft's Playwright MCP server (@playwright/mcp) as a stdio
subprocess and exposes its browser tools (navigate, snapshot, click, type, …)
to in-process AI agents. Used by the agentic scraper actor so an AI agent can
drive a real browser on job boards we have no dedicated scraper for.

Requires Node.js in the runtime image (added to Dockerfile.worker).
"""

import logging
import os
from typing import Any

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)

# Tools the scraping agent is allowed to use. Anything else the server offers
# (file upload, PDF save, tab management…) stays off-limits.
ALLOWED_TOOLS = {
    "browser_navigate",
    "browser_snapshot",
    "browser_click",
    "browser_type",
    "browser_press_key",
    "browser_wait_for",
}

# Accessibility snapshots of busy job boards can be enormous; cap what we
# feed back into the model per tool call.
MAX_TOOL_RESULT_CHARS = 20_000


class MCPBrowser:
    """Async context manager around a Playwright MCP stdio session."""

    def __init__(self) -> None:
        self._stdio_ctx = None
        self._session_ctx = None
        self.session: ClientSession | None = None
        self._tools: list[dict[str, Any]] = []

    async def __aenter__(self) -> "MCPBrowser":
        npx = "npx.cmd" if os.name == "nt" else "npx"
        params = StdioServerParameters(
            command=npx,
            args=["-y", "@playwright/mcp@latest", "--headless", "--isolated"],
        )
        self._stdio_ctx = stdio_client(params)
        read, write = await self._stdio_ctx.__aenter__()
        self._session_ctx = ClientSession(read, write)
        self.session = await self._session_ctx.__aenter__()
        await self.session.initialize()

        listing = await self.session.list_tools()
        self._tools = [
            {
                "name": t.name,
                "description": t.description or "",
                "input_schema": t.inputSchema,
            }
            for t in listing.tools
            if t.name in ALLOWED_TOOLS
        ]
        logger.info(f"MCP browser ready with tools: {[t['name'] for t in self._tools]}")
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:
        if self._session_ctx is not None:
            await self._session_ctx.__aexit__(exc_type, exc, tb)
        if self._stdio_ctx is not None:
            await self._stdio_ctx.__aexit__(exc_type, exc, tb)

    def bedrock_tool_config(self) -> list[dict[str, Any]]:
        """The allowed MCP tools in Bedrock Converse toolSpec format."""
        return [
            {
                "toolSpec": {
                    "name": t["name"],
                    "description": t["description"][:500],
                    "inputSchema": {"json": t["input_schema"]},
                }
            }
            for t in self._tools
        ]

    async def call_tool(self, name: str, arguments: dict[str, Any]) -> str:
        """Invoke an MCP tool and return its text content (truncated)."""
        if name not in ALLOWED_TOOLS:
            return f"Error: tool '{name}' is not allowed."
        result = await self.session.call_tool(name, arguments)
        parts = [c.text for c in result.content if getattr(c, "text", None)]
        text = "\n".join(parts)
        if len(text) > MAX_TOOL_RESULT_CHARS:
            text = text[:MAX_TOOL_RESULT_CHARS] + "\n…[truncated]"
        return text or "(no output)"
