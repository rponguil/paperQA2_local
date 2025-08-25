import pytest
import pytest_asyncio
import aiohttp
from unittest.mock import AsyncMock, patch, MagicMock

from paperqa2_local.llm.local_llm import LocalLLMManager, LocalLLMConfig


@pytest.fixture
def llm_config():
    """Provides a default LocalLLMConfig for testing."""
    return LocalLLMConfig(base_url="http://mock-ollama:11434")


@pytest_asyncio.fixture
async def manager(llm_config):
    """Provides a LocalLLMManager instance and ensures it's closed after tests."""
    m = LocalLLMManager(llm_config)
    yield m
    await m.close()


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_generate_response_success(mock_post, manager):
    """Test successful response generation from the LLM."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(
        return_value={"response": "The sky is blue because of Rayleigh scattering."}
    )
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value.__aenter__.return_value = mock_response

    prompt = "Why is the sky blue?"
    response = await manager.generate_response(prompt)

    assert response == "The sky is blue because of Rayleigh scattering."
    called_url = mock_post.call_args.args[0]
    assert "api/generate" in called_url
    called_payload = mock_post.call_args.kwargs["json"]
    assert called_payload["prompt"] == prompt


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_embed_text_success(mock_post, manager):
    """Test successful text embedding from the LLM."""
    mock_response = AsyncMock()
    mock_response.status = 200
    mock_response.json = AsyncMock(return_value={"embedding": [0.1, 0.2, 0.3, 0.4]})
    mock_response.raise_for_status = MagicMock()
    mock_post.return_value.__aenter__.return_value = mock_response

    text_to_embed = "This is a test sentence."
    embedding = await manager.embed_text(text_to_embed)

    assert embedding == [0.1, 0.2, 0.3, 0.4]
    called_url = mock_post.call_args.args[0]
    assert "api/embeddings" in called_url
    called_payload = mock_post.call_args.kwargs["json"]
    assert called_payload["prompt"] == text_to_embed


@pytest.mark.asyncio
@patch("aiohttp.ClientSession.post")
async def test_llm_api_failure_raises_connection_error(mock_post, manager):
    """Test that an API error raises a ConnectionError."""
    mock_response = AsyncMock()
    mock_response.status = 500
    # raise_for_status is a sync method, so it needs a sync mock.
    mock_response.raise_for_status = MagicMock(
        side_effect=aiohttp.ClientResponseError(
            request_info=MagicMock(),
            history=(),
            status=500,
            message="Internal Server Error",
        )
    )
    mock_post.return_value.__aenter__.return_value = mock_response

    with pytest.raises(ConnectionError, match="Failed to connect to LLM provider"):
        await manager.generate_response("Any prompt")


@pytest.mark.asyncio
async def test_get_session_creation(manager):
    """Test that the aiohttp session is created lazily."""
    assert manager._session is None
    session1 = await manager._get_session()
    assert isinstance(session1, aiohttp.ClientSession)
    assert not session1.closed
    session2 = await manager._get_session()
    assert session1 is session2


@pytest.mark.asyncio
async def test_close_session(manager):
    """Test that the close method correctly closes the session."""
    session = await manager._get_session()
    assert not session.closed
    await manager.close()
    assert session.closed
    await manager.close()
    assert session.closed
