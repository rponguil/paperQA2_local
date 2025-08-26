import pytest
import pytest_asyncio
from unittest.mock import AsyncMock, MagicMock
import numpy as np

from paperqa2_local.rag.enhanced_docs import EnhancedDocs, PQASession, Chunk
from paperqa2_local.core.base import ExtractedDocument, DocumentMetadata, DocumentSection


@pytest.fixture
def mock_extractor():
    """Provides a mock HybridExtractor."""
    return AsyncMock()


@pytest.fixture
def mock_llm_manager():
    """Provides a mock LocalLLMManager with a consistent embedding dimension."""
    mock = AsyncMock()
    # Simulate a 128-dimensional embedding vector
    mock.embed_text.return_value = np.random.rand(128).tolist()
    return mock


@pytest.fixture
def sample_extracted_doc():
    """A sample ExtractedDocument object for use in tests."""
    return ExtractedDocument(
        text="Full document text...",
        metadata=DocumentMetadata(title="Test Doc", abstract="This is the abstract."),
        sections=[
            DocumentSection(title="1. Introduction", text="This is the introduction."),
            DocumentSection(title="2. Conclusion", text="This is the conclusion."),
        ],
        quality_score=0.9,
    )


@pytest.mark.asyncio
async def test_add_pdf_full_pipeline(
    mock_extractor, mock_llm_manager, sample_extracted_doc
):
    """
    Tests the full add_pdf pipeline: extraction, chunking, embedding, and indexing.
    """
    # Arrange
    mock_extractor.extract_pdf.return_value = sample_extracted_doc
    docs = EnhancedDocs(extractor=mock_extractor, llm_manager=mock_llm_manager)
    pdf_path = "test_document.pdf"

    # Act
    added_doc = await docs.add_pdf(pdf_path)

    # Assert
    # 1. Extractor was called correctly
    mock_extractor.extract_pdf.assert_called_once_with(pdf_path)

    # 2. LLM Manager was called for each chunk (abstract + 2 sections)
    assert mock_llm_manager.embed_text.call_count == 3
    # Check that it was called with the correct text
    mock_llm_manager.embed_text.assert_any_call("This is the abstract.")
    mock_llm_manager.embed_text.assert_any_call("This is the conclusion.")

    # 3. Document metadata was stored correctly
    assert pdf_path in docs.documents
    assert docs.documents[pdf_path] is added_doc
    assert added_doc.metadata["title"] == "Test Doc"

    # 4. Chunks were created and stored
    assert len(docs.chunks) == 3
    assert docs.chunks[0].doc_key == pdf_path
    assert docs.chunks[0].section_title == "Abstract"
    assert docs.chunks[1].section_title == "1. Introduction"

    # 5. FAISS index was initialized and populated
    assert docs.index is not None
    assert docs.index.ntotal == 3
    assert docs.embedding_dim == 128  # Based on the mock embedding


@pytest.mark.asyncio
async def test_add_pdf_already_exists(mock_extractor, mock_llm_manager):
    """Tests that an existing document is not re-processed."""
    # Arrange
    docs = EnhancedDocs(extractor=mock_extractor, llm_manager=mock_llm_manager)
    pdf_path = "existing_doc.pdf"
    docs.documents[pdf_path] = "dummy_document_object" # Pre-populate

    # Act
    await docs.add_pdf(pdf_path)

    # Assert
    # The extractor and LLM manager should not have been called
    mock_extractor.extract_pdf.assert_not_called()
    mock_llm_manager.embed_text.assert_not_called()


@pytest_asyncio.fixture
async def populated_docs(mock_extractor, mock_llm_manager, sample_extracted_doc):
    """Provides an EnhancedDocs instance with one document already added."""
    mock_extractor.extract_pdf.return_value = sample_extracted_doc
    docs = EnhancedDocs(extractor=mock_extractor, llm_manager=mock_llm_manager)
    await docs.add_pdf("test_document.pdf")
    # Reset mocks to clear the calls from the add_pdf setup
    mock_extractor.reset_mock()
    mock_llm_manager.reset_mock()
    return docs


@pytest.mark.asyncio
async def test_query_pipeline(populated_docs, mock_llm_manager):
    """Test the full query pipeline from question to answer."""
    # Arrange
    docs = populated_docs
    question = "What is the conclusion?"

    # Mock the embedding for the question
    mock_llm_manager.embed_text.return_value = np.random.rand(128).tolist()

    # Mock the final answer generation
    final_answer = "The conclusion is that RAG is great."
    mock_llm_manager.generate_response.return_value = final_answer

    # Mock the FAISS search result to return the index of the "Conclusion" chunk
    mock_search_indices = np.array([[2, 1, 0]], dtype=np.int64)
    mock_search_distances = np.array([[0.1, 0.5, 0.8]], dtype=np.float32)
    docs.index.search = MagicMock(
        return_value=(mock_search_distances, mock_search_indices)
    )

    # Act
    result_session = await docs.query(question, k=3)

    # Assert
    # 1. Question embedding was generated
    mock_llm_manager.embed_text.assert_called_once_with(question)

    # 2. Index was searched correctly
    docs.index.search.assert_called_once()
    # The `k` argument in `faiss.search` is positional, not keyword
    assert docs.index.search.call_args.args[1] == 3

    # 3. Final response was generated with a prompt containing the right context
    mock_llm_manager.generate_response.assert_called_once()
    prompt_arg = mock_llm_manager.generate_response.call_args[0][0]
    assert "Context:" in prompt_arg
    assert "This is the conclusion." in prompt_arg  # The text of the top retrieved chunk
    assert "This is the introduction." in prompt_arg # Text of the second chunk

    # 4. PQASession is correct
    assert isinstance(result_session, PQASession)
    assert result_session.question == question
    assert result_session.answer == final_answer
    assert len(result_session.contexts) == 3
    assert result_session.contexts[0].section_title == "2. Conclusion"
