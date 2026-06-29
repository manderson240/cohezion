"""Client for interacting with Ollama API."""

import logging

import httpx


logger = logging.getLogger(__name__)


class OllamaClient:
    """Client for Ollama model API."""

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 30):
        """Initialize Ollama client.

        Args:
            base_url: Base URL for Ollama API
            timeout: Request timeout in seconds
        """
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._client: httpx.AsyncClient | None = None

    async def _get_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(timeout=self.timeout)
        return self._client

    async def query(
        self, prompt: str, model: str = "mistral", temperature: float = 0.7
    ) -> str:
        """Execute a query against an Ollama model.

        Args:
            prompt: The prompt to send to the model
            model: Model name to use
            temperature: Temperature for generation (0.0-1.0)

        Returns:
            Generated text response
        """
        try:
            client = await self._get_client()
            url = f"{self.base_url}/api/generate"

            response = await client.post(
                url,
                json={
                    "model": model,
                    "prompt": prompt,
                    "temperature": temperature,
                    "stream": False,
                },
            )
            response.raise_for_status()

            data = response.json()
            return data.get("response", "")

        except Exception as e:
            logger.error(f"Query failed: {e}")
            raise

    async def embed(
        self, texts: list[str], model: str = "nomic-embed-text-v2-moe-GGUF"
    ) -> list[list[float]]:
        """Generate embeddings for texts.

        Args:
            texts: List of text strings to embed
            model: Embedding model to use

        Returns:
            List of embedding vectors
        """
        try:
            client = await self._get_client()
            # lemonade OmniRouter is OpenAI-compatible: /v1/embeddings, batched input
            url = f"{self.base_url}/v1/embeddings"
            response = await client.post(
                url,
                json={"model": model, "input": texts},
            )
            response.raise_for_status()
            data = response.json()
            return [d.get("embedding", []) for d in data.get("data", [])]

        except Exception as e:
            logger.error(f"Embed failed: {e}")
            raise

    async def status(self) -> dict:
        """Get Ollama service status and available models.

        Returns:
            Dictionary with status information
        """
        try:
            client = await self._get_client()
            url = f"{self.base_url}/api/tags"

            response = await client.get(url)
            response.raise_for_status()

            data = response.json()
            return {
                "status": "healthy",
                "models": data.get("models", []),
            }

        except Exception as e:
            logger.error(f"Status check failed: {e}")
            return {
                "status": "unhealthy",
                "error": str(e),
            }

    async def close(self) -> None:
        """Close the HTTP client."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self):
        """Context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        await self.close()
