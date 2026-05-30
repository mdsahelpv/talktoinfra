"""LangGraph state graph for multi-step agent orchestration."""

from langgraph.graph import StateGraph, START
from langgraph.checkpoint.memory import MemorySaver

from src.core.state import ConversationState
from src.core.agent_engine import AgentEngine


def build_conversation_graph() -> StateGraph:
    engine = AgentEngine()
    builder = StateGraph(ConversationState)

    async def process_node(state: ConversationState) -> dict:
        result = await engine.process_message(
            session_id=state.get("session_id", ""),
            message=state.get("user_message", ""),
            user_id=state.get("user_id", ""),
        )
        return {
            "response": result["content"],
            "tool_calls": result["tool_calls"],
            "requires_approval": result["requires_approval"],
            "approval_id": result["approval_id"],
            "iteration": state.get("iteration", 0) + 1,
        }

    builder.add_node("process", process_node)
    builder.add_edge(START, "process")
    builder.add_conditional_edges(
        "process",
        lambda s: "approve" if s.get("requires_approval") else "respond",
    )
    builder.set_entry_point("process")

    checkpointer = MemorySaver()
    return builder.compile(checkpointer=checkpointer)
