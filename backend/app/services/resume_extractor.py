"""
Resume extraction using Cerebras AI.
We use the Cerebras API instead of transformers/torch for lightweight deployment.
"""
import logging
import pdfplumber
from . import cerebras_service

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file using pdfplumber."""
    text_parts = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    text_parts.append(text)
        return "\n\n".join(text_parts)
    except Exception as e:
        logger.error(f"Error extracting text from PDF: {str(e)}")
        raise


async def parse_resume(pdf_path: str) -> dict:
    """
    Extract text from PDF and use Cerebras AI to parse as profile.
    Returns structured profile dict.
    """
    # Extract raw text
    text = extract_text_from_pdf(pdf_path)
    if not text or len(text.strip()) < 50:
        raise ValueError("PDF appears to be empty or unreadable")

    logger.info(f"Extracted {len(text)} characters from PDF, parsing with Cerebras...")

    # Use Cerebras to extract profile
    profile = await cerebras_service.extract_profile(text)

    logger.info(f"✓ Parsed resume: {profile.get('full_name', 'Unknown')}")
    return profile
