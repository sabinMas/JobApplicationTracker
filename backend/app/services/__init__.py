# Services package
# Individual services are imported lazily where needed to avoid
# import errors in environments where not all dependencies are available
# (e.g., Lambda doesn't need pdfplumber/reportlab/playwright)

__all__ = ["ai_service", "pdf_service", "resume_extractor"]
