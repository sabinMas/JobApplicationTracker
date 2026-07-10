#!/usr/bin/env python3
"""
Integration tests for job sync scheduler with job sources.

Tests full workflow: add sources -> sync -> verify database.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.logging_config import setup_logging, get_logger
from app.services.job_sources import JobSourceManager, GitHubJobSource
from app.services.job_sync_scheduler import JobSyncScheduler
from app.database import engine, Base, AsyncSessionLocal
from app.models import Job
from sqlalchemy import select

setup_logging("development")
logger = get_logger("test_integration")

print("\n" + "="*60)
print("JOB SYNC SCHEDULER INTEGRATION TESTS")
print("="*60 + "\n")


async def setup_test_db():
    """Create fresh test database."""
    async with engine.begin() as conn:
        # Drop with CASCADE to handle foreign key constraints
        if "postgres" in str(engine.url) or "postgresql" in str(engine.url):
            from sqlalchemy import text
            await conn.execute(text("DROP SCHEMA public CASCADE"))
            await conn.execute(text("CREATE SCHEMA public"))
        else:
            await conn.run_sync(Base.metadata.drop_all)

        await conn.run_sync(Base.metadata.create_all)
    logger.info("Test database initialized")


async def test_scheduler_with_github_source():
    """Test scheduler syncing with GitHub source."""
    print("TEST 1: Scheduler with GitHub Source")
    print("-" * 60)
    
    await setup_test_db()
    
    manager = JobSourceManager()
    scheduler = JobSyncScheduler(manager)
    
    # Add GitHub source
    github = GitHubJobSource()
    manager.add_source(github)
    
    config = scheduler.get_config()
    assert len(config["sources"]) == 1
    print("[PASS] GitHub source registered with scheduler")
    
    # Note: Don't actually sync from GitHub API in test (requires network)
    # Just verify the scheduler config
    assert config["is_running"] == False
    assert config["interval_minutes"] == 60
    
    print("[PASS] Scheduler config is correct")
    print()


async def test_scheduler_sync_with_mock_manager():
    """Test scheduler with mock job manager."""
    print("TEST 2: Scheduler Sync with Mock Manager")
    print("-" * 60)
    
    await setup_test_db()
    
    # Create mock manager with mock jobs
    class MockJobSource:
        def __init__(self):
            self.name = "MockSource"
        
        async def fetch_jobs(self):
            from app.services.job_sources import JobListing
            return [
                JobListing(
                    title="Senior Python Engineer",
                    company="TechCorp",
                    location="Remote",
                    job_type="full-time",
                    description="Build awesome stuff",
                    source="MockSource",
                    source_url="https://example.com/job/1",
                    apply_url="https://example.com/apply/1",
                ),
                JobListing(
                    title="Frontend Developer",
                    company="StartupXYZ",
                    location="San Francisco",
                    job_type="full-time",
                    description="Build UIs",
                    source="MockSource",
                    source_url="https://example.com/job/2",
                    apply_url="https://example.com/apply/2",
                ),
            ]
    
    manager = JobSourceManager()
    manager.add_source(MockJobSource())
    
    scheduler = JobSyncScheduler(manager)
    
    # Trigger sync
    result = await scheduler.sync_now()
    
    assert result["status"] == "success"
    assert result["stats"]["added"] == 2
    assert result["stats"]["duplicates"] == 0
    
    print("[PASS] Mock sync added 2 jobs")
    print(f"[PASS] Sync took {result['duration_ms']}ms")
    
    # Verify last_sync_at was updated
    assert scheduler.last_sync_at is not None
    assert scheduler.next_sync_at is not None
    
    print("[PASS] Scheduler timestamps updated")
    
    # Verify jobs in database
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job))
        jobs = result.scalars().all()
        assert len(jobs) == 2
    
    print("[PASS] Jobs saved to database")
    print()


async def test_scheduler_duplicate_handling():
    """Test scheduler handles duplicates correctly."""
    print("TEST 3: Scheduler Duplicate Handling")
    print("-" * 60)
    
    await setup_test_db()
    
    class DuplicateJobSource:
        def __init__(self, run_number=1):
            self.name = "DuplicateSource"
            self.run_number = run_number
        
        async def fetch_jobs(self):
            from app.services.job_sources import JobListing
            
            jobs = [
                JobListing(
                    title="Senior Python Engineer",
                    company="TechCorp",
                    location="Remote",
                    job_type="full-time",
                    description="Build awesome stuff",
                    source="DuplicateSource",
                    source_url="https://example.com/job/1",
                    apply_url="https://example.com/apply/1",
                ),
            ]
            
            # On second run, add another job with same URL (duplicate)
            if self.run_number == 2:
                jobs.append(JobListing(
                    # Title must pass the relevance pre-filter so this job
                    # reaches the duplicate check (what this test verifies)
                    title="Senior Python Engineer (Repost)",
                    company="TechCorp",
                    location="Remote",
                    job_type="full-time",
                    description="Different description",
                    source="DuplicateSource",
                    source_url="https://example.com/job/1",  # Same URL = duplicate
                    apply_url="https://example.com/apply/1",
                ))
            
            return jobs
    
    manager = JobSourceManager()
    source = DuplicateJobSource(run_number=1)
    manager.add_source(source)
    
    scheduler = JobSyncScheduler(manager)
    
    # First sync
    result1 = await scheduler.sync_now()
    assert result1["stats"]["added"] == 1
    print("[PASS] First sync added 1 job")
    
    # Second sync with duplicate
    source.run_number = 2
    result2 = await scheduler.sync_now()
    assert result2["stats"]["added"] == 0  # No new jobs (both are duplicates now)
    assert result2["stats"]["duplicates"] == 2  # 2 duplicates detected (one existing + one duplicate within batch)
    print("[PASS] Second sync detected 2 duplicates")
    
    # Verify total jobs in database
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job))
        jobs = result.scalars().all()
        assert len(jobs) == 1  # Should have 1 total (all are duplicates after 2nd sync)
    
    print("[PASS] Total jobs in database: 1 (duplicates filtered)")
    print()


async def test_scheduler_interval_configuration():
    """Test scheduler interval configuration."""
    print("TEST 4: Scheduler Interval Configuration")
    print("-" * 60)
    
    manager = JobSourceManager()
    scheduler = JobSyncScheduler(manager)
    
    # Default interval
    assert scheduler.sync_interval_minutes == 60
    print("[PASS] Default interval is 60 minutes")
    
    # Update interval
    scheduler.set_sync_interval(30)
    assert scheduler.sync_interval_minutes == 30
    print("[PASS] Updated interval to 30 minutes")
    
    # Validate minimum interval
    try:
        scheduler.set_sync_interval(2)
        print("[FAIL] Should reject interval < 5 minutes")
    except ValueError:
        print("[PASS] Rejected invalid interval (< 5 minutes)")
    
    # Valid boundary
    scheduler.set_sync_interval(5)
    assert scheduler.sync_interval_minutes == 5
    print("[PASS] Accepted minimum valid interval (5 minutes)")
    
    print()


async def test_scheduler_config_export():
    """Test scheduler config export for API."""
    print("TEST 5: Scheduler Config Export")
    print("-" * 60)
    
    from app.services.job_sources import RSSJobSource
    
    manager = JobSourceManager()
    manager.add_source(RSSJobSource("https://example.com/jobs.rss"))
    manager.add_source(GitHubJobSource())
    
    scheduler = JobSyncScheduler(manager)
    scheduler.set_sync_interval(45)
    
    config = scheduler.get_config()
    
    # Verify config structure
    assert "is_running" in config
    assert "interval_minutes" in config
    assert "last_sync_at" in config
    assert "next_sync_at" in config
    assert "sources_count" in config
    assert "sources" in config
    
    # Verify values
    assert config["is_running"] == False
    assert config["interval_minutes"] == 45
    assert config["sources_count"] == 2
    assert len(config["sources"]) == 2
    
    print("[PASS] Config has all required fields")
    print(f"[PASS] Sources: {config['sources']}")
    
    print()


async def run_all_tests():
    """Run all integration tests."""
    try:
        await test_scheduler_with_github_source()
        await test_scheduler_sync_with_mock_manager()
        await test_scheduler_duplicate_handling()
        await test_scheduler_interval_configuration()
        await test_scheduler_config_export()
        
        print("=" * 60)
        print("[PASS] ALL INTEGRATION TESTS PASSED (5/5)")
        print("=" * 60)
        print("\nKey Features Verified:")
        print("- [PASS] Scheduler works with GitHub source")
        print("- [PASS] Mock sync correctly adds jobs to database")
        print("- [PASS] Duplicate detection and filtering works")
        print("- [PASS] Interval configuration and validation")
        print("- [PASS] Config export for API endpoints")
        print()
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
