"""Conversation and incident memory management."""


class ConversationMemory:
    def __init__(self, max_turns: int = 20):
        self.max_turns = max_turns
        self._turns: dict[str, list[dict]] = {}

    def add_turn(self, session_id: str, user_msg: str, assistant_msg: str, tool_calls: list | None = None):
        if session_id not in self._turns:
            self._turns[session_id] = []
        self._turns[session_id].append({
            "user": user_msg,
            "assistant": assistant_msg,
            "tool_calls": tool_calls or [],
        })
        if len(self._turns[session_id]) > self.max_turns:
            self._turns[session_id] = self._turns[session_id][-self.max_turns:]

    def get_history(self, session_id: str) -> list[dict]:
        return self._turns.get(session_id, [])

    def get_context(self, session_id: str, max_tokens: int = 2000) -> str:
        history = self.get_history(session_id)
        lines = []
        for turn in history[-5:]:
            lines.append(f"User: {turn['user']}")
            lines.append(f"Assistant: {turn['assistant']}")
        return "\n".join(lines)
