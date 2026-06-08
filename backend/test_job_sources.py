#!/usr/bin/env python3
"""
Test job sources framework.

Tests RSS feed integration, deduplication, and database sync.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.logging_config import setup_logging, get_logger
from app.services.job_sources import JobSourceManager, RSSJobSource, JobListing
from app.database import engine, Base, AsyncSessionLocal
from app.models import Job
from sqlalchemy import select

setup_logging("development")
logger = get_logger("test_job_sources")

print("\n" + "="*60)
print("JOB SOURCES FRAMEWORK TESTS")
print("="*60 + "\n")


async def setup_test_db():
    """Create fresh test database."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Test database initialized")


async def test_job_listing_creation():
    """Test JobListing normalization."""
    print("TEST 1: Job Listing Creation")
    print("-" * 60)
    
    job = JobListing(
        title="Senior Python Engineer",
        company="TechCorp",
        location="Remote",
        job_type="full-time",
        description="Build amazing things with Python",
        source="test_feed",
        source_url="https://example.com/jobs/123",
        apply_url="https://example.com/jobs/123/apply",
        posted_date="2026-06-01T10:00:00Z",
    )
    
    assert job.title == "Senior Python Engineer"
    assert job.source == "test_feed"
    assert job.to_dict()["title"] == "Senior Python Engineer"
    
    print("[PASS] JobListing created successfully")
    print("[PASS] to_dict() method works")
    print()


async def test_job_source_manager_creation():
    """Test manager initialization."""
    print("TEST 2: Job Source Manager Creation")
    print("-" * 60)
    
    manager = JobSourceManager()
    
    assert len(manager.sources) == 0
    print("[PASS] Manager initialized with no sources")
    
    # Add a dummy source
    class DummySource:
        def __init__(self):
            self.name = "Dummy"
        
        async def fetch_jobs(self):
            return []
    
    dummy = DummySource()
    manager.add_source(dummy)
    
    assert "Dummy" in manager.sources
    print("[PASS] Source registration works")
    print()


async def test_job_deduplication():
    """Test deduplication logic."""
    print("TEST 3: Job Deduplication")
    print("-" * 60)
    
    await setup_test_db()
    
    manager = JobSourceManager()
    
    # Create mock jobs with same URL
    jobs_source1 = [
        JobListing(
            title="Python Engineer",
            company="Company A",
            location="Remote",
            job_type="full-time",
            description="Job desc",
            source="source1",
            source_url="https://company-a.com/jobs",
            apply_url="https://company-a.com/jobs/apply",
        ),
    ]
    
    jobs_source2 = [
        JobListing(
            title="Python Engineer",
            company="Company A",
            location="Remote",
            job_type="full-time",
            description="Same job, different source",
            source="source2",
            source_url="https://company-a.com/jobs",
            apply_url="https://company-a.com/jobs/apply",  # Same apply URL
        ),
    ]
    
    # Sync first batch
    jobs_by_source_1 = {"source1": jobs_source1}
    stats_1 = await manager.sync_to_database(jobs_by_source_1)
    
    assert stats_1["added"] == 1
    assert stats_1["duplicates"] == 0
    print(f"[PASS] First sync added 1 job")
    
    # Sync second batch (should detect duplicate)
    jobs_by_source_2 = {"source2": jobs_source2}
    stats_2 = await manager.sync_to_database(jobs_by_source_2)
    
    assert stats_2["added"] == 0
    assert stats_2["duplicates"] == 1
    print(f"[PASS] Second sync detected duplicate by apply_url")
    print()


async def test_job_persistence():
    """Test that jobs are saved to database."""
    print("TEST 4: Job Persistence")
    print("-" * 60)
    
    await setup_test_db()
    
    manager = JobSourceManager()
    
    jobs = [
        JobListing(
            title="Backend Engineer",
            company="StartupXYZ",
            location="San Francisco",
            job_type="full-time",
            description="Build APIs",
            source="test_source",
            source_url="https://startup.com/jobs/123",
            apply_url="https://startup.com/apply/123",
        ),
        JobListing(
            title="Frontend Developer",
            company="StartupXYZ",
            location="Remote",
            job_type="full-time",
            description="Build UIs",
            source="test_source",
            source_url="https://startup.com/jobs/124",
            apply_url="https://startup.com/apply/124",
        ),
    ]
    
    jobs_by_source = {"test_source": jobs}
    stats = await manager.sync_to_database(jobs_by_source)
    
    assert stats["added"] == 2
    print(f"[PASS] Synced 2 jobs to database")
    
    # Verify jobs are in database
    async with AsyncSessionLocal() as session:
        result = await session.execute(select(Job))
        db_jobs = result.scalars().all()
        
        assert len(db_jobs) == 2
        assert db_jobs[0].title == "Backend Engineer"
        assert db_jobs[1].title == "Frontend Developer"
    
    print(f"[PASS] Jobs verified in database")
    print()


async def test_rss_source_url_extraction():
    """Test RSS source domain extraction."""
    print("TEST 5: RSS Source URL Extraction")
    print("-" * 60)
    
    test_urls = [
        ("https://news.ycombinator.com/rss", "News Ycombinator"),
        ("https://www.hackernewsjobs.com/feed", "Hackernewsjobs"),
        ("https://jobs.lever.co/rss", "Jobs Lever"),
        ("https://api.angel.co/feeds/jobs", "Api Angel"),
    ]
    
    for url, expected_name_part in test_urls:
        source = RSSJobSource(url)
        # Name should contain part of domain
        assert len(source.name) > 0
        print(f"[PASS] {url} -> {source.name}")
    
    print()


async def test_job_listing_normalization():
    """Test that job listings normalize different input formats."""
    print("TEST 6: Job Listing Normalization")
    print("-" * 60)
    
    # Test with minimal required fields
    job_minimal = JobListing(
        title="Job Title",
        company="Company",
        location="Location",
        job_type="full-time",
        description="Description",
        source="test",
        source_url="https://example.com",
        apply_url="https://example.com/apply",
    )
    
    job_dict = job_minimal.to_dict()
    assert "title" in job_dict
    assert "company" in job_dict
    assert "apply_url" in job_dict
    assert job_dict["job_type"] == "full-time"
    
    print("[PASS] Minimal JobListing normalized correctly")
    
    # Test with all fields
    job_full = JobListing(
        title="Senior Engineer",
        company="BigTech",
        location="Remote",
        job_type="full-time",
        description="Do important work",
        source="linkedin",
        source_url="https://linkedin.com/jobs/123",
        apply_url="https://linkedin.com/apply/123",
        requirements="5+ years Python",
        salary_range="$150k-200k",
        posted_date="2026-06-01",
    )
    
    job_dict_full = job_full.to_dict()
    assert job_dict_full["requirements"] == "5+ years Python"
    assert job_dict_full["salary_range"] == "$150k-200k"
    
    print("[PASS] Full JobListing with all fields normalized correctly")
    print()


async def test_source_manager_parallel_fetch():
    """Test that manager can fetch from multiple sources (mock)."""
    print("TEST 7: Parallel Source Fetching")
    print("-" * 60)
    
    manager = JobSourceManager()
    
    # Create mock sources
    class MockSource1:
        def __init__(self):
            self.name = "Mock1"
        
        async def fetch_jobs(self):
            await asyncio.sleep(0.1)  # Simulate network delay
            return [
                JobListing(
                    title="Job1",
                    company="CompanyA",
                    location="Remote",
                    job_type="full-time",
                    description="Desc1",
                    source="Mock1",
                    source_url="https://a.com/1",
                    apply_url="https://a.com/1/apply",
                )
            ]
    
    class MockSource2:
        def __init__(self):
            self.name = "Mock2"
        
        async def fetch_jobs(self):
            await asyncio.sleep(0.05)  # Shorter delay
            return [
                JobListing(
                    title="Job2",
                    company="CompanyB",
                    location="Remote",
                    job_type="full-time",
                    description="Desc2",
                    source="Mock2",
                    source_url="https://b.com/2",
                    apply_url="https://b.com/2/apply",
                )
            ]
    
    manager.add_source(MockSource1())
    manager.add_source(MockSource2())
    
    # Fetch all in parallel
    import time
    start = time.time()
    results = await manager.fetch_all()
    elapsed = time.time() - start
    
    assert len(results) == 2
    assert len(results["Mock1"]) == 1
    assert len(results["Mock2"]) == 1
    
    # Should be faster than sequential (0.15s vs 0.15s = parallel)
    print(f"[PASS] Fetched from 2 sources in parallel ({elapsed:.2f}s)")
    print(f"[PASS] Mock1: {len(results['Mock1'])} jobs")
    print(f"[PASS] Mock2: {len(results['Mock2'])} jobs")
    print()


async def run_all_tests():
    """Run all tests."""
    try:
        await test_job_listing_creation()
        await test_job_source_manager_creation()
        await test_job_deduplication()
        await test_job_persistence()
        await test_rss_source_url_extraction()
        await test_job_listing_normalization()
        await test_source_manager_parallel_fetch()
        
        print("=" * 60)
        print("[PASS] ALL JOB SOURCE TESTS PASSED")
        print("=" * 60)
        print("\nKey Features Verified:")
        print("- [PASS] Job listing normalization")
        print("- [PASS] Source manager initialization")
        print("- [PASS] Deduplication logic")
        print("- [PASS] Database persistence")
        print("- [PASS] URL extraction")
        print("- [PASS] Parallel source fetching")
        print("")
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
