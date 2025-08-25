import pytest
from unittest.mock import AsyncMock

from paperqa2_local.core.base import DocumentMetadata, ExtractedDocument
from paperqa2_local.extractors.hybrid_extractor import HybridExtractor


@pytest.fixture
def mock_grobid_extractor():
    """Provides a mock for the GrobidExtractor."""
    return AsyncMock()


@pytest.fixture
def mock_fallback_extractor():
    """Provides a mock for the FallbackExtractor."""
    return AsyncMock()


@pytest.fixture
def hybrid_extractor(mock_grobid_extractor, mock_fallback_extractor):
    """Provides a HybridExtractor instance with mocked dependencies."""
    return HybridExtractor(
        grobid_extractor=mock_grobid_extractor,
        fallback_extractor=mock_fallback_extractor,
        quality_threshold=0.7,
    )


@pytest.mark.asyncio
async def test_uses_grobid_on_high_quality(
    hybrid_extractor, mock_grobid_extractor, mock_fallback_extractor
):
    """Test that the GROBID result is used when its quality score is high."""
    high_quality_doc = ExtractedDocument(
        text="High quality text", metadata=DocumentMetadata(), quality_score=0.9
    )
    mock_grobid_extractor.extract_pdf.return_value = high_quality_doc

    result = await hybrid_extractor.extract_pdf("dummy.pdf")

    assert result == high_quality_doc
    mock_grobid_extractor.extract_pdf.assert_called_once_with("dummy.pdf")
    mock_fallback_extractor.extract_pdf.assert_not_called()


@pytest.mark.asyncio
async def test_falls_back_on_low_quality(
    hybrid_extractor, mock_grobid_extractor, mock_fallback_extractor
):
    """Test that the fallback extractor is used when GROBID's quality is low."""
    low_quality_doc = ExtractedDocument(
        text="Low quality text", metadata=DocumentMetadata(), quality_score=0.5
    )
    fallback_doc = ExtractedDocument(
        text="Fallback document text", metadata=DocumentMetadata(), quality_score=0.4
    )
    mock_grobid_extractor.extract_pdf.return_value = low_quality_doc
    mock_fallback_extractor.extract_pdf.return_value = fallback_doc

    result = await hybrid_extractor.extract_pdf("dummy.pdf")

    assert result == fallback_doc
    mock_grobid_extractor.extract_pdf.assert_called_once_with("dummy.pdf")
    mock_fallback_extractor.extract_pdf.assert_called_once_with("dummy.pdf")


@pytest.mark.asyncio
async def test_falls_back_on_grobid_failure(
    hybrid_extractor, mock_grobid_extractor, mock_fallback_extractor
):
    """Test that the fallback extractor is used when GROBID raises an exception."""
    fallback_doc = ExtractedDocument(
        text="Fallback document text", metadata=DocumentMetadata(), quality_score=0.4
    )
    mock_grobid_extractor.extract_pdf.side_effect = ValueError("GROBID server exploded")
    mock_fallback_extractor.extract_pdf.return_value = fallback_doc

    result = await hybrid_extractor.extract_pdf("dummy.pdf")

    assert result == fallback_doc
    mock_grobid_extractor.extract_pdf.assert_called_once_with("dummy.pdf")
    mock_fallback_extractor.extract_pdf.assert_called_once_with("dummy.pdf")
