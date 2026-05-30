"""High-level chat completion helper."""

from src.llm.provider import LLMProvider


async def build_chat_completion(
    provider: LLMProvider,
    system_prompt: str,
    messages: list,
    context: str = "",
    tools: list[dict] | None = None,
) -> dict:
    return await provider.chat_completion(
        system_prompt=system_prompt,
        messages=[{"role": m.role, "content": m.content} for m in messages],
        tools=tools,
        context=context,
    )
