"""
PDF text extraction (pdfplumber) and PDF generation (reportlab).
"""
import pdfplumber
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import re
from pathlib import Path


def extract_text(pdf_path: str) -> str:
    """Extract all text from a PDF file."""
    text_parts = []
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            text = page.extract_text()
            if text:
                text_parts.append(text)
    return "\n\n".join(text_parts)


def markdown_to_pdf(markdown_text: str, output_path: str, doc_type: str = "resume") -> str:
    """
    Convert markdown text to a clean PDF.
    Supports: # H1, ## H2, ### H3, - bullets, plain paragraphs.
    Returns the output_path.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=letter,
        rightMargin=0.75 * inch,
        leftMargin=0.75 * inch,
        topMargin=0.75 * inch,
        bottomMargin=0.75 * inch,
    )

    styles = getSampleStyleSheet()

    style_h1 = ParagraphStyle(
        "H1", parent=styles["Heading1"],
        fontSize=18, spaceAfter=4, textColor=colors.HexColor("#1a1a2e"),
        alignment=TA_CENTER,
    )
    style_h2 = ParagraphStyle(
        "H2", parent=styles["Heading2"],
        fontSize=13, spaceBefore=10, spaceAfter=2,
        textColor=colors.HexColor("#16213e"),
        borderPad=0,
    )
    style_h3 = ParagraphStyle(
        "H3", parent=styles["Heading3"],
        fontSize=11, spaceBefore=6, spaceAfter=2,
        textColor=colors.HexColor("#0f3460"),
    )
    style_body = ParagraphStyle(
        "Body", parent=styles["Normal"],
        fontSize=10, leading=14, spaceAfter=3,
    )
    style_bullet = ParagraphStyle(
        "Bullet", parent=styles["Normal"],
        fontSize=10, leading=13, leftIndent=16, bulletIndent=6, spaceAfter=2,
    )

    story = []
    lines = markdown_text.split("\n")

    for line in lines:
        stripped = line.strip()
        if not stripped:
            story.append(Spacer(1, 4))
            continue

        if stripped.startswith("### "):
            story.append(Paragraph(stripped[4:], style_h3))
        elif stripped.startswith("## "):
            story.append(HRFlowable(width="100%", thickness=0.5, color=colors.HexColor("#cccccc"), spaceAfter=2))
            story.append(Paragraph(stripped[3:].upper(), style_h2))
        elif stripped.startswith("# "):
            story.append(Paragraph(stripped[2:], style_h1))
        elif stripped.startswith("- ") or stripped.startswith("* "):
            story.append(Paragraph(f"• {stripped[2:]}", style_bullet))
        else:
            # Inline bold/italic: **text** → <b>text</b>
            formatted = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", stripped)
            formatted = re.sub(r"\*(.+?)\*", r"<i>\1</i>", formatted)
            story.append(Paragraph(formatted, style_body))

    doc.build(story)
    return output_path
