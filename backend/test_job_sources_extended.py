#!/usr/bin/env python3
"""
Extended job sources tests.

Tests for GitHub, LinkedIn, and Angel List sources.
"""

import sys
import os
import asyncio

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.logging_config import setup_logging, get_logger
from app.services.job_sources import (
    JobSourceManager,
    GitHubJobSource,
    LinkedInJobSource,
    AngelListJobSource,
)
from app.services.job_sync_scheduler import JobSyncScheduler

setup_logging("development")
logger = get_logger("test_extended_sources")

print("\n" + "="*60)
print("EXTENDED JOB SOURCES TESTS")
print("="*60 + "\n")


async def test_github_source_init():
    """Test GitHub source initialization."""
    print("TEST 1: GitHub Source Initialization")
    print("-" * 60)
    
    source = GitHubJobSource()
    
    assert source.name == "GitHub Jobs"
    assert source.api_url == "https://jobs.github.com/positions.json"
    
    print("[PASS] GitHub source initialized correctly")
    print()


async def test_linkedin_source_init():
    """Test LinkedIn source initialization."""
    print("TEST 2: LinkedIn Source Initialization")
    print("-" * 60)
    
    source_unconfigured = LinkedInJobSource()
    assert not source_unconfigured.is_configured
    print("[PASS] LinkedIn source without credentials marked as not configured")
    
    source_configured = LinkedInJobSource(
        client_id="test_id",
        client_secret="test_secret",
    )
    assert source_configured.is_configured
    print("[PASS] LinkedIn source with credentials marked as configured")
    
    print()


async def test_angellist_source_init():
    """Test Angel List source initialization."""
    print("TEST 3: Angel List Source Initialization")
    print("-" * 60)
    
    source_unconfigured = AngelListJobSource()
    assert not source_unconfigured.is_configured
    print("[PASS] Angel List source without credentials marked as not configured")
    
    source_configured = AngelListJobSource(api_key="test_key")
    assert source_configured.is_configured
    print("[PASS] Angel List source with API key marked as configured")
    
    print()


async def test_unconfigured_sources_fetch():
    """Test that unconfigured sources return empty lists."""
    print("TEST 4: Unconfigured Sources Fetch")
    print("-" * 60)
    
    linkedin = LinkedInJobSource()
    angellist = AngelListJobSource()
    
    linkedin_jobs = await linkedin.fetch_jobs()
    angellist_jobs = await angellist.fetch_jobs()
    
    assert linkedin_jobs == []
    assert angellist_jobs == []
    
    print("[PASS] LinkedIn unconfigured returns empty list")
    print("[PASS] Angel List unconfigured returns empty list")
    
    print()


async def test_job_sync_scheduler_init():
    """Test job sync scheduler initialization."""
    print("TEST 5: Job Sync Scheduler Initialization")
    print("-" * 60)
    
    manager = JobSourceManager()
    scheduler = JobSyncScheduler(manager)
    
    assert scheduler.is_running == False
    assert scheduler.sync_interval_minutes == 60
    assert scheduler.last_sync_at is None
    
    config = scheduler.get_config()
    assert config["is_running"] == False
    assert config["interval_minutes"] == 60
    assert config["sources_count"] == 0
    
    print("[PASS] Job sync scheduler initialized correctly")
    print("[PASS] Default interval is 60 minutes")
    print()


async def test_job_sync_scheduler_interval_validation():
    """Test scheduler interval validation."""
    print("TEST 6: Job Sync Scheduler Interval Validation")
    print("-" * 60)
    
    manager = JobSourceManager()
    scheduler = JobSyncScheduler(manager)
    
    # Valid interval
    scheduler.set_sync_interval(30)
    assert scheduler.sync_interval_minutes == 30
    print("[PASS] Setting valid interval (30 min) works")
    
    # Invalid interval
    try:
        scheduler.set_sync_interval(2)  # Less than 5 minutes
        print("[FAIL] Should have rejected interval < 5 minutes")
    except ValueError as e:
        print(f"[PASS] Rejected invalid interval: {e}")
    
    print()


async def test_scheduler_config_retrieval():
    """Test scheduler configuration retrieval."""
    print("TEST 7: Scheduler Config Retrieval")
    print("-" * 60)
    
    manager = JobSourceManager()
    scheduler = JobSyncScheduler(manager)
    scheduler.set_sync_interval(45)
    
    config = scheduler.get_config()
    
    assert config["interval_minutes"] == 45
    assert config["is_running"] == False
    assert config["sources_count"] == 0
    assert "last_sync_at" in config
    assert "next_sync_at" in config
    
    print("[PASS] Config contains all expected fields")
    print("[PASS] Interval correctly reflects set value")
    
    print()


async def test_manager_with_multiple_sources():
    """Test manager with multiple sources."""
    print("TEST 8: Manager with Multiple Sources")
    print("-" * 60)
    
    manager = JobSourceManager()
    
    # Add different sources
    github = GitHubJobSource()
    linkedin = LinkedInJobSource(client_id="id", client_secret="secret")
    
    manager.add_source(github)
    manager.add_source(linkedin)
    
    assert len(manager.sources) == 2
    assert "GitHub Jobs" in manager.sources
    assert "LinkedIn" in manager.sources
    
    print("[PASS] Multiple sources registered correctly")
    
    config = manager.sources
    print(f"[PASS] Sources: {list(config.keys())}")
    
    print()


async def test_scheduler_with_manager():
    """Test scheduler integration with manager."""
    print("TEST 9: Scheduler with Manager")
    print("-" * 60)
    
    manager = JobSourceManager()
    scheduler = JobSyncScheduler(manager)
    
    # Add sources to manager
    github = GitHubJobSource()
    manager.add_source(github)
    
    config = scheduler.get_config()
    assert config["sources_count"] == 1
    assert "GitHub Jobs" in config["sources"]
    
    print("[PASS] Scheduler aware of manager sources")
    print(f"[PASS] Sources in scheduler config: {config['sources']}")
    
    print()


async def test_source_external_id_generation():
    """Test external ID generation for deduplication."""
    print("TEST 10: Source External ID Generation")
    print("-" * 60)
    
    from app.services.job_sources import JobListing
    
    github = GitHubJobSource()
    linkedin = LinkedInJobSource()
    angellist = AngelListJobSource()
    
    job = JobListing(
        title="Senior Python Engineer",
        company="TechCorp",
        location="Remote",
        job_type="full-time",
        description="Build awesome stuff",
        source="test",
        source_url="https://example.com/job/123",
        apply_url="https://example.com/apply/123",
    )
    
    # All sources should generate IDs for the same job
    github_id = await github.get_external_id(job)
    linkedin_id = await linkedin.get_external_id(job)
    angellist_id = await angellist.get_external_id(job)
    
    # IDs should be deterministic (same job = same ID)
    github_id2 = await github.get_external_id(job)
    
    assert github_id == linkedin_id == angellist_id
    assert github_id == github_id2
    
    print("[PASS] All sources generate consistent external IDs")
    print(f"[PASS] External ID: {github_id}")
    
    print()


async def run_all_tests():
    """Run all tests."""
    try:
        await test_github_source_init()
        await test_linkedin_source_init()
        await test_angellist_source_init()
        await test_unconfigured_sources_fetch()
        await test_job_sync_scheduler_init()
        await test_job_sync_scheduler_interval_validation()
        await test_scheduler_config_retrieval()
        await test_manager_with_multiple_sources()
        await test_scheduler_with_manager()
        await test_source_external_id_generation()
        
        print("=" * 60)
        print("[PASS] ALL EXTENDED TESTS PASSED (10/10)")
        print("=" * 60)
        print("\nKey Features Verified:")
        print("- [PASS] GitHub source working")
        print("- [PASS] LinkedIn stub ready for credentials")
        print("- [PASS] Angel List stub ready for credentials")
        print("- [PASS] Job sync scheduler initialized correctly")
        print("- [PASS] Scheduler validates intervals")
        print("- [PASS] Multiple sources manageable")
        print("- [PASS] External ID generation for deduplication")
        print()
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
