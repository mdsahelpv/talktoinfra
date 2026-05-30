"""Ollama LLM provider — runs fully local, no data leaves your network."""

import json

import httpx

from src.config import settings
from src.llm.provider import LLMProvider


class OllamaProvider(LLMProvider):
    def __init__(self):
        self.base_url = settings.ollama_base_url
        self.model = settings.ollama_model

    def name(self) -> str:
        return "ollama"

    async def chat_completion(
        self,
        system_prompt: str,
        messages: list[dict],
        tools: list[dict] | None = None,
        context: str | None = None,
    ) -> dict:
        try:
            formatted = [{"role": "system", "content": system_prompt}]
            if context:
                formatted.append({"role": "system", "content": f"Context:\n{context}"})
            for msg in messages[-10:]:
                formatted.append({
                    "role": msg.get("role", "user"),
                    "content": msg.get("content", ""),
                })

            payload = {
                "model": self.model,
                "messages": formatted,
                "stream": False,
            }

            if tools:
                payload["tools"] = [
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

            async with httpx.AsyncClient() as client:
                resp = await client.post(
                    f"{self.base_url}/api/chat",
                    json=payload,
                    timeout=120,
                )
                resp.raise_for_status()
                data = resp.json()

            content = data.get("message", {}).get("content", "")
            tool_calls = []
            for tc in data.get("message", {}).get("tool_calls", []):
                tool_calls.append({
                    "action": tc.get("function", {}).get("name", ""),
                    "parameters": tc.get("function", {}).get("arguments", {}),
                })

            return {"content": content, "tool_calls": tool_calls}

        except Exception as e:
            return {"content": f"⚠️ Ollama error: {e}", "tool_calls": []}
