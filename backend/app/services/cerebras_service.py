"""
All Cerebras AI interactions via the OpenAI-compatible endpoint.
Model: llama-3.3-70b (fast, smart enough for structured extraction).
"""
import json
import os
from openai import AsyncOpenAI
from dotenv import load_dotenv

load_dotenv()

_client = AsyncOpenAI(
    api_key=os.getenv("CEREBRAS_API_KEY"),
    base_url="https://api.cerebras.ai/v1",
)
MODEL = "gpt-oss-120b"


async def _chat(system: str, user: str, temperature: float = 0.3) -> str:
    resp = await _client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        temperature=temperature,
    )
    return resp.choices[0].message.content.strip()


async def extract_job(page_text: str) -> dict:
    """
    Given raw text scraped from a job posting page, return structured job data.
    """
    system = (
        "You are a job data extractor. Given raw text from a job posting webpage, "
        "extract structured information and return ONLY valid JSON with these keys: "
        "title, company, location, job_type (full-time/part-time/contract/internship), "
        "apply_url, description, requirements, salary_range, posted_date. "
        "Use null for missing fields. Return only JSON, no explanation."
    )
    result = await _chat(system, f"Job page text:\n\n{page_text[:8000]}")
    # Strip markdown fences if present
    result = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {"title": "Unknown", "company": "Unknown", "description": page_text[:500]}


async def extract_profile(resume_text: str) -> dict:
    """
    Given raw text from a resume PDF, return structured profile data.
    """
    system = (
        "You are a resume parser. Given resume text, extract a structured profile and return "
        "ONLY valid JSON with keys: full_name, email, phone, location, linkedin_url, github_url, "
        "portfolio_url, summary, skills (array of strings), "
        "experience (array of {company, title, start, end, bullets}), "
        "education (array of {school, degree, field, start, end, gpa}), "
        "certifications (array of {name, issuer, date}). "
        "Use null or empty arrays for missing fields. Return only JSON."
    )
    result = await _chat(system, f"Resume text:\n\n{resume_text[:8000]}")
    result = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {}


async def tailor_resume(
    job_description: str,
    job_requirements: str,
    base_resume_text: str,
    profile: dict,
) -> str:
    """
    Return tailored resume text (markdown) optimized for the job.
    """
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
    return await _chat(system, user, temperature=0.4)


async def generate_cover_letter(
    job_description: str,
    company: str,
    job_title: str,
    profile: dict,
    example_cover_letters: list[str],
) -> str:
    """
    Return a tailored cover letter in plain text.
    """
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
    return await _chat(system, user, temperature=0.6)


async def map_form_fields(field_labels: list[str], profile: dict) -> dict:
    """
    Given a list of form field labels from an application page, return a mapping
    of label → value drawn from the user's profile.
    """
    system = (
        "You are a job application form assistant. Given form field labels and a candidate profile, "
        "return a JSON object mapping each field label to the appropriate value from the profile. "
        "For unknown or inapplicable fields use null. "
        "Common mappings: 'First Name'→first name, 'LinkedIn URL'→linkedin_url, "
        "'Resume'→null (file upload handled separately), etc. "
        "Return ONLY valid JSON."
    )
    user = (
        f"FORM FIELDS: {json.dumps(field_labels)}\n\n"
        f"PROFILE: {json.dumps(profile, indent=2)[:3000]}"
    )
    result = await _chat(system, user, temperature=0.1)
    result = result.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    try:
        return json.loads(result)
    except json.JSONDecodeError:
        return {}
