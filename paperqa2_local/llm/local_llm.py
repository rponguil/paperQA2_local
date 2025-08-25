"""
Configuración y manejo de LLMs locales (Ollama, LM Studio).

Soporte para:
- Ollama (configuración automática)
- LM Studio (API compatible OpenAI)
- Detección automática de modelos disponibles
- Rate limiting local
- Fallbacks entre modelos
"""
import aiohttp
from dataclasses import dataclass
from typing import List, Optional


@dataclass
class LocalLLMConfig:
    """Configuration for the LocalLLMManager."""

    provider: str = "ollama"
    base_url: str = "http://localhost:11434"
    default_model: str = "llama3.2:8b"
    embedding_model: str = "mxbai-embed-large"
    timeout: int = 120


class LocalLLMManager:
    """
    Manages local LLMs (Ollama, LM Studio).
    """

    def __init__(self, config: LocalLLMConfig):
        """Inicializar manager con configuración"""
        self.config = config
        self._session: Optional[aiohttp.ClientSession] = None

    async def _get_session(self) -> aiohttp.ClientSession:
        """Lazily create and return the aiohttp client session."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=self.config.timeout)
            self._session = aiohttp.ClientSession(timeout=timeout)
        return self._session

    async def generate_response(self, prompt: str, model_name: str = None) -> str:
        """Generar respuesta con modelo específico o default"""
        session = await self._get_session()
        url = f"{self.config.base_url}/api/generate"
        model = model_name or self.config.default_model
        payload = {"model": model, "prompt": prompt, "stream": False}

        try:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("response", "")
        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to connect to LLM provider at {url}: {e}"
            ) from e

    async def embed_text(self, text: str, model_name: str = None) -> List[float]:
        """Generar embeddings usando modelo local"""
        session = await self._get_session()
        url = f"{self.config.base_url}/api/embeddings"
        model = model_name or self.config.embedding_model
        payload = {"model": model, "prompt": text}

        try:
            async with session.post(url, json=payload) as response:
                response.raise_for_status()
                data = await response.json()
                return data.get("embedding", [])
        except aiohttp.ClientError as e:
            raise ConnectionError(
                f"Failed to connect to LLM provider at {url}: {e}"
            ) from e

    def get_optimal_model_for_task(self, task_type: str) -> str:
        """Seleccionar modelo óptimo para tipo de tarea específica"""
        # Placeholder for future logic to select models based on task
        return self.config.default_model

    async def close(self):
        """Gracefully close the aiohttp client session."""
        if self._session and not self._session.closed:
            await self._session.close()
