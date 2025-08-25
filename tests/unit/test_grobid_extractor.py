import pytest
from unittest.mock import patch

from paperqa2_local.core.base import ExtractedDocument
from paperqa2_local.extractors.grobid_extractor import GrobidExtractor


@pytest.fixture
def sample_tei_xml():
    """Provides the content of the sample TEI XML file."""
    with open("tests/fixtures/sample_tei.xml", "r", encoding="utf-8") as f:
        return f.read()


@pytest.mark.asyncio
@patch("paperqa2_local.extractors.grobid_extractor.GrobidClient")
async def test_extract_pdf_success(MockGrobidClient, sample_tei_xml):
    """Test successful PDF extraction and parsing of a complete document."""
    mock_instance = MockGrobidClient.return_value
    mock_instance.process.return_value = (
        200,
        "application/xml",
        sample_tei_xml.encode("utf-8"),
    )

    extractor = GrobidExtractor()
    pdf_path = "tests/fixtures/sample.pdf"  # The actual PDF content doesn't matter due to mocking
    extracted_doc = await extractor.extract_pdf(pdf_path)

    # Top-level assertions
    assert isinstance(extracted_doc, ExtractedDocument)
    assert extracted_doc.extraction_method == "grobid"
    assert extracted_doc.quality_score >= 0.9

    # Metadata assertions
    meta = extracted_doc.metadata
    assert meta.title == "A Comprehensive Analysis of Modern RAG Systems"
    assert len(meta.authors) == 2
    assert meta.authors[0].name == "Jane Doe"
    assert meta.authors[1].name == "John Smith"
    assert "This paper presents a detailed analysis" in meta.abstract
    assert meta.doi == "10.1234/jaair.2023.5678"
    assert meta.year == 2023
    assert "RAG" in meta.keywords and "LLM" in meta.keywords

    # Content structure assertions
    assert len(extracted_doc.sections) == 4
    assert extracted_doc.sections[0].title == "1. Introduction"
    assert "The field of Natural Language Processing" in extracted_doc.sections[0].text
    assert extracted_doc.sections[3].title == "4. Conclusion"

    assert len(extracted_doc.references) == 2
    assert "Retrieval-Augmented Generation" in extracted_doc.references[0].text

    assert len(extracted_doc.figures) == 1
    assert "Performance comparison" in extracted_doc.figures[0].caption

    # Markdown text assertions
    assert "## Abstract" in extracted_doc.text
    assert "## 1. Introduction" in extracted_doc.text
    assert "## 4. Conclusion" in extracted_doc.text
    assert "We conclude that RAG systems are a vital component" in extracted_doc.text


@pytest.mark.asyncio
@patch("paperqa2_local.extractors.grobid_extractor.GrobidClient")
async def test_extract_pdf_grobid_failure(MockGrobidClient):
    """Test handling of a GROBID server failure during processing."""
    mock_instance = MockGrobidClient.return_value
    mock_instance.process.side_effect = Exception("GROBID server is down")

    extractor = GrobidExtractor()
    pdf_path = "tests/fixtures/sample.pdf"

    with pytest.raises(IOError, match="Failed to process PDF with GROBID"):
        await extractor.extract_pdf(pdf_path)


@pytest.mark.asyncio
@patch("paperqa2_local.extractors.grobid_extractor.GrobidClient")
async def test_extract_pdf_empty_response(MockGrobidClient):
    """Test handling of an empty but successful response from GROBID."""
    mock_instance = MockGrobidClient.return_value
    mock_instance.process.return_value = (200, "application/xml", b"")

    extractor = GrobidExtractor()
    pdf_path = "tests/fixtures/sample.pdf"

    with pytest.raises(
        ValueError, match="GROBID processing failed, returned empty response."
    ):
        await extractor.extract_pdf(pdf_path)

@patch("paperqa2_local.extractors.grobid_extractor.GrobidClient")
def test_tei_to_markdown_structure(MockGrobidClient, sample_tei_xml):
    """Test the TEI to Markdown conversion logic specifically."""
    from lxml import etree

    extractor = GrobidExtractor()
    parser = etree.XMLParser(remove_blank_text=True, recover=True)
    root = etree.fromstring(sample_tei_xml.encode("utf-8"), parser)

    markdown_text = extractor.tei_to_markdown(root)

    # Check for key structural elements
    assert markdown_text.startswith("## Abstract")
    assert "\n\n## 1. Introduction\n\n" in markdown_text
    assert "\n\n## 2. Methodology\n\n" in markdown_text
    assert "The iterative RAG model demonstrated" in markdown_text
    # Ensure inline references are not included in the main text body
    assert "[b0]" not in markdown_text
