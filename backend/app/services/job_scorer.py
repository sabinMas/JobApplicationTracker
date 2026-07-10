"""
Job Scoring Service — scores how well a job fits *this* candidate.

Loads the Profile and SearchPreferences from the database itself so callers
can't forget to pass them. Applies a free keyword pre-filter before spending
AI tokens, then asks the AI for a structured 1-10 fit score.
"""

import logging
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models import Job, Profile, SearchPreferences
from . import ai_service

logger = logging.getLogger(__name__)

_SCORE_SCHEMA = {
    "type": "object",
    "properties": {
        "score": {"type": "number", "minimum": 1, "maximum": 10},
        "reasoning": {"type": "string", "description": "2-3 sentence explanation"},
        "strengths": {"type": "array", "items": {"type": "string"}},
        "concerns": {"type": "array", "items": {"type": "string"}},
        "recommendation": {"type": "string", "enum": ["SUBMIT", "SKIP"]},
    },
    "required": ["score", "reasoning", "strengths", "concerns", "recommendation"],
}


async def load_candidate_context(
    db: AsyncSession,
) -> tuple[Optional[Profile], Optional[SearchPreferences]]:
    """Load the (single-row) Profile and SearchPreferences."""
    profile = (await db.execute(select(Profile))).scalar_one_or_none()
    prefs = (await db.execute(select(SearchPreferences))).scalar_one_or_none()
    return profile, prefs


def prefilter_job(
    job: Job, prefs: Optional[SearchPreferences]
) -> Optional[dict[str, Any]]:
    """Cheap keyword screen before any AI call.

    Returns a complete score-result dict (score=1, SKIP) when the job is a
    hard reject, or None when it should proceed to AI scoring.
    """
    if prefs is None:
        return None

    text = " ".join(
        filter(None, [job.title, job.description, job.requirements, job.location])
    ).lower()

    for kw in prefs.avoid_keywords or []:
        if kw.lower() in text:
            return {
                "score": 1,
                "reasoning": f"Rejected by pre-filter: contains avoid keyword '{kw}'.",
                "strengths": [],
                "concerns": [f"avoid keyword: {kw}"],
                "recommendation": "SKIP",
                "prefiltered": True,
            }

    if prefs.job_types and job.job_type and job.job_type not in prefs.job_types:
        return {
            "score": 2,
            "reasoning": f"Rejected by pre-filter: job type '{job.job_type}' not in preferences.",
            "strengths": [],
            "concerns": [f"job type: {job.job_type}"],
            "recommendation": "SKIP",
            "prefiltered": True,
        }

    must_have = prefs.must_have_keywords or []
    if must_have and not any(kw.lower() in text for kw in must_have):
        return {
            "score": 2,
            "reasoning": "Rejected by pre-filter: mentions none of the must-have keywords.",
            "strengths": [],
            "concerns": ["no must-have keyword match"],
            "recommendation": "SKIP",
            "prefiltered": True,
        }

    return None


def _build_prompt(
    job: Job, profile: Optional[Profile], prefs: Optional[SearchPreferences]
) -> tuple[str, str]:
    system = (
        "You are a job-fit evaluator for one specific candidate. Score how well a job "
        "posting matches the candidate's niches, expertise, and preferences on a 1-10 scale.\n"
        "Scoring: 8-10 = excellent fit (matches their niches and constraints, worth a "
        "tailored application). 6-7 = good fit with some tradeoffs. 4-5 = moderate fit. "
        "1-3 = poor fit or red flags.\n"
        "Be strict: a generic match to their broad field is NOT enough for 8+; the role "
        "should align with their specific niches and seniority. recommendation is SUBMIT "
        "only for scores >= 7 with no disqualifying concerns."
    )

    candidate_lines: list[str] = []
    if profile is not None:
        candidate_lines.append(f"Summary: {profile.summary or 'N/A'}")
        candidate_lines.append(f"Skills: {', '.join((profile.skills or [])[:20])}")
        candidate_lines.append(f"Location: {profile.location or 'N/A'}")
        for exp in (profile.experience or [])[:4]:
            candidate_lines.append(
                f"Experience: {exp.get('title', '?')} at {exp.get('company', '?')} "
                f"({exp.get('start', '?')}–{exp.get('end', 'present')})"
            )
    if prefs is not None:
        candidate_lines.append(f"Target roles: {', '.join(prefs.target_roles or [])}")
        candidate_lines.append(f"Niches: {', '.join(prefs.niches or [])}")
        candidate_lines.append(f"Seniority: {prefs.seniority or 'N/A'}")
        if prefs.salary_floor:
            candidate_lines.append(f"Salary floor: ${prefs.salary_floor:,}/yr")
        locations = ", ".join(prefs.locations or [])
        remote = "remote OK" if prefs.remote_ok else "remote NOT acceptable"
        candidate_lines.append(f"Locations: {locations or 'N/A'} ({remote})")
        if prefs.must_have_keywords:
            candidate_lines.append(
                f"Wants to see: {', '.join(prefs.must_have_keywords)}"
            )

    user = (
        "CANDIDATE:\n" + "\n".join(candidate_lines) + "\n\n"
        f"JOB POSTING:\n"
        f"Title: {job.title}\n"
        f"Company: {job.company}\n"
        f"Location: {job.location or 'N/A'}\n"
        f"Type: {job.job_type or 'N/A'}\n"
        f"Salary: {job.salary_range or 'not stated'}\n"
        f"Description: {(job.description or '')[:2500]}\n"
        f"Requirements: {(job.requirements or '')[:1500]}"
    )
    return system, user


async def score_job(db: AsyncSession, job: Job) -> dict[str, Any]:
    """Score a job against the stored candidate context. Raises on AI failure —
    callers decide the failure policy (the safe default is SKIP, never apply)."""
    profile, prefs = await load_candidate_context(db)

    rejected = prefilter_job(job, prefs)
    if rejected is not None:
        logger.info(f"Job {job.id} pre-filtered: {rejected['reasoning']}")
        return rejected

    system, user = _build_prompt(job, profile, prefs)
    result = await ai_service.structured(system, user, _SCORE_SCHEMA, temperature=0.2)

    score = max(1, min(10, float(result.get("score", 1))))
    return {
        "score": score,
        "reasoning": result.get("reasoning", ""),
        "strengths": _coerce_to_list(result.get("strengths")),
        "concerns": _coerce_to_list(result.get("concerns")),
        "recommendation": result.get("recommendation", "SKIP"),
    }


def _coerce_to_list(value: Any) -> list[str]:
    """Normalize the AI's strengths/concerns output to a list of strings.

    The model isn't always strictly schema-compliant — it sometimes returns
    a single newline/bullet-separated string instead of a JSON array. Store
    a list either way so downstream Pydantic schemas (list[str]) don't choke.
    """
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        lines = [line.strip(" -*\t") for line in value.splitlines()]
        return [line for line in lines if line]
    return [str(value)]


async def score_and_store(
    db: AsyncSession, job: Job, rescore: bool = False
) -> dict[str, Any]:
    """Score a job and persist the result onto the Job row."""
    if job.score is not None and not rescore:
        return {
            "already_scored": True,
            "score": job.score,
            "reasoning": job.score_reasoning,
            "strengths": job.score_strengths or [],
            "concerns": job.score_concerns or [],
            "recommendation": job.score_recommendation,
        }

    result = await score_job(db, job)

    job.score = int(round(result["score"]))
    job.score_reasoning = result["reasoning"]
    job.score_strengths = result["strengths"]
    job.score_concerns = result["concerns"]
    job.score_recommendation = result["recommendation"]
    job.scored_at = datetime.utcnow()
    job.pipeline_stage = "scored"  # Update pipeline stage after scoring
    await db.commit()

    logger.info(
        f"Scored job {job.id} '{job.title}': {job.score}/10 {job.score_recommendation}"
    )
    return result
