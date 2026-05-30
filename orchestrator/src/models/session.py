from datetime import datetime, timezone
from uuid import uuid4

from shared.python.models.chat import ChatSession, ChatMessage


class SessionManager:
    _sessions: dict[str, ChatSession] = {}

    async def create(self, user_id: str = "", description: str = "") -> ChatSession:
        session = ChatSession(
            id=str(uuid4()),
            user_id=user_id,
            description=description,
        )
        self._sessions[session.id] = session
        return session

    async def get(self, session_id: str) -> ChatSession | None:
        return self._sessions.get(session_id)

    async def get_or_create(self, session_id: str, user_id: str = "") -> ChatSession:
        if session_id and session_id in self._sessions:
            session = self._sessions[session_id]
            session.last_active = datetime.now(timezone.utc).isoformat()
            return session
        return await self.create(user_id, f"Session {len(self._sessions) + 1}")

    async def list(self, user_id: str = "", limit: int = 20, offset: int = 0) -> list[dict]:
        sessions = list(self._sessions.values())
        if user_id:
            sessions = [s for s in sessions if s.user_id == user_id]
        sessions.sort(key=lambda s: s.last_active, reverse=True)
        return [
            {
                "id": s.id,
                "user_id": s.user_id,
                "description": s.description,
                "message_count": len(s.messages),
                "created_at": s.created_at,
                "last_active": s.last_active,
                "status": s.status,
            }
            for s in sessions[offset : offset + limit]
        ]

    async def add_message(self, session_id: str, message: ChatMessage) -> None:
        session = self._sessions.get(session_id)
        if session:
            session.messages.append(message)
            session.last_active = datetime.now(timezone.utc).isoformat()
