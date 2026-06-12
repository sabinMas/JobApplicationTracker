"""
Resume extraction using AWS Bedrock AI (Qwen models).
We use Bedrock for cost-effective on-demand throughput without infrastructure overhead.
"""
import logging
try:
    import pdfplumber
    PDF_AVAILABLE = True
except ImportError:
    PDF_AVAILABLE = False

from . import ai_service

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path: str) -> str:
    """Extract all text from a PDF file using pdfplumber."""
    if not PDF_AVAILABLE:
        raise RuntimeError("pdfplumber not installed")
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
    Extract text from PDF and use AWS Bedrock AI to parse as profile.
    Returns structured profile dict.
    """
    # Extract raw text
    text = extract_text_from_pdf(pdf_path)
    if not text or len(text.strip()) < 50:
        raise ValueError("PDF appears to be empty or unreadable")

    logger.info(f"Extracted {len(text)} characters from PDF, parsing with Bedrock AI...")

    # Use Bedrock to extract profile
    profile = await ai_service.extract_profile(text)

    logger.info(f"✓ Parsed resume: {profile.get('full_name', 'Unknown')}")
    return profile
