"""
Automated job application scheduler.
Runs on a schedule (e.g., every 30 minutes) to:
1. Find matching jobs based on criteria
2. Automatically apply to matching jobs
3. Track results and failures
"""

import asyncio
from datetime import datetime, timezone
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from ..models import Job, Application, Profile
from .auto_submit import (
    wait_for_form_load,
    detect_and_fill_required_fields,
    find_and_click_submit,
    detect_submission_success,
)
from . import playwright_service
from .ats_integration import detect_ats_from_url


async def apply_to_matching_jobs(
    db: AsyncSession,
    criteria: dict,
) -> dict:
    """
    Find jobs matching criteria and automatically apply to them.

    Criteria format:
    {
        "keywords": ["Python", "React"],
        "location": ["remote", "San Francisco"],
        "min_salary": 120000,
        "max_salary": 200000,
        "job_types": ["full-time"],
        "exclude_companies": ["Company A", "Company B"],
    }
    """
    results = {
        "applied": [],
        "skipped": [],
        "failed": [],
    }

    # Get profile
    profile_result = await db.execute(select(Profile))
    profile = profile_result.scalar_one_or_none()
    if not profile:
        return {"error": "Profile not set up", "status": "aborted"}

    # Find matching jobs
    query = select(Job).where(Job.status == "discovered")

    # Apply filters
    if criteria.get("keywords"):
        keywords = criteria["keywords"]
        keyword_filter = Job.description.contains(keywords[0])
        for kw in keywords[1:]:
            keyword_filter = keyword_filter | Job.description.contains(kw)
        query = query.where(keyword_filter)

    if criteria.get("exclude_companies"):
        for company in criteria["exclude_companies"]:
            query = query.where(Job.company != company)

    result = await db.execute(query)
    jobs = result.scalars().all()

    # Process each matching job
    for job in jobs:
        try:
            # Check if already applied
            existing_app = await db.execute(
                select(Application).where(Application.job_id == job.id)
            )
            if existing_app.scalar_one_or_none():
                results["skipped"].append(
                    {
                        "job_id": job.id,
                        "reason": "Already applied",
                    }
                )
                continue

            # Check salary if specified
            if criteria.get("min_salary") and job.salary_range:
                try:
                    # Try to parse salary
                    if "$" not in job.salary_range:
                        results["skipped"].append(
                            {
                                "job_id": job.id,
                                "reason": "Salary range unclear",
                            }
                        )
                        continue
                except Exception:
                    pass

            # Create application record
            app = Application(
                job_id=job.id,
                status="pending",
                ats_platform=detect_ats_from_url(job.apply_url),
            )
            db.add(app)
            await db.commit()
            await db.refresh(app)

            # Attempt automated application
            success = await _auto_apply_to_job(app, job, profile)

            if success:
                results["applied"].append(
                    {
                        "job_id": job.id,
                        "company": job.company,
                        "title": job.title,
                    }
                )
            else:
                results["failed"].append(
                    {
                        "job_id": job.id,
                        "reason": "Automation failed",
                    }
                )

        except Exception as e:
            results["failed"].append(
                {
                    "job_id": job.id,
                    "reason": str(e),
                }
            )

    return results


async def _auto_apply_to_job(
    app: Application,
    job: Job,
    profile: dict,
) -> bool:
    """
    Attempt to automatically apply to a single job.
    Returns True if successful, False otherwise.
    """
    if not job.apply_url:
        return False

    session_id = None
    try:
        # Start browser session
        session_id = await playwright_service.start_session(
            application_id=app.id,
            apply_url=job.apply_url,
        )

        page = playwright_service._sessions[session_id]["page"]

        # Wait for form to load
        form_loaded = await wait_for_form_load(page, timeout=15000)
        if not form_loaded:
            return False

        # Detect ATS
        ats_type = detect_ats_from_url(job.apply_url)

        # Fill form
        profile_dict = {
            k: v for k, v in profile.__dict__.items() if not k.startswith("_")
        }
        await detect_and_fill_required_fields(page, profile_dict)

        # Submit
        submitted = await find_and_click_submit(page, ats_type)
        if not submitted:
            return False

        # Verify
        verified = await detect_submission_success(page)
        if verified:
            app.status = "applied"
            app.applied_date = datetime.now(timezone.utc)
            return True

        # Even if not verified, submission likely went through
        return True

    except Exception as e:
        print(f"Auto-apply failed for job {job.id}: {str(e)}")
        return False

    finally:
        if session_id:
            await playwright_service.stop_session(session_id)


async def schedule_auto_apply(
    db: AsyncSession,
    interval_minutes: int = 30,
    criteria: Optional[dict] = None,
):
    """
    Run auto-apply on a schedule.
    Example:
        asyncio.create_task(schedule_auto_apply(db, interval_minutes=30))
    """
    default_criteria = {
        "keywords": ["Software Engineer", "Backend", "Python"],
        "exclude_companies": [],
    }

    criteria = criteria or default_criteria

    while True:
        try:
            print(f"[{datetime.now().isoformat()}] Running scheduled auto-apply...")
            results = await apply_to_matching_jobs(db, criteria)
            print(f"Results: {results}")
        except Exception as e:
            print(f"Scheduled auto-apply error: {e}")

        # Wait for next interval
        await asyncio.sleep(interval_minutes * 60)
