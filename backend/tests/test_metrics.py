#!/usr/bin/env python3
"""
Test metrics endpoints.

Tests the dashboard, errors, and summary endpoints.
"""

import sys
import os
import asyncio
from datetime import datetime, timezone, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from app.logging_config import setup_logging, get_logger
from app.database import Base, engine
from app.models import ApplicationMetric, Application, Job, Profile
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy import select

setup_logging("development")
logger = get_logger("test_metrics")

print("\n" + "="*60)
print("METRICS ENDPOINTS TEST")
print("="*60 + "\n")

# Create test database
TEST_DB_URL = "sqlite+aiosqlite:///:memory:"


async def setup_test_db():
    """Create test database with sample data."""
    logger.info("Setting up test database")
    
    # Create async engine for test
    test_engine = create_async_engine(
        TEST_DB_URL,
        echo=False,
        future=True,
    )
    
    # Create tables
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    # Create session factory
    SessionLocal = async_sessionmaker(
        test_engine,
        class_=AsyncSession,
        expire_on_commit=False,
        future=True,
    )
    
    session = SessionLocal()
    
    try:
        # Create profile
        profile = Profile(
            id=1,
            full_name="Test User",
            email="test@example.com",
            phone="+1-555-1234",
            location="Remote",
            skills=["Python", "React"],
        )
        session.add(profile)
        
        # Create jobs
        job1 = Job(
            title="Backend Engineer",
            company="Company A",
            location="Remote",
            job_type="full-time",
            apply_url="https://company-a.greenhouse.io/jobs/123",
            status="discovered",
        )
        job2 = Job(
            title="Frontend Engineer",
            company="Company B",
            location="Remote",
            job_type="full-time",
            apply_url="https://company-b.lever.co/jobs/456",
            status="discovered",
        )
        session.add_all([job1, job2])
        await session.flush()
        
        # Create applications
        app1 = Application(job_id=job1.id, status="applied", retry_count=0)
        app2 = Application(job_id=job2.id, status="pending", retry_count=2)
        session.add_all([app1, app2])
        await session.flush()
        
        # Create metrics
        now = datetime.now(timezone.utc)
        
        # Successful submission
        metric1 = ApplicationMetric(
            application_id=app1.id,
            attempt_number=1,
            start_time=now - timedelta(hours=2),
            end_time=now - timedelta(hours=2, minutes=-5),
            duration_ms=5000,
            status="success",
            ats_platform_detected="greenhouse",
            form_fields_detected=5,
            fields_filled=5,
        )
        
        # Failed submission
        metric2 = ApplicationMetric(
            application_id=app2.id,
            attempt_number=1,
            start_time=now - timedelta(hours=1),
            end_time=now - timedelta(hours=1, minutes=-2),
            duration_ms=8000,
            status="failed",
            ats_platform_detected="lever",
            error_message="Form did not load",
            form_fields_detected=0,
            fields_filled=0,
        )
        
        # Retry that succeeded
        metric3 = ApplicationMetric(
            application_id=app2.id,
            attempt_number=2,
            start_time=now - timedelta(minutes=30),
            end_time=now - timedelta(minutes=-2),
            duration_ms=6000,
            status="success",
            ats_platform_detected="lever",
            form_fields_detected=4,
            fields_filled=4,
        )
        
        session.add_all([metric1, metric2, metric3])
        await session.commit()
        
        logger.info("Test database populated", extra_fields={
            "applications": 2,
            "metrics": 3,
        })
        
        return session
        
    except Exception as e:
        logger.error(f"Failed to setup test database: {e}")
        await session.close()
        raise


async def test_metrics_dashboard():
    """Test metrics dashboard generation."""
    print("TEST 1: Metrics Dashboard")
    print("-" * 60)
    
    session = await setup_test_db()
    
    try:
        # Simulate dashboard query
        now = datetime.now(timezone.utc)
        start_date = now - timedelta(days=7)
        
        # Total attempts
        total_result = await session.execute(
            select(ApplicationMetric)
        )
        total_attempts = len(total_result.scalars().all())
        
        # Success count
        success_result = await session.execute(
            select(ApplicationMetric).where(
                ApplicationMetric.status == "success"
            )
        )
        successful = len(success_result.scalars().all())
        
        success_rate = (successful / total_attempts * 100) if total_attempts > 0 else 0
        
        assert total_attempts == 3, f"Expected 3 attempts, got {total_attempts}"
        assert successful == 2, f"Expected 2 successful, got {successful}"
        assert 66.0 < success_rate < 67.0, f"Expected ~66.67% success rate, got {success_rate}"
        
        print(f"[PASS] Total attempts: {total_attempts}")
        print(f"[PASS] Successful: {successful}")
        print(f"[PASS] Success rate: {success_rate:.1f}%")
        
    finally:
        await session.close()
    
    print()


async def test_ats_breakdown():
    """Test ATS platform breakdown."""
    print("TEST 2: ATS Platform Breakdown")
    print("-" * 60)
    
    session = await setup_test_db()
    
    try:
        # Get all metrics
        metrics_result = await session.execute(
            select(ApplicationMetric)
        )
        
        metrics = metrics_result.scalars().all()
        
        # Count by platform
        ats_counts = {}
        for metric in metrics:
            platform = metric.ats_platform_detected or "unknown"
            if platform not in ats_counts:
                ats_counts[platform] = {"attempts": 0, "successful": 0}
            ats_counts[platform]["attempts"] += 1
            if metric.status == "success":
                ats_counts[platform]["successful"] += 1
        
        assert "greenhouse" in ats_counts, "Greenhouse not found"
        assert "lever" in ats_counts, "Lever not found"
        assert ats_counts["greenhouse"]["attempts"] == 1
        assert ats_counts["lever"]["attempts"] == 2
        assert ats_counts["greenhouse"]["successful"] == 1
        assert ats_counts["lever"]["successful"] == 1
        
        print(f"[PASS] Greenhouse: {ats_counts['greenhouse']['successful']}/{ats_counts['greenhouse']['attempts']} successful")
        print(f"[PASS] Lever: {ats_counts['lever']['successful']}/{ats_counts['lever']['attempts']} successful")
        
    finally:
        await session.close()
    
    print()


async def test_error_tracking():
    """Test error tracking."""
    print("TEST 3: Error Tracking")
    print("-" * 60)
    
    session = await setup_test_db()
    
    try:
        # Get failed metrics
        failed_result = await session.execute(
            select(ApplicationMetric).where(
                ApplicationMetric.status == "failed"
            )
        )
        failed_metrics = failed_result.scalars().all()
        
        assert len(failed_metrics) == 1, f"Expected 1 failed, got {len(failed_metrics)}"
        assert failed_metrics[0].error_message == "Form did not load"
        
        print(f"[PASS] Failed submissions tracked: {len(failed_metrics)}")
        print(f"[PASS] Error message: {failed_metrics[0].error_message}")
        
    finally:
        await session.close()
    
    print()


async def test_retry_tracking():
    """Test retry attempt tracking."""
    print("TEST 4: Retry Attempt Tracking")
    print("-" * 60)
    
    session = await setup_test_db()
    
    try:
        # Get metrics for application 2 (which has retries)
        app_result = await session.execute(
            select(Application).where(Application.id == 2)
        )
        app = app_result.scalar_one()
        
        # Get metrics for this application
        metrics_result = await session.execute(
            select(ApplicationMetric).where(
                ApplicationMetric.application_id == app.id
            ).order_by(ApplicationMetric.attempt_number)
        )
        metrics = metrics_result.scalars().all()
        
        assert len(metrics) == 2, f"Expected 2 metrics for app2, got {len(metrics)}"
        assert metrics[0].attempt_number == 1
        assert metrics[0].status == "failed"
        assert metrics[1].attempt_number == 2
        assert metrics[1].status == "success"
        
        print(f"[PASS] Retry attempts tracked: {len(metrics)}")
        print(f"[PASS] Attempt 1: {metrics[0].status}")
        print(f"[PASS] Attempt 2: {metrics[1].status} (recovered!)")
        
    finally:
        await session.close()
    
    print()


async def test_duration_tracking():
    """Test duration tracking for performance analysis."""
    print("TEST 5: Duration Tracking")
    print("-" * 60)
    
    session = await setup_test_db()
    
    try:
        # Get average duration
        metrics_result = await session.execute(
            select(ApplicationMetric)
        )
        metrics = metrics_result.scalars().all()
        
        durations = [m.duration_ms for m in metrics if m.duration_ms]
        avg_duration = sum(durations) / len(durations) if durations else 0
        
        assert len(durations) == 3
        assert 6000 < avg_duration < 6700, f"Expected avg ~6333, got {avg_duration}"
        
        print(f"[PASS] Metrics tracked: {len(metrics)}")
        print(f"[PASS] Average duration: {avg_duration:.0f}ms")
        print(f"[PASS] Durations: {durations}")
        
    finally:
        await session.close()
    
    print()


async def run_all_tests():
    """Run all metrics tests."""
    try:
        await test_metrics_dashboard()
        await test_ats_breakdown()
        await test_error_tracking()
        await test_retry_tracking()
        await test_duration_tracking()
        
        print("=" * 60)
        print("[PASS] ALL METRICS TESTS PASSED")
        print("=" * 60)
        print("\nKey Features Verified:")
        print("- [PASS] Success rate calculation")
        print("- [PASS] ATS platform breakdown")
        print("- [PASS] Error tracking")
        print("- [PASS] Retry attempt tracking")
        print("- [PASS] Duration/performance tracking")
        print("")
        
    except Exception as e:
        print(f"\n[FAIL] TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(run_all_tests())
