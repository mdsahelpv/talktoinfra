"""
Approval Chain Manager module.
Manages multi-level approval chains.
"""

from typing import Any, Dict, List, Optional

import structlog

from models import ApprovalResponse, ApprovalChain

logger = structlog.get_logger()


class ApprovalChainManager:
    """Manages multi-level approval chains."""

    def __init__(self):
        # In-memory store - replace with database in production
        self.chains: Dict[str, ApprovalChain] = {}
        self.approval_records: Dict[str, List[Dict[str, Any]]] = {}

        # Initialize default chains
        self._initialize_defaults()

    def _initialize_defaults(self):
        """Initialize default approval chains."""
        # Production deployment chain
        self.chains["production_deploy"] = ApprovalChain(
            chain_id="production_deploy",
            name="Production Deployment",
            description="Multi-level approval for production deployments",
            levels=[
                {
                    "level": 1,
                    "required_approvals": 1,
                    "approver_roles": ["sre-oncall"],
                    "any_of_roles": True,
                },
                {
                    "level": 2,
                    "required_approvals": 1,
                    "approver_roles": ["platform-lead", "engineering-manager"],
                    "any_of_roles": True,
                },
            ],
            conditions={
                "action": ["deploy", "scale"],
                "environment": ["production"],
            },
        )

        # Destructive action chain
        self.chains["destructive"] = ApprovalChain(
            chain_id="destructive",
            name="Destructive Actions",
            description="Approval for destructive actions",
            levels=[
                {
                    "level": 1,
                    "required_approvals": 2,
                    "approver_roles": ["admin", "sre-oncall"],
                    "any_of_roles": True,
                },
            ],
            conditions={
                "action": ["delete", "terminate", "remove"],
            },
        )

        logger.info(
            "approval_chains_initialized",
            chains=list(self.chains.keys()),
        )

    def can_approve(self, approval: ApprovalResponse, user_id: str) -> bool:
        """Check if a user can approve an action."""
        # Direct approver list
        if user_id in approval.approvers:
            return True

        # Check if user has required role
        # In production, query user service for roles
        # For now, assume user_roles from approval

        return False

    def record_approval(self, approval_id: str, user_id: str):
        """Record an approval in the chain."""
        if approval_id not in self.approval_records:
            self.approval_records[approval_id] = []

        self.approval_records[approval_id].append(
            {
                "user_id": user_id,
                "timestamp": "now",  # Would use actual timestamp
            }
        )

        logger.info(
            "approval_recorded",
            approval_id=approval_id,
            user_id=user_id,
        )

    def get_remaining_approvals(self, approval: ApprovalResponse) -> int:
        """Get number of remaining required approvals."""
        # Find applicable chain
        chain = self._find_applicable_chain(approval)
        if not chain:
            return 0

        # Get current approvals
        current = len(self.approval_records.get(approval.approval_id, []))

        # Calculate required
        total_required = sum(
            level.get("required_approvals", 1) for level in chain.levels
        )

        return max(0, total_required - current)

    def _find_applicable_chain(
        self, approval: ApprovalResponse
    ) -> Optional[ApprovalChain]:
        """Find the approval chain applicable to an action."""
        for chain in self.chains.values():
            conditions = chain.conditions

            # Check action match
            if "action" in conditions:
                if approval.action not in conditions["action"]:
                    continue

            return chain

        return None

    def get_chain_for_action(
        self,
        action: str,
        target: str,
        environment: str,
    ) -> Optional[ApprovalChain]:
        """Get the approval chain for an action."""
        for chain in self.chains.values():
            conditions = chain.conditions

            # Check action match
            if "action" in conditions:
                if action not in conditions["action"]:
                    continue

            # Check environment match
            if "environment" in conditions:
                if environment not in conditions["environment"]:
                    continue

            return chain

        return None

    def list_chains(self) -> List[ApprovalChain]:
        """List all approval chains."""
        return list(self.chains.values())

    def add_chain(self, chain: ApprovalChain):
        """Add a new approval chain."""
        self.chains[chain.chain_id] = chain
        logger.info("approval_chain_added", chain_id=chain.chain_id)
