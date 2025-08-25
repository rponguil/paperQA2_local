"""
Fallback extractor for when GROBID is not suitable or fails.
Uses PyPDF for basic text extraction.
"""
from pypdf import PdfReader
import time

from paperqa2_local.core.base import ExtractedDocument, DocumentMetadata


class FallbackExtractor:
    """A fallback extractor using PyPDF for basic text extraction."""

    async def extract_pdf(self, pdf_path: str) -> ExtractedDocument:
        """Extracts text from a PDF using PyPDF."""
        start_time = time.time()
        try:
            reader = PdfReader(pdf_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""

            # Create a minimal ExtractedDocument
            doc = ExtractedDocument(
                text=text.strip(),
                metadata=DocumentMetadata(title=pdf_path.split("/")[-1]),
                extraction_method="pypdf",
                quality_score=0.1,  # Assign a low base score
                processing_time=time.time() - start_time,
            )
            if len(text) > 100:
                doc.quality_score = 0.4  # A bit better if text was found
            return doc
        except Exception:
            # If PyPDF also fails, return a completely empty document
            return ExtractedDocument(
                text="",
                metadata=DocumentMetadata(title=pdf_path.split("/")[-1]),
                extraction_method="pypdf-failed",
                quality_score=0.0,
                processing_time=time.time() - start_time,
            )
