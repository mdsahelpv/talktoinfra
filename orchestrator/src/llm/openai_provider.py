"""OpenAI LLM provider."""

import json

from openai import AsyncOpenAI

from src.config import settings
from src.llm.provider import LLMProvider


class OpenAIProvider(LLMProvider):
    def __init__(self):
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if settings.openai_api_key else None
        self.model = settings.openai_model

    def name(self) -> str:
        return "openai"

    async def chat_completion(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        context: str | None = None,
    ) -> dict:
        if not self.client:
            return self._fallback(tools)

        formatted = [{"role": "system", "content": system_prompt}]
        if context:
            formatted.append({"role": "system", "content": f"Context:\n{context}"})

        for msg in messages[-10:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            formatted.append({"role": role, "content": content})

        kwargs = {
            "model": self.model,
            "messages": formatted,
        }

        if tools:
            kwargs["tools"] = [
                {
                    "type": "function",
                    "function": {
                        "name": t["name"],
                        "description": t["description"],
                        "parameters": t["parameters"],
                    },
                }
                for t in tools
            ]
            kwargs["tool_choice"] = "auto"

        try:
            response = await self.client.chat.completions.create(**kwargs)
            return self._parse_response(response)
        except Exception as e:
            return {"content": f"⚠️ OpenAI error: {e}", "tool_calls": []}

    def _parse_response(self, response) -> dict:
        choice = response.choices[0]
        content = choice.message.content or ""
        tool_calls = []

        if choice.message.tool_calls:
            for tc in choice.message.tool_calls:
                try:
                    args = json.loads(tc.function.arguments)
                except json.JSONDecodeError:
                    args = {}
                tool_calls.append({
                    "action": tc.function.name,
                    "parameters": args,
                })

        return {"content": content, "tool_calls": tool_calls}

    def _fallback(self, tools: list[dict] | None = None) -> dict:
        return {
            "content": (
                "OpenAI is not configured. Set TALKTOINFRA_OPENAI_API_KEY "
                "in your environment or use a different provider."
            ),
            "tool_calls": [],
        }
