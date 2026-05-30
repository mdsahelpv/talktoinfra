"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod


class LLMProvider(ABC):
    @abstractmethod
    async def chat_completion(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        context: str | None = None,
    ) -> dict:
        """Send a chat completion request and return the response.

        Returns: {
            "content": str,
            "tool_calls": [{"action": str, "parameters": dict}]
        }
        """
        ...

    @abstractmethod
    def name(self) -> str:
        ...
