"""
Embedding Generator module.
Generates vector embeddings using Ollama.
"""

from typing import List

import httpx
import structlog

logger = structlog.get_logger()


class EmbeddingGenerator:
    """Generates vector embeddings for text."""

    def __init__(self, ollama_host: str, model: str):
        self.ollama_host = ollama_host
        self.model = model
        self.client = httpx.AsyncClient(timeout=60.0)

    async def generate(self, text: str) -> List[float]:
        """Generate embedding for text."""
        try:
            logger.debug("generating_embedding", text_length=len(text))

            response = await self.client.post(
                f"{self.ollama_host}/api/embeddings",
                json={
                    "model": self.model,
                    "prompt": text[:4000],  # Truncate if too long
                },
            )
            response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding", [])

            logger.debug("embedding_generated", dimensions=len(embedding))

            return embedding

        except httpx.HTTPError as e:
            logger.error("embedding_generation_failed", error=str(e))
            # Return zero vector as fallback
            return [0.0] * 768

    async def generate_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts."""
        embeddings = []
        for text in texts:
            embedding = await self.generate(text)
            embeddings.append(embedding)
        return embeddings

    async def health_check(self) -> bool:
        """Check if Ollama is accessible."""
        try:
            response = await self.client.get(f"{self.ollama_host}/api/tags")
            response.raise_for_status()
            return True
        except Exception:
            return False

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
