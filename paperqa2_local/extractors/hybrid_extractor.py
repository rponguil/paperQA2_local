"""
Orquestador que decide qué extractor usar y maneja fallbacks.

Lógica de decisión:
1. Intentar GROBID primero para PDFs científicos
2. Si falla o calidad baja, usar fallback PyPDF
3. Logging detallado de decisiones
4. Métricas de performance por extractor
"""
from paperqa2_local.core.base import ExtractedDocument
from .grobid_extractor import GrobidExtractor
from .fallback_extractor import FallbackExtractor


class HybridExtractor:
    """
    Orchestrator that decides which extractor to use and handles fallbacks.
    """

    def __init__(
        self,
        grobid_extractor: GrobidExtractor,
        fallback_extractor: FallbackExtractor,
        quality_threshold: float = 0.7,
    ):
        """Inicializar con extractores y umbral de calidad."""
        self.grobid_extractor = grobid_extractor
        self.fallback_extractor = fallback_extractor
        self.quality_threshold = quality_threshold

    async def extract_pdf(self, pdf_path: str) -> ExtractedDocument:
        """
        Estrategia de extracción inteligente:
        1. Intentar con GROBID.
        2. Validar calidad.
        3. Fallback a otro extractor si es necesario.
        """
        try:
            # Step 1: Attempt extraction with Grobid
            grobid_doc = await self.grobid_extractor.extract_pdf(pdf_path)

            # Step 2: Validate quality
            if grobid_doc.quality_score >= self.quality_threshold:
                return grobid_doc

        except Exception:
            # If GROBID fails for any reason (e.g., server down, parsing error),
            # we will fall back. The error should be logged in a real system.
            pass

        # Step 3: Fallback if Grobid failed or quality was low
        fallback_doc = await self.fallback_extractor.extract_pdf(pdf_path)
        return fallback_doc
