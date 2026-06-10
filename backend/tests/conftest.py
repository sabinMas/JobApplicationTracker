"""
Pytest configuration.

Forces tests onto a local SQLite database (never the production RDS instance)
and provides a session-scoped event loop for async tests on Windows.
"""

import asyncio
import os
import sys
import tempfile

import pytest

# Must be set before any `app.*` module is imported, since app.database
# creates the engine at import time from this variable.
_TEST_DB = os.path.join(tempfile.gettempdir(), "jobtracker_test.db")
os.environ["DATABASE_URL"] = f"sqlite+aiosqlite:///{_TEST_DB}"
os.environ.setdefault("ENVIRONMENT", "test")


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    if sys.platform == "win32":
        policy = asyncio.WindowsProactorEventLoopPolicy()
    else:
        policy = asyncio.get_event_loop_policy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
