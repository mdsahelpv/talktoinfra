"""Core agent engine — processes user messages with policy + guardrails + audit."""

import json
import asyncio
from datetime import datetime, timezone
from typing import AsyncGenerator
from uuid import uuid4

from src.config import settings
from src.llm.registry import LLMRegistry
from src.llm.completions import build_chat_completion
from src.core.state import ConversationState
from src.core.router import IntentRouter
from src.safety.gate import SafetyGate
from src.safety.redactor import Redactor
from src.safety.guardrails import guardrail_engine
from src.policy.engine import policy_engine, PolicyDecision
from src.knowledge.retriever import KnowledgeRetriever
from src.models.session import SessionManager
from src.storage.repository import AuditRepository
from shared.python.models.chat import ChatMessage
from shared.python.catalog import build_default_catalog


class AgentEngine:
    def __init__(self):
        self.llm = LLMRegistry.get_provider(settings.default_llm_provider)
        self.catalog = build_default_catalog()
        self.router = IntentRouter(self.catalog)
        self.safety_gate = SafetyGate()
        self.redactor = Redactor()
        self.knowledge = KnowledgeRetriever()
        self.sessions = SessionManager()
        self.audit = AuditRepository()
        self._pending_approvals: dict[str, dict] = {}
        self._system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        tools_desc = []
        for action in self.catalog.actions.values():
            params = ", ".join(f"{p.name}: {p.type}" for p in action.parameters)
            tools_desc.append(
                f"  - {action.name} ({action.tier.value}, {action.category.value}): "
                f"{action.description} [{params}]"
            )
        return f"""You are TalkToInfra, an AI infrastructure copilot.
You help IT/DevOps teams manage their infrastructure through natural language.

Available tools:
{chr(10).join(tools_desc)}

Rules:
1. Use the appropriate tool(s) to answer the user's question.
2. For READ-tier tools, call them directly.
3. For MUTATE/DESTRUCTIVE tools, explain what you want to do and wait for approval.
4. If you don't have the right tool, explain what the user can do instead.
5. Keep answers concise and actionable.
6. Use knowledge from past incidents and runbooks when relevant."""

    async def process_message(
        self, session_id: str, message: str, user_id: str = "", org_id: str = "", user_roles: list[str] | None = None
    ) -> dict:
        user_roles = user_roles or ["viewer"]
        session = await self.sessions.get(session_id)
        context = ""
        if session:
            context = await self.knowledge.get_relevant_context(message)

        user_msg = ChatMessage(role="user", content=message)
        await self.sessions.add_message(session_id, user_msg)

        response = await build_chat_completion(
            provider=self.llm,
            system_prompt=self._system_prompt,
            messages=session.messages[-10:] if session else [],
            context=context,
            tools=self._get_tool_definitions(),
        )

        tool_calls = response.get("tool_calls", [])
        requires_approval = False
        approval_id = None

        if tool_calls:
            for tc in tool_calls:
                action = self.catalog.get(tc["action"])
                if not action:
                    continue

                # 1. Content guardrails — scan tool args
                guard = guardrail_engine.check_tool_args(tc["action"], tc.get("parameters", {}))
                tc["parameters"] = guard.redacted_args or tc.get("parameters", {})

                # 2. Policy engine check
                policy_result = policy_engine.evaluate({
                    "tier": action.tier.value,
                    "tool_name": tc["action"],
                    "tool_args": tc.get("parameters", {}),
                    "user_roles": user_roles,
                })

                # 3. Log to immutable audit
                audit_id = await self.audit.log({
                    "session_id": session_id,
                    "user_id": user_id,
                    "org_id": org_id,
                    "action": tc["action"],
                    "tool_name": tc["action"],
                    "tool_args": tc.get("parameters", {}),
                    "tier": action.tier.value,
                    "approved": False,
                    "status": "pending" if policy_result.decision != PolicyDecision.ALLOW else "executed",
                    "parameters": {"guard_flags": guard.flags, "policy_reason": policy_result.reason},
                })

                if policy_result.decision == PolicyDecision.DENY:
                    return {
                        "content": f"Cannot execute {tc['action']}: {policy_result.reason}",
                        "tool_calls": [],
                        "requires_approval": False,
                        "approval_id": None,
                        "audit_id": audit_id,
                    }

                if policy_result.decision == PolicyDecision.REQUIRE_APPROVAL:
                    requires_approval = True
                    approval_id = str(uuid4())
                    self._pending_approvals[approval_id] = {
                        "action": tc["action"],
                        "parameters": tc["parameters"],
                        "tier": action.tier.value,
                        "session_id": session_id,
                        "user_id": user_id,
                        "org_id": org_id,
                        "audit_id": audit_id,
                        "status": "pending",
                    }
                    break

            if not requires_approval:
                await self._execute_tool_calls(tool_calls, session_id, user_id, org_id)

        assistant_msg = ChatMessage(
            role="assistant",
            content=response.get("content", ""),
            tool_calls=tool_calls,
        )
        await self.sessions.add_message(session_id, assistant_msg)

        return {
            "content": response.get("content", ""),
            "tool_calls": tool_calls,
            "requires_approval": requires_approval,
            "approval_id": approval_id,
        }

    async def process_message_stream(
        self, session_id: str, message: str, user_id: str = "", org_id: str = "", user_roles: list[str] | None = None
    ) -> AsyncGenerator[dict, None]:
        user_roles = user_roles or ["viewer"]
        session = await self.sessions.get(session_id)
        context = ""
        if session:
            context = await self.knowledge.get_relevant_context(message)

        user_msg = ChatMessage(role="user", content=message)
        await self.sessions.add_message(session_id, user_msg)

        yield {"type": "thinking", "content": "Analyzing your request..."}

        response = await build_chat_completion(
            provider=self.llm,
            system_prompt=self._system_prompt,
            messages=session.messages[-10:] if session else [],
            context=context,
            tools=self._get_tool_definitions(),
        )

        content = response.get("content", "")
        tool_calls = response.get("tool_calls", [])

        if content:
            yield {"type": "text", "content": content}

        if tool_calls:
            requires_approval = False
            for tc in tool_calls:
                action = self.catalog.get(tc["action"])
                if not action:
                    continue

                guard = guardrail_engine.check_tool_args(tc["action"], tc.get("parameters", {}))
                tc["parameters"] = guard.redacted_args or tc.get("parameters", {})

                policy_result = policy_engine.evaluate({
                    "tier": action.tier.value,
                    "tool_name": tc["action"],
                    "tool_args": tc.get("parameters", {}),
                    "user_roles": user_roles,
                })

                audit_id = await self.audit.log({
                    "session_id": session_id,
                    "user_id": user_id,
                    "org_id": org_id,
                    "action": tc["action"],
                    "tool_name": tc["action"],
                    "tool_args": tc.get("parameters", {}),
                    "tier": action.tier.value,
                    "approved": False,
                    "status": "pending" if policy_result.decision != PolicyDecision.ALLOW else "executed",
                    "parameters": {"guard_flags": guard.flags, "policy_reason": policy_result.reason},
                })

                if policy_result.decision == PolicyDecision.DENY:
                    yield {"type": "error", "content": f"Cannot execute {tc['action']}: {policy_result.reason}"}
                    continue

                if policy_result.decision == PolicyDecision.REQUIRE_APPROVAL:
                    requires_approval = True
                    approval_id = str(uuid4())
                    self._pending_approvals[approval_id] = {
                        "action": tc["action"],
                        "parameters": tc["parameters"],
                        "tier": action.tier.value,
                        "session_id": session_id,
                        "user_id": user_id,
                        "org_id": org_id,
                        "audit_id": audit_id,
                        "status": "pending",
                    }
                    yield {
                        "type": "approval_required",
                        "approval_id": approval_id,
                        "action": tc["action"],
                        "parameters": tc["parameters"],
                        "reason": content,
                    }
                    continue

                yield {"type": "tool_call", "action": tc["action"], "parameters": tc["parameters"]}
                result = await self._execute_single_tool(tc, user_id, org_id)
                yield {"type": "tool_result", "action": tc["action"], **result}

        yield {"type": "final", "content": content}

    async def handle_approval(
        self, approval_id: str, approved: bool, approved_by: str, note: str = ""
    ) -> str | None:
        pending = self._pending_approvals.pop(approval_id, None)
        if not pending:
            return None
        if not approved:
            await self.audit.log({
                "session_id": pending["session_id"],
                "user_id": pending["user_id"],
                "org_id": pending.get("org_id", ""),
                "action": pending["action"],
                "tier": pending["tier"],
                "approved": False,
                "approved_by": approved_by,
                "approval_note": note,
                "status": "denied",
                "parameters": {},
            })
            return "denied"
        await self.audit.update_approval(pending.get("audit_id", ""), approved_by, note)
        tool_calls = [{"action": pending["action"], "parameters": pending["parameters"]}]
        await self._execute_tool_calls(tool_calls, pending["session_id"], pending["user_id"], pending.get("org_id", ""))
        return "executed"

    async def _execute_tool_calls(self, tool_calls: list[dict], session_id: str, user_id: str = "", org_id: str = "") -> None:
        for tc in tool_calls:
            result = await self._execute_single_tool(tc, user_id, org_id)
            msg = ChatMessage(
                role="assistant",
                content=f"Executed {tc['action']}: {result.get('output', result.get('error', ''))}",
                tool_results=[result],
            )
            await self.sessions.add_message(session_id, msg)

    async def _execute_single_tool(self, tool_call: dict, user_id: str = "", org_id: str = "") -> dict:
        action_name = tool_call["action"]
        action = self.catalog.get(action_name)
        if not action:
            return {"success": False, "error": f"Unknown action: {action_name}"}

        allowed, reason = await self.safety_gate.check(action, tool_call.get("parameters", {}))
        if not allowed:
            return {"success": False, "error": reason}

        result = await self.router.route(action, tool_call.get("parameters", {}))

        await self.audit.log({
            "session_id": tool_call.get("_session_id", ""),
            "user_id": user_id,
            "org_id": org_id,
            "action": action_name,
            "tool_name": action_name,
            "tool_args": tool_call.get("parameters", {}),
            "tier": action.tier.value,
            "approved": True,
            "status": "completed" if result.get("success", False) else "failed",
            "result": result.get("output", result.get("error", "")),
            "duration_ms": result.get("duration_ms", 0),
            "parameters": {},
        })

        return result

    def _get_tool_definitions(self) -> list[dict]:
        tools = []
        for action in self.catalog.actions.values():
            tool = {
                "name": action.name,
                "description": action.description,
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            }
            for p in action.parameters:
                tool["parameters"]["properties"][p.name] = {
                    "type": p.type,
                    "description": p.description,
                }
                if p.required:
                    tool["parameters"]["required"].append(p.name)
            tools.append(tool)
        return tools
