from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import shutil
from pathlib import Path
import os
import time
import unicodedata

from ..database import get_db
from ..models import Profile, Document, SearchPreferences
from ..schemas import (
    ProfileUpdate,
    ProfileOut,
    SearchPreferencesUpdate,
    SearchPreferencesOut,
)
from ..services import ai_service, pdf_service, resume_extractor, profile_service

router = APIRouter(prefix="/api/profile", tags=["profile"])

DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp/data" if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else str(Path(__file__).parent.parent.parent.parent / "data")))


def _sanitize_filename(filename: str) -> str:
    """Remove or replace Unicode characters that Windows can't handle."""
    # Normalize unicode (NFD decomposition)
    filename = unicodedata.normalize('NFKD', filename)
    # Keep only ASCII letters, digits, and safe punctuation
    filename = ''.join(c for c in filename if c.isascii() and (c.isalnum() or c in '._- '))
    # If filename becomes empty, use timestamp-based name
    if not filename or filename.startswith('.'):
        filename = f"resume_{int(time.time())}.pdf"
    return filename


@router.get("", response_model=ProfileOut)
async def get_profile(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Profile))
    profile = result.scalar_one_or_none()
    if not profile:
        # Create empty profile on first access
        profile = Profile(id=1)
        db.add(profile)
        await db.commit()
        await db.refresh(profile)
    return profile


@router.put("", response_model=ProfileOut)
async def update_profile(data: ProfileUpdate, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Profile))
    profile = result.scalar_one_or_none()
    if not profile:
        profile = Profile(id=1)
        db.add(profile)

    for field, value in data.model_dump(exclude_none=True).items():
        setattr(profile, field, value)

    await db.commit()
    await db.refresh(profile)
    return profile


@router.post("/extract")
async def extract_profile_from_resume(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """Upload a PDF resume → Claude extracts structured profile → auto-merge into profile."""
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(400, "Only PDF files are supported.")

        save_dir = DATA_DIR / "documents" / "resumes"
        save_dir.mkdir(parents=True, exist_ok=True)

        # Sanitize filename to avoid Unicode issues on Windows
        safe_filename = unicodedata.normalize('NFKD', file.filename).encode('ascii', 'ignore').decode('ascii')
        if not safe_filename:
            safe_filename = f"resume_{int(time.time())}.pdf"
        file_path = save_dir / safe_filename

        # Save file
        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            print(f"[EXTRACT] File saved to: {file_path}")
        except Exception as e:
            print(f"[EXTRACT] ERROR saving file: {type(e).__name__}: {str(e)}")
            raise HTTPException(400, f"Failed to save file: {str(e)}")

        # Extract profile using AI (Qwen via AWS Bedrock)
        try:
            print(f"[EXTRACT] Parsing resume with Claude...")
            extracted = await resume_extractor.parse_resume(str(file_path))
            if not extracted:
                print(f"[EXTRACT] AI returned empty profile - user can fill in manually")
            else:
                print(f"[EXTRACT] Profile extracted: {extracted.get('full_name', 'Unknown')}")
                print(f"[EXTRACT]   - Skills: {len(extracted.get('skills', []))} found")
                print(f"[EXTRACT]   - Experience: {len(extracted.get('experience', []))} entries")
                print(f"[EXTRACT]   - Education: {len(extracted.get('education', []))} entries")
        except Exception as e:
            print(f"[EXTRACT] AI extraction failed: {type(e).__name__}: {str(e)}")
            print("[EXTRACT] Continuing with empty profile - user can fill in manually")
            extracted = {}

        # Merge extracted data with existing profile
        try:
            result = await db.execute(select(Profile))
            profile = result.scalar_one_or_none()
            if not profile:
                profile = Profile(id=1)
                db.add(profile)
                await db.flush()  # Get the profile in the session

            print(f"[MERGE] Merging extracted data into existing profile...")
            merged_profile, changed_fields = await profile_service.merge_extracted_profile(profile, extracted)
            await db.commit()
            await db.refresh(merged_profile)
            print(f"[MERGE] Profile merged: {len(changed_fields)} fields updated: {changed_fields}")
        except Exception as e:
            print(f"[MERGE] Profile merge failed: {type(e).__name__}: {str(e)}")
            print("[MERGE] Continuing - extracted data will be returned for manual review")
            merged_profile = None
            changed_fields = []

        # Save document record
        try:
            # Get the raw text for storage
            text = resume_extractor.extract_text_from_pdf(str(file_path))
            doc = Document(
                type="resume",
                variant="base",
                filename=safe_filename,
                file_path=str(file_path),
                content_text=text,
            )
            db.add(doc)
            await db.commit()
            print(f"[EXTRACT] Document saved to DB with ID: {doc.id}")
        except Exception as e:
            print(f"[EXTRACT] ERROR saving document to DB: {type(e).__name__}: {str(e)}")
            raise HTTPException(500, f"Failed to save document: {str(e)}")

        return {
            "extracted": extracted,
            "merged": merged_profile if merged_profile else None,
            "document_id": doc.id,
            "changes": changed_fields,
        }
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR extracting profile (outer catch): {type(e).__name__}: {str(e)}")
        raise HTTPException(500, f"Profile extraction failed: {str(e)}")


# ─── Search Preferences ──────────────────────────────────────────────────────

async def _get_or_create_preferences(db: AsyncSession) -> SearchPreferences:
    result = await db.execute(select(SearchPreferences))
    prefs = result.scalar_one_or_none()
    if not prefs:
        prefs = SearchPreferences(id=1)
        db.add(prefs)
        await db.commit()
        await db.refresh(prefs)
    return prefs


@router.get("/preferences", response_model=SearchPreferencesOut)
async def get_preferences(db: AsyncSession = Depends(get_db)):
    """Get job search preferences (niches, keywords, thresholds)."""
    return await _get_or_create_preferences(db)


@router.put("/preferences", response_model=SearchPreferencesOut)
async def update_preferences(
    data: SearchPreferencesUpdate, db: AsyncSession = Depends(get_db)
):
    """Update job search preferences."""
    prefs = await _get_or_create_preferences(db)
    for field, value in data.model_dump(exclude_none=True).items():
        setattr(prefs, field, value)
    await db.commit()
    await db.refresh(prefs)
    return prefs


@router.post("/preferences/seed", response_model=SearchPreferencesOut)
async def seed_preferences(db: AsyncSession = Depends(get_db)):
    """Propose initial preferences from the stored profile using AI, persist,
    and return them for review/editing."""
    result = await db.execute(select(Profile))
    profile = result.scalar_one_or_none()
    if not profile or not (profile.skills or profile.experience or profile.summary):
        raise HTTPException(
            400, "Profile is empty — upload a resume via /api/profile/extract first."
        )

    profile_dict = {
        "full_name": profile.full_name,
        "location": profile.location,
        "summary": profile.summary,
        "skills": profile.skills or [],
        "experience": profile.experience or [],
        "education": profile.education or [],
        "certifications": profile.certifications or [],
    }
    suggested = await ai_service.suggest_search_preferences(profile_dict)

    prefs = await _get_or_create_preferences(db)
    for field in (
        "target_roles", "niches", "must_have_keywords", "avoid_keywords",
        "salary_floor", "locations", "remote_ok", "seniority", "job_types",
    ):
        if field in suggested and suggested[field] is not None:
            setattr(prefs, field, suggested[field])
    await db.commit()
    await db.refresh(prefs)
    return prefs
