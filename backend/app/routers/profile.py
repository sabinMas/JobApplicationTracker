from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import shutil
from pathlib import Path
import os

from ..database import get_db
from ..models import Profile, Document
from ..schemas import ProfileUpdate, ProfileOut
from ..services import pdf_service, cerebras_service, resume_extractor

router = APIRouter(prefix="/api/profile", tags=["profile"])

DATA_DIR = Path(os.getenv("DATA_DIR", Path(__file__).parent.parent.parent.parent / "data"))


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
    """Upload a PDF resume → BERT NER extracts structured profile → returns for review."""
    try:
        if not file.filename.endswith(".pdf"):
            raise HTTPException(400, "Only PDF files are supported.")

        save_dir = DATA_DIR / "documents" / "resumes"
        save_dir.mkdir(parents=True, exist_ok=True)
        file_path = save_dir / file.filename

        # Save file
        try:
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)
            print(f"✓ File saved to: {file_path}")
        except Exception as e:
            print(f"ERROR saving file: {type(e).__name__}: {str(e)}")
            raise HTTPException(400, f"Failed to save file: {str(e)}")

        # Extract profile using BERT NER (no Cerebras needed for basic extraction)
        try:
            print(f"Parsing resume with BERT NER model...")
            extracted = resume_extractor.parse_resume(str(file_path))
            print(f"✓ Profile extracted successfully: {extracted.get('full_name', 'Unknown')}")
            print(f"  - Skills found: {len(extracted.get('skills', []))}")
        except Exception as e:
            print(f"ERROR extracting profile with BERT: {type(e).__name__}: {str(e)}")
            raise HTTPException(400, f"Failed to extract profile: {str(e)}")

        # Save document record
        try:
            # Get the raw text for storage
            text = resume_extractor.extract_text_from_pdf(str(file_path))
            doc = Document(
                type="resume",
                variant="base",
                filename=file.filename,
                file_path=str(file_path),
                content_text=text,
            )
            db.add(doc)
            await db.commit()
            print(f"✓ Document saved to DB with ID: {doc.id}")
        except Exception as e:
            print(f"ERROR saving document to DB: {type(e).__name__}: {str(e)}")
            raise HTTPException(500, f"Failed to save document: {str(e)}")

        return {"extracted": extracted, "document_id": doc.id}
    except HTTPException:
        raise
    except Exception as e:
        print(f"ERROR extracting profile (outer catch): {type(e).__name__}: {str(e)}")
        raise HTTPException(500, f"Profile extraction failed: {str(e)}")
