"""Anthropic Claude LLM provider."""

from anthropic import AsyncAnthropic

from src.config import settings
from src.llm.provider import LLMProvider


class AnthropicProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncAnthropic(api_key=settings.anthropic_api_key) if settings.anthropic_api_key else None
        self.model = settings.anthropic_model

    def name(self) -> str:
        return "anthropic"

    async def chat_completion(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        context: str | None = None,
    ) -> dict:
        if not self.client:
            return self._fallback()

        formatted = []
        for msg in messages[-10:]:
            role = "user" if msg.get("role") in ("user", "system") else "assistant"
            formatted.append({"role": role, "content": msg.get("content", "")})

        kwargs = {
            "model": self.model,
            "system": system_prompt + ("\n\nContext:\n" + context if context else ""),
            "messages": formatted if formatted else [{"role": "user", "content": "Hello"}],
            "max_tokens": 4096,
        }

        if tools:
            kwargs["tools"] = [
                {
                    "name": t["name"],
                    "description": t["description"],
                    "input_schema": t["parameters"],
                }
                for t in tools
            ]

        try:
            response = await self.client.messages.create(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            return {"content": f"⚠️ Anthropic error: {e}", "tool_calls": []}

    def _parse_response(self, response) -> dict:
        content = ""
        tool_calls = []

        for block in response.content:
            if block.type == "text":
                content += block.text
            elif block.type == "tool_use":
                tool_calls.append({
                    "action": block.name,
                    "parameters": block.input if hasattr(block, "input") else {},
                })

        return {"content": content, "tool_calls": tool_calls}

    def _fallback(self) -> dict:
        return {
            "content": (
                "Anthropic is not configured. Set TALKTOINFRA_ANTHROPIC_API_KEY "
                "in your environment or use a different provider."
            ),
            "tool_calls": [],
        }
