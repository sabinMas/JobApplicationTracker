"""
Resume extraction using BERT-based Named Entity Recognition.
Model: yashpwr/resume-ner-bert-v2
Accuracy: 90.87% F1 score on 22,542 resume samples
"""
import logging
from typing import Optional
import pdfplumber
from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

logger = logging.getLogger(__name__)

# Initialize model and pipeline (cached globally)
_tokenizer = None
_model = None
_ner_pipeline = None

# Entity label mappings
ENTITY_LABEL_MAP = {
    "B-NAME": "name",
    "I-NAME": "name",
    "B-EMAIL": "email",
    "I-EMAIL": "email",
    "B-PHONE_NUM": "phone",
    "I-PHONE_NUM": "phone",
    "B-SKILLS": "skills",
    "I-SKILLS": "skills",
    "B-DESIGNATION": "designation",
    "I-DESIGNATION": "designation",
    "B-COMPANIES": "company",
    "I-COMPANIES": "company",
    "B-LOCATION": "location",
    "I-LOCATION": "location",
    "B-DEGREE": "degree",
    "I-DEGREE": "degree",
    "B-UNIVERSITIES": "university",
    "I-UNIVERSITIES": "university",
}


def _load_model():
    """Load BERT NER model on first use."""
    global _tokenizer, _model, _ner_pipeline
    if _ner_pipeline is None:
        logger.info("Loading BERT resume NER model (yashpwr/resume-ner-bert-v2)...")
        model_name = "yashpwr/resume-ner-bert-v2"
        _tokenizer = AutoTokenizer.from_pretrained(model_name)
        _model = AutoModelForTokenClassification.from_pretrained(model_name)
        _ner_pipeline = pipeline(
            "token-classification",
            model=_model,
            tokenizer=_tokenizer,
            aggregation_strategy="simple"
        )
        logger.info("✓ BERT model loaded successfully")
    return _ner_pipeline


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


def extract_resume_entities(text: str) -> dict:
    """
    Extract structured data from resume text using BERT NER.
    Returns a dict with keys: name, email, phone, skills, company,
    designation, location, degree, university.
    """
    ner_pipeline = _load_model()

    # Limit text to first 512 tokens to avoid model limits
    text = text[:4096]

    try:
        logger.info(f"Running NER on {len(text)} characters of resume text...")
        entities = ner_pipeline(text)

        # Group entities by type
        extracted = {
            "name": [],
            "email": [],
            "phone": [],
            "skills": [],
            "company": [],
            "designation": [],
            "location": [],
            "degree": [],
            "university": [],
        }

        for entity in entities:
            label = entity.get("entity_group", "O")
            word = entity.get("word", "").strip()

            # Map label to our schema
            if label in ENTITY_LABEL_MAP:
                entity_type = ENTITY_LABEL_MAP[label]
                if word and word not in extracted[entity_type]:
                    extracted[entity_type].append(word)

        logger.info(f"✓ Extracted entities: {len(extracted)} types, total words: {sum(len(v) for v in extracted.values())}")
        return extracted
    except Exception as e:
        logger.error(f"Error running NER: {str(e)}")
        raise


def parse_resume(pdf_path: str) -> dict:
    """
    Main function: extract text from PDF, then extract entities using BERT.
    Returns structured profile dict.
    """
    # Extract raw text
    text = extract_text_from_pdf(pdf_path)
    if not text or len(text.strip()) < 50:
        raise ValueError("PDF appears to be empty or unreadable")

    logger.info(f"Extracted {len(text)} characters from PDF")

    # Extract entities
    entities = extract_resume_entities(text)

    # Format as profile dict
    profile = {
        "full_name": entities["name"][0] if entities["name"] else None,
        "email": entities["email"][0] if entities["email"] else None,
        "phone": entities["phone"][0] if entities["phone"] else None,
        "location": entities["location"][0] if entities["location"] else None,
        "summary": None,  # Not provided by BERT NER
        "skills": entities["skills"],  # Array of skill strings
        "experience": [],  # Not extracted by basic NER (would need additional parsing)
        "education": [
            {
                "school": entities["university"][0] if entities["university"] else None,
                "degree": entities["degree"][0] if entities["degree"] else None,
                "field": None,
                "start": None,
                "end": None,
                "gpa": None,
            }
        ] if (entities["university"] or entities["degree"]) else [],
        "certifications": [],
    }

    return profile
