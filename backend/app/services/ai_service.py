"""
Provider-routing AI layer.

Primary provider: AWS Bedrock (Amazon Nova) via the async Converse API — paid
with AWS credits, IAM-authenticated, no API key and no use-case form needed.
Fallback provider: Cerebras (OpenAI-compatible endpoint).

Routing is controlled by the AI_PROVIDER env var ("bedrock" | "cerebras",
default "bedrock"). If the primary provider fails, the call falls back to the
other provider automatically.

Two model tiers:
- FAST  (extraction, scoring, field mapping): Amazon Nova Lite
- SMART (resume tailoring, cover letters):    Amazon Nova Pro

All high-level AI functions used across the app live here. Service modules
should import from `ai_service`, not from `cerebras_service`.
"""

import json
import logging
import os
from typing import Any, Optional

import aioboto3

from . import cerebras_service

logger = logging.getLogger(__name__)

AI_PROVIDER = os.getenv("AI_PROVIDER", "bedrock")
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")

# Amazon Nova models — NO gate required, available immediately
# Support forced tool-use (structured output) via Bedrock Converse API
# FAST  (extraction, scoring, field mapping): Nova Lite (~faster, cheaper)
# SMART (resume tailoring, cover letters):    Nova Pro (~higher quality)
BEDROCK_FAST_MODEL = os.getenv("BEDROCK_FAST_MODEL", "amazon.nova-lite-v1:0")
BEDROCK_SMART_MODEL = os.getenv("BEDROCK_SMART_MODEL", "amazon.nova-pro-v1:0")

logger.info(f"AI Provider: {AI_PROVIDER.upper()} | Fast: {BEDROCK_FAST_MODEL} | Smart: {BEDROCK_SMART_MODEL}")

_session = aioboto3.Session()


async def _bedrock_chat(
    system: str,
    user: str,
    temperature: float,
    model_id: str,
    max_tokens: int = 4096,
    tool_schema: Optional[dict] = None,
    tool_name: str = "structured_output",
) -> str | dict:
    """Call Bedrock Converse (Amazon Nova models — no gate required).
    If tool_schema given, force structured output; otherwise return text."""
    kwargs: dict[str, Any] = {
        "modelId": model_id,
        "system": [{"text": system}],
        "messages": [{"role": "user", "content": [{"text": user}]}],
        "inferenceConfig": {"temperature": temperature, "maxTokens": max_tokens},
    }
    if tool_schema is not None:
        kwargs["toolConfig"] = {
            "tools": [
                {
                    "toolSpec": {
                        "name": tool_name,
                        "description": "Return the structured result.",
                        "inputSchema": {"json": tool_schema},
                    }
                }
            ],
            "toolChoice": {"tool": {"name": tool_name}},
        }

    logger.debug(f"Calling Bedrock Converse: model={model_id}, structured={tool_schema is not None}")
    try:
        async with _session.client("bedrock-runtime", region_name=AWS_REGION) as client:
            response = await client.converse(**kwargs)
    except Exception as e:
        logger.error(f"Bedrock API error: {type(e).__name__}: {str(e)[:200]}")
        raise

    content = response["output"]["message"]["content"]
    if tool_schema is not None:
        for block in content:
            if "toolUse" in block:
                logger.debug(f"Bedrock returned structured output successfully")
                return block["toolUse"]["input"]
        raise ValueError("Bedrock response contained no toolUse block")

    text_response = "".join(block.get("text", "") for block in content).strip()
    logger.debug(f"Bedrock returned text response ({len(text_response)} chars)")
    return text_response


def _parse_json_text(result: str) -> dict:
    """Best-effort JSON parse for providers without native structured output."""
    result = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    return json.loads(result)


async def chat(
    system: str,
    user: str,
    temperature: float = 0.3,
    tier: str = "fast",
) -> str:
    """Free-text completion routed to the configured provider with fallback."""
    model_id = BEDROCK_SMART_MODEL if tier == "smart" else BEDROCK_FAST_MODEL
    providers = ["bedrock", "cerebras"] if AI_PROVIDER == "bedrock" else ["cerebras", "bedrock"]
    last_error: Exception | None = None
    for provider in providers:
        try:
            if provider == "bedrock":
                return await _bedrock_chat(system, user, temperature, model_id)
            return await cerebras_service._chat(system, user, temperature)
        except Exception as e:
            last_error = e
            logger.warning(
                f"AI provider '{provider}' failed, trying next")
    raise RuntimeError(f"All AI providers failed: {last_error}")


async def structured(
    system: str,
    user: str,
    schema: dict,
    temperature: float = 0.2,
    tier: str = "fast",
) -> dict:
    """Structured-output completion. Uses Bedrock tool-use when available,
    falls back to JSON-in-text parsing on Cerebras."""
    model_id = BEDROCK_SMART_MODEL if tier == "smart" else BEDROCK_FAST_MODEL
    providers = ["bedrock", "cerebras"] if AI_PROVIDER == "bedrock" else ["cerebras", "bedrock"]
    last_error: Exception | None = None
    errors: dict[str, str] = {}

    for provider in providers:
        try:
            logger.info(f"Trying AI provider: {provider} (tier={tier}, model={model_id if provider == 'bedrock' else 'cerebras'})")
            if provider == "bedrock":
                result = await _bedrock_chat(
                    system, user, temperature, model_id, tool_schema=schema
                )
                assert isinstance(result, dict)
                logger.info(f"✓ Bedrock succeeded")
                return result
            text = await cerebras_service._chat(
                system + " Return ONLY valid JSON matching the requested structure.",
                user,
                temperature,
            )
            result = _parse_json_text(text)
            logger.info(f"✓ Cerebras succeeded")
            return result
        except Exception as e:
            last_error = e
            error_msg = f"{type(e).__name__}: {str(e)[:200]}"
            errors[provider] = error_msg
            logger.warning(
                f"AI provider '{provider}' failed: {error_msg}, trying next...")

    error_detail = "; ".join(f"{k}={v}" for k, v in errors.items())
    raise RuntimeError(f"All AI providers failed — {error_detail}")


# ─── High-level functions (the app-facing API) ───────────────────────────────

_JOB_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": ["string", "null"]},
        "company": {"type": ["string", "null"]},
        "location": {"type": ["string", "null"]},
        "job_type": {"type": ["string", "null"]},
        "apply_url": {"type": ["string", "null"]},
        "description": {"type": ["string", "null"]},
        "requirements": {"type": ["string", "null"]},
        "salary_range": {"type": ["string", "null"]},
        "posted_date": {"type": ["string", "null"]},
    },
    "required": ["title", "company"],
}


async def extract_job(page_text: str) -> dict:
    """Given raw text scraped from a job posting page, return structured job data."""
    system = (
        "You are a job data extractor. Given raw text from a job posting webpage, "
        "extract structured information. job_type is one of "
        "full-time/part-time/contract/internship. Use null for missing fields."
    )
    try:
        return await structured(
            system, f"Job page text:\n\n{page_text[:8000]}", _JOB_SCHEMA, temperature=0.1
        )
    except Exception as e:
        logger.error(f"extract_job failed: {e}")
        return {"title": "Unknown", "company": "Unknown", "description": page_text[:500]}


_PROFILE_SCHEMA = {
    "type": "object",
    "properties": {
        "full_name": {"type": ["string", "null"]},
        "email": {"type": ["string", "null"]},
        "phone": {"type": ["string", "null"]},
        "location": {"type": ["string", "null"]},
        "linkedin_url": {"type": ["string", "null"]},
        "github_url": {"type": ["string", "null"]},
        "portfolio_url": {"type": ["string", "null"]},
        "summary": {"type": ["string", "null"]},
        "skills": {"type": "array", "items": {"type": "string"}},
        "experience": {"type": "array", "items": {"type": "object"}},
        "education": {"type": "array", "items": {"type": "object"}},
        "certifications": {"type": "array", "items": {"type": "object"}},
    },
}


async def extract_profile(resume_text: str) -> dict:
    """Given raw text from a resume PDF, return structured profile data."""
    system = (
        "You are a resume parser. Extract a structured candidate profile. "
        "experience items are {company, title, start, end, bullets}; "
        "education items are {school, degree, field, start, end, gpa}; "
        "certifications items are {name, issuer, date}. "
        "Use null or empty arrays for missing fields."
    )
    try:
        logger.info(f"Starting profile extraction from {len(resume_text)} chars of resume text")
        result = await structured(
            system, f"Resume text:\n\n{resume_text[:8000]}", _PROFILE_SCHEMA, temperature=0.1
        )
        logger.info(f"✓ Profile extraction succeeded: {result.get('full_name', 'Unknown')}")
        return result
    except Exception as e:
        logger.error(f"✗ extract_profile failed: {type(e).__name__}: {str(e)}", exc_info=True)
        logger.warning(f"Falling back to returning empty profile (user can fill in manually)")
        return {}


_PREFERENCES_SCHEMA = {
    "type": "object",
    "properties": {
        "target_roles": {"type": "array", "items": {"type": "string"}},
        "niches": {"type": "array", "items": {"type": "string"}},
        "must_have_keywords": {"type": "array", "items": {"type": "string"}},
        "avoid_keywords": {"type": "array", "items": {"type": "string"}},
        "salary_floor": {"type": ["integer", "null"]},
        "locations": {"type": "array", "items": {"type": "string"}},
        "remote_ok": {"type": "boolean"},
        "seniority": {"type": ["string", "null"]},
        "job_types": {"type": "array", "items": {"type": "string"}},
    },
}


async def suggest_search_preferences(profile: dict) -> dict:
    """Propose initial SearchPreferences from an extracted resume profile."""
    system = (
        "You are a career advisor. Given a candidate's structured profile, propose job "
        "search preferences that capture their specific niches and expertise. "
        "target_roles: 3-6 concrete job titles they are qualified for. "
        "niches: 3-6 specialty areas that differentiate them (be specific, e.g. "
        "'LLM application development' not 'AI'). "
        "must_have_keywords: 5-10 technologies/domains a good-fit posting would mention. "
        "avoid_keywords: red-flag terms given their background (e.g. wrong stack, "
        "clearance requirements they lack). "
        "seniority: one of entry/mid/senior/staff based on years of experience. "
        "job_types: usually ['full-time']. locations: from their stated location, plus "
        "'Remote'. salary_floor: a reasonable conservative floor in USD for their level, "
        "or null if unclear."
    )
    return await structured(
        system,
        f"CANDIDATE PROFILE:\n{json.dumps(profile, indent=2)[:6000]}",
        _PREFERENCES_SCHEMA,
        temperature=0.3,
    )


async def tailor_resume(
    job_description: str,
    job_requirements: str,
    base_resume_text: str,
    profile: dict,
) -> str:
    """Return tailored resume text (markdown) optimized for the job."""
    system = (
        "You are an expert resume writer. Given a job description and a candidate's resume, "
        "rewrite the resume to be highly tailored for this specific role. "
        "- Emphasize relevant skills and experience that match the job requirements. "
        "- Rewrite bullet points to use strong action verbs and quantify impact where possible. "
        "- Mirror keywords from the job description naturally. "
        "- Keep all factual information accurate — do NOT invent experience. "
        "- Format output as clean markdown: use ## for sections, - for bullets. "
        "Return only the tailored resume in markdown, no preamble."
    )
    user = (
        f"JOB TITLE & DESCRIPTION:\n{job_description[:3000]}\n\n"
        f"JOB REQUIREMENTS:\n{job_requirements[:2000]}\n\n"
        f"CANDIDATE RESUME:\n{base_resume_text[:4000]}"
    )
    return await chat(system, user, temperature=0.4, tier="smart")


async def generate_cover_letter(
    job_description: str,
    company: str,
    job_title: str,
    profile: dict,
    example_cover_letters: list[str],
) -> str:
    """Return a tailored cover letter in plain text."""
    examples_block = "\n\n---\n\n".join(
        f"EXAMPLE {i+1}:\n{ex[:1500]}" for i, ex in enumerate(example_cover_letters[:3])
    )
    system = (
        "You are an expert cover letter writer. Write a compelling, personalized cover letter "
        "for the candidate applying to this specific role. "
        "- Match the tone and style of the provided example cover letters. "
        "- Highlight 2-3 specific achievements that are most relevant to this role. "
        "- Show genuine enthusiasm for the company. "
        "- Keep it to 3-4 concise paragraphs (under 400 words). "
        "Return only the cover letter body text (no subject line or metadata)."
    )
    user = (
        f"COMPANY: {company}\nROLE: {job_title}\n\n"
        f"JOB DESCRIPTION:\n{job_description[:3000]}\n\n"
        f"CANDIDATE PROFILE:\n{json.dumps(profile, indent=2)[:2000]}\n\n"
        f"EXAMPLE COVER LETTERS FOR STYLE REFERENCE:\n{examples_block}"
    )
    return await chat(system, user, temperature=0.6, tier="smart")


async def map_form_fields(field_labels: list[str], profile: dict) -> dict:
    """Given form field labels from an application page, return label → value
    mappings drawn from the user's profile."""
    system = (
        "You are a job application form assistant. Given form field labels and a candidate "
        "profile, return a JSON object mapping each field label to the appropriate value "
        "from the profile. For unknown or inapplicable fields use null. "
        "Common mappings: 'First Name'→first name, 'LinkedIn URL'→linkedin_url, "
        "'Resume'→null (file upload handled separately)."
    )
    user = (
        f"FORM FIELDS: {json.dumps(field_labels)}\n\n"
        f"PROFILE: {json.dumps(profile, indent=2)[:3000]}"
    )
    schema = {
        "type": "object",
        "properties": {
            "mappings": {
                "type": "object",
                "description": "field label → value or null",
            }
        },
        "required": ["mappings"],
    }
    try:
        result = await structured(system, user, schema, temperature=0.1)
        return result.get("mappings", result)
    except Exception as e:
        logger.error(f"map_form_fields failed: {e}")
        return {}
