from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import shutil
from pathlib import Path
import os
from typing import List

from ..database import get_db
from ..models import Document
from ..schemas import DocumentOut
from ..services import pdf_service

router = APIRouter(prefix="/api/documents", tags=["documents"])

DATA_DIR = Path(os.getenv("DATA_DIR", "/tmp/data" if os.getenv("AWS_LAMBDA_FUNCTION_NAME") else str(Path(__file__).parent.parent.parent.parent / "data")))


@router.get("", response_model=List[DocumentOut])
async def list_documents(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).order_by(Document.created_at.desc()))
    return result.scalars().all()


@router.post("/upload", response_model=DocumentOut)
async def upload_document(
    file: UploadFile = File(...),
    doc_type: str = Form(...),  # "resume" or "cover_letter"
    db: AsyncSession = Depends(get_db),
):
    """Upload a base resume or cover letter PDF."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(400, "Only PDF files are supported.")
    if doc_type not in ("resume", "cover_letter"):
        raise HTTPException(400, "doc_type must be 'resume' or 'cover_letter'.")

    subfolder = "resumes" if doc_type == "resume" else "cover_letters"
    save_dir = DATA_DIR / "documents" / subfolder
    save_dir.mkdir(parents=True, exist_ok=True)
    file_path = save_dir / file.filename

    with open(file_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    text = pdf_service.extract_text(str(file_path))

    doc = Document(
        type=doc_type,
        variant="base",
        filename=file.filename,
        file_path=str(file_path),
        content_text=text,
    )
    db.add(doc)
    await db.commit()
    await db.refresh(doc)
    return doc


@router.get("/{doc_id}/download")
async def download_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found.")
    if not Path(doc.file_path).exists():
        raise HTTPException(404, "File not found on disk.")
    return FileResponse(doc.file_path, media_type="application/pdf", filename=doc.filename)


@router.delete("/{doc_id}")
async def delete_document(doc_id: int, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Document).where(Document.id == doc_id))
    doc = result.scalar_one_or_none()
    if not doc:
        raise HTTPException(404, "Document not found.")
    try:
        Path(doc.file_path).unlink(missing_ok=True)
    except Exception:
        pass
    await db.delete(doc)
    await db.commit()
    return {"ok": True}
