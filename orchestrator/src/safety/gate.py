"""Safety gate — three-tier permission system.

Tiers:
- READ: Auto-execute. Safe by definition.
- MUTATE: Requires HITL approval per session.
- DESTRUCTIVE: Requires fresh HITL approval every time. Never remembered.
"""

from shared.python.models.action import ActionDefinition, PermissionTier


class SafetyGate:
    def __init__(self):
        self._session_approvals: dict[str, set[str]] = {}

    async def check(self, action: ActionDefinition, parameters: dict) -> tuple[bool, str]:
        """Check if an action is allowed based on its tier.

        Returns (allowed, reason).
        """
        match action.tier:
            case PermissionTier.READ:
                return True, "Read action — auto-approved"

            case PermissionTier.MUTATE:
                return False, "Mutation requires human approval"

            case PermissionTier.DESTRUCTIVE:
                return False, "Destructive action requires fresh human approval every time"

            case _:
                return False, f"Unknown permission tier: {action.tier}"

    def mark_approved(self, session_id: str, action_name: str, tier: PermissionTier) -> None:
        if tier == PermissionTier.MUTATE:
            if session_id not in self._session_approvals:
                self._session_approvals[session_id] = set()
            self._session_approvals[session_id].add(action_name)

    def is_approved_in_session(self, session_id: str, action_name: str, tier: PermissionTier) -> bool:
        if tier == PermissionTier.READ:
            return True
        if tier == PermissionTier.DESTRUCTIVE:
            return False
        return action_name in self._session_approvals.get(session_id, set())
