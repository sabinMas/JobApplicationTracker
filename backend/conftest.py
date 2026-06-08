"""
Pytest configuration for async tests with PostgreSQL.

Handles event loop lifecycle to avoid 'Event loop is closed' errors
when running tests that connect to the database.
"""

import pytest
import asyncio


@pytest.fixture(scope="session")
def event_loop():
    """Create a single event loop for the entire test session."""
    policy = asyncio.WindowsProactorEventLoopPolicy()
    loop = policy.new_event_loop()
    yield loop
    loop.close()
