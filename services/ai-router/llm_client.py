"""
Ollama LLM client for text generation and streaming.
"""

import json
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx
import structlog

logger = structlog.get_logger()


class OllamaClient:
    """Client for Ollama LLM server."""

    def __init__(
        self,
        host: str,
        model_chat: str,
        model_code: str,
        timeout: float = 120.0,
    ):
        """Initialize Ollama client.

        Args:
            host: Ollama server URL
            model_chat: Model name for chat/general tasks
            model_code: Model name for code generation
            timeout: Request timeout in seconds
        """
        self.host = host.rstrip("/")
        self.model_chat = model_chat
        self.model_code = model_code
        self.timeout = timeout

        self.client = httpx.AsyncClient(
            base_url=self.host,
            timeout=httpx.Timeout(timeout),
        )

    async def health_check(self) -> Dict[str, Any]:
        """Check Ollama server health.

        Returns:
            Health status dict

        Raises:
            ConnectionError: If Ollama is unreachable
        """
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()

            data = response.json()
            models = [m.get("name", m.get("model")) for m in data.get("models", [])]

            return {
                "status": "healthy",
                "host": self.host,
                "available_models": models,
                "default_chat_model": self.model_chat,
                "default_code_model": self.model_code,
            }

        except httpx.HTTPError as e:
            logger.error("ollama_health_check_failed", error=str(e))
            raise ConnectionError(f"Ollama health check failed: {str(e)}")

    async def generate(
        self,
        prompt: str,
        model_type: str = "chat",
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Generate text from prompt.

        Args:
            prompt: Input prompt
            model_type: "chat" or "code"
            system: System message/prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens to generate
            options: Additional Ollama options

        Returns:
            Generated text
        """
        model = self.model_chat if model_type == "chat" else self.model_code

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            "temperature": temperature,
        }

        if system:
            payload["system"] = system

        if max_tokens:
            payload["max_tokens"] = max_tokens

        if options:
            payload["options"] = options

        try:
            logger.info(
                "llm_generation_started",
                model=model,
                prompt_length=len(prompt),
            )

            response = await self.client.post(
                "/api/generate",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            generated_text = data.get("response", "").strip()

            logger.info(
                "llm_generation_completed",
                model=model,
                prompt_length=len(prompt),
                response_length=len(generated_text),
            )

            return generated_text

        except httpx.HTTPError as e:
            logger.error(
                "llm_generation_failed",
                error=str(e),
                model=model,
            )
            raise ConnectionError(f"Failed to generate from Ollama: {str(e)}")

    async def generate_stream(
        self,
        prompt: str,
        model_type: str = "chat",
        system: Optional[str] = None,
        temperature: float = 0.7,
    ) -> AsyncIterator[str]:
        """Generate text with streaming response.

        Args:
            prompt: Input prompt
            model_type: "chat" or "code"
            system: System message/prompt
            temperature: Sampling temperature

        Yields:
            Text chunks as they are generated
        """
        model = self.model_chat if model_type == "chat" else self.model_code

        payload: Dict[str, Any] = {
            "model": model,
            "prompt": prompt,
            "stream": True,
            "temperature": temperature,
        }

        if system:
            payload["system"] = system

        try:
            logger.info(
                "llm_stream_started",
                model=model,
                prompt_length=len(prompt),
            )

            async with self.client.stream(
                "POST",
                "/api/generate",
                json=payload,
            ) as response:
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line:
                        continue

                    try:
                        data = json.loads(line)
                        chunk = data.get("response", "")
                        if chunk:
                            yield chunk

                        # Check if done
                        if data.get("done", False):
                            break

                    except json.JSONDecodeError:
                        continue

            logger.info("llm_stream_completed", model=model)

        except httpx.HTTPError as e:
            logger.error("llm_stream_failed", error=str(e), model=model)
            raise ConnectionError(f"Failed to stream from Ollama: {str(e)}")

    async def chat(
        self,
        messages: List[Dict[str, str]],
        model_type: str = "chat",
        temperature: float = 0.7,
    ) -> str:
        """Send chat messages and get response.

        Args:
            messages: List of message dicts with "role" and "content"
            model_type: "chat" or "code"
            temperature: Sampling temperature

        Returns:
            Assistant's response
        """
        model = self.model_chat if model_type == "chat" else self.model_code

        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            "temperature": temperature,
        }

        try:
            logger.info(
                "llm_chat_started",
                model=model,
                message_count=len(messages),
            )

            response = await self.client.post(
                "/api/chat",
                json=payload,
            )
            response.raise_for_status()

            data = response.json()
            message = data.get("message", {})
            response_text = message.get("content", "").strip()

            logger.info(
                "llm_chat_completed",
                model=model,
                response_length=len(response_text),
            )

            return response_text

        except httpx.HTTPError as e:
            logger.error("llm_chat_failed", error=str(e), model=model)
            raise ConnectionError(f"Failed to chat with Ollama: {str(e)}")

    async def list_models(self) -> List[Dict[str, Any]]:
        """List available models.

        Returns:
            List of model info dicts
        """
        try:
            response = await self.client.get("/api/tags")
            response.raise_for_status()

            data = response.json()
            return data.get("models", [])

        except httpx.HTTPError as e:
            logger.error("list_models_failed", error=str(e))
            raise ConnectionError(f"Failed to list models: {str(e)}")

    async def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama registry.

        Args:
            model_name: Name of the model to pull

        Returns:
            True if successful
        """
        try:
            logger.info("pulling_model", model=model_name)

            response = await self.client.post(
                "/api/pull",
                json={"name": model_name},
            )
            response.raise_for_status()

            return True

        except httpx.HTTPError as e:
            logger.error("pull_model_failed", error=str(e), model=model_name)
            raise

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
