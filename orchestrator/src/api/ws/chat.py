import json
import asyncio

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from src.core.agent_engine import AgentEngine
from src.models.session import SessionManager

chat_ws_router = APIRouter()
agent_engine = AgentEngine()
session_manager = SessionManager()


@chat_ws_router.websocket("/ws/chat")
async def websocket_chat(ws: WebSocket):
    await ws.accept()
    session_id = None
    user_id = "ws_user"

    try:
        data = await ws.receive_json()
        session_id = data.get("session_id", "")
        session = await session_manager.get_or_create(session_id, user_id)
        session_id = session.id

        await ws.send_json({"type": "connected", "session_id": session_id})

        async for chunk in agent_engine.process_message_stream(
            session_id=session_id,
            message=data.get("message", ""),
            user_id=user_id,
        ):
            await ws.send_json(chunk)
            if chunk.get("type") == "final":
                break

    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await ws.send_json({"type": "error", "message": str(e)})
        except RuntimeError:
            pass
