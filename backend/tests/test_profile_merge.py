"""
Tests for profile merging logic (profile_service.merge_extracted_profile).

These tests verify that extracted resume data is intelligently merged with
existing profile data, preserving manual entries while filling gaps.
"""

import pytest
from app.models import Profile
from app.services.profile_service import merge_extracted_profile


@pytest.mark.asyncio
async def test_merge_empty_profile_accepts_all():
    """When profile is empty, all extracted data should be accepted."""
    existing = Profile(id=1)

    extracted = {
        "full_name": "Jane Doe",
        "email": "jane@example.com",
        "phone": "+1 (555) 123-4567",
        "location": "San Francisco, CA",
        "summary": "Software engineer with 5 years experience",
        "skills": ["Python", "React", "AWS"],
        "experience": [{"company": "TechCorp", "title": "Senior Engineer", "start": "2020", "end": "Present"}],
        "education": [{"school": "Stanford", "degree": "B.S.", "field": "Computer Science"}],
    }

    merged, changes = await merge_extracted_profile(existing, extracted)

    # All fields should be updated
    assert merged.full_name == "Jane Doe"
    assert merged.email == "jane@example.com"
    assert merged.skills == ["Python", "React", "AWS"]
    assert len(merged.experience) == 1
    assert len(merged.education) == 1
    assert len(changes) == 8  # All 8 fields changed


@pytest.mark.asyncio
async def test_merge_preserves_manual_entries():
    """Manually entered fields should be preserved over extracted data."""
    existing = Profile(
        id=1,
        full_name="Jane Doe",  # Already filled (manual)
        email="jane@custom.com",  # Already filled (manual)
        location=None,
    )

    extracted = {
        "full_name": "Jane Smith",  # Should be ignored (existing is not empty)
        "email": "jane@work.com",  # Should be ignored (existing is not empty)
        "location": "San Francisco, CA",  # Should be filled (existing is empty)
        "skills": ["Python"],
    }

    merged, changes = await merge_extracted_profile(existing, extracted)

    # Manual entries preserved
    assert merged.full_name == "Jane Doe"
    assert merged.email == "jane@custom.com"
    # New data filled in
    assert merged.location == "San Francisco, CA"
    assert merged.skills == ["Python"]
    # Only 2 fields changed (location, skills)
    assert set(changes) == {"location", "skills"}


@pytest.mark.asyncio
async def test_merge_deduplicates_skills():
    """Duplicate skills should not be added."""
    existing = Profile(
        id=1,
        skills=["Python", "React", "AWS"],
    )

    extracted = {
        "skills": ["Python", "Node.js", "Docker"],  # Python is duplicate
    }

    merged, changes = await merge_extracted_profile(existing, extracted)

    # Only new skills added (Node.js, Docker), Python not duplicated
    assert set(merged.skills) == {"Python", "React", "AWS", "Node.js", "Docker"}
    assert "Python" not in [s for s in merged.skills[3:]]  # Not added twice


@pytest.mark.asyncio
async def test_merge_deduplicates_experience():
    """Duplicate jobs should not be added."""
    existing = Profile(
        id=1,
        experience=[
            {"company": "TechCorp", "title": "Senior Engineer", "start": "2020", "end": "Present"},
        ],
    )

    extracted = {
        "experience": [
            {"company": "TechCorp", "title": "Senior Engineer", "start": "2020", "end": "Present"},  # Duplicate
            {"company": "StartupXYZ", "title": "Lead Dev", "start": "2018", "end": "2020"},  # New
        ],
    }

    merged, changes = await merge_extracted_profile(existing, extracted)

    # Only new experience added, duplicate not included
    assert len(merged.experience) == 2
    assert merged.experience[0]["company"] == "TechCorp"
    assert merged.experience[1]["company"] == "StartupXYZ"
    assert changes == ["experience"]


@pytest.mark.asyncio
async def test_merge_empty_extracted_no_changes():
    """Empty extracted data should result in no changes."""
    existing = Profile(
        id=1,
        full_name="Jane Doe",
        email="jane@example.com",
    )

    extracted = {}

    merged, changes = await merge_extracted_profile(existing, extracted)

    # Nothing should change
    assert merged.full_name == "Jane Doe"
    assert merged.email == "jane@example.com"
    assert len(changes) == 0


@pytest.mark.asyncio
async def test_merge_partial_extracted():
    """Only non-empty extracted fields should be considered."""
    existing = Profile(
        id=1,
        full_name="Jane Doe",
        location=None,
    )

    extracted = {
        "full_name": None,  # Explicitly None
        "location": "San Francisco",  # New value
        "skills": ["Python"],
    }

    merged, changes = await merge_extracted_profile(existing, extracted)

    # Name preserved (existing + extracted is None)
    assert merged.full_name == "Jane Doe"
    # Location filled (existing is None + extracted has value)
    assert merged.location == "San Francisco"
    # Skills added
    assert merged.skills == ["Python"]
    assert set(changes) == {"location", "skills"}


@pytest.mark.asyncio
async def test_merge_deduplicates_education():
    """Duplicate education entries should not be added."""
    existing = Profile(
        id=1,
        education=[
            {"school": "Stanford", "degree": "B.S.", "field": "Computer Science"},
        ],
    )

    extracted = {
        "education": [
            {"school": "Stanford", "degree": "B.S.", "field": "Computer Science"},  # Duplicate
            {"school": "MIT", "degree": "M.S.", "field": "AI"},  # New
        ],
    }

    merged, changes = await merge_extracted_profile(existing, extracted)

    # Only new education added, duplicate not included
    assert len(merged.education) == 2
    assert merged.education[0]["school"] == "Stanford"
    assert merged.education[1]["school"] == "MIT"


@pytest.mark.asyncio
async def test_merge_case_insensitive_dedup():
    """Deduplication should be case-insensitive for companies/schools."""
    existing = Profile(
        id=1,
        skills=["python", "React"],
    )

    extracted = {
        "skills": ["PYTHON", "Node.js"],  # PYTHON should match python
    }

    merged, changes = await merge_extracted_profile(existing, extracted)

    # Only one "python" (case-insensitive), plus React and Node.js
    assert merged.skills == ["python", "React", "Node.js"]
    assert len(merged.skills) == 3


@pytest.mark.asyncio
async def test_merge_preserves_order():
    """Existing items should come before new extracted items."""
    existing = Profile(
        id=1,
        skills=["Python", "React"],
    )

    extracted = {
        "skills": ["AWS", "Docker"],
    }

    merged, changes = await merge_extracted_profile(existing, extracted)

    # Existing order preserved, new items appended
    assert merged.skills == ["Python", "React", "AWS", "Docker"]
