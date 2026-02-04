"""
Unit tests for Discovered Infrastructure API.
"""

import pytest
from datetime import datetime
from uuid import uuid4, UUID

from app.models_discovered import (
    DiscoveredInfrastructure,
    DiscoveredState,
    InfrastructureType,
    VALID_STATE_TRANSITIONS,
)
from app.schemas_discovered import (
    DiscoveredInfrastructureResponse,
    DiscoveredStatsSchema,
    OnboardingSuggestionSchema,
    PaginatedDiscoveredResponse,
)


class TestStateMachineTransitions:
    """Test state machine transitions for discovered infrastructure."""

    def test_valid_transitions_from_discovered(self):
        """Test valid transitions from DISCOVERED state."""
        assert DiscoveredState.DISCOVERED in VALID_STATE_TRANSITIONS
        assert DiscoveredState.ANALYZED in VALID_STATE_TRANSITIONS[DiscoveredState.DISCOVERED]
        assert DiscoveredState.IGNORED in VALID_STATE_TRANSITIONS[DiscoveredState.DISCOVERED]
        assert DiscoveredState.SUGGESTED not in VALID_STATE_TRANSITIONS[
            DiscoveredState.DISCOVERED]

    def test_valid_transitions_from_analyzed(self):
        """Test valid transitions from ANALYZED state."""
        assert DiscoveredState.ANALYZED in VALID_STATE_TRANSITIONS
        assert DiscoveredState.SUGGESTED in VALID_STATE_TRANSITIONS[DiscoveredState.ANALYZED]
        assert DiscoveredState.IGNORED in VALID_STATE_TRANSITIONS[DiscoveredState.ANALYZED]

    def test_valid_transitions_from_suggested(self):
        """Test valid transitions from SUGGESTED state."""
        assert DiscoveredState.SUGGESTED in VALID_STATE_TRANSITIONS
        assert DiscoveredState.PENDING_ONBOARDING in VALID_STATE_TRANSITIONS[
            DiscoveredState.SUGGESTED]
        assert DiscoveredState.ONBOARDED in VALID_STATE_TRANSITIONS[DiscoveredState.SUGGESTED]
        assert DiscoveredState.IGNORED in VALID_STATE_TRANSITIONS[DiscoveredState.SUGGESTED]

    def test_valid_transitions_from_onboarding(self):
        """Test valid transitions from ONBOARDING state."""
        assert DiscoveredState.ONBOARDING in VALID_STATE_TRANSITIONS
        assert DiscoveredState.ONBOARDED in VALID_STATE_TRANSITIONS[DiscoveredState.ONBOARDING]
        assert DiscoveredState.FAILED in VALID_STATE_TRANSITIONS[DiscoveredState.ONBOARDING]

    def test_ignored_is_terminal_state(self):
        """Test that IGNORED is a terminal state."""
        assert DiscoveredState.IGNORED in VALID_STATE_TRANSITIONS
        assert len(VALID_STATE_TRANSITIONS[DiscoveredState.IGNORED]) == 0


class TestInfrastructureType:
    """Test infrastructure type enum."""

    def test_all_types_defined(self):
        """Test that all infrastructure types are defined."""
        expected_types = [
            "kubernetes_cluster",
            "cloud_resource",
            "database",
            "load_balancer",
            "service",
            "network_device",
            "host",
            "unknown",
        ]
        for type_name in expected_types:
            assert hasattr(InfrastructureType, type_name.upper())
            assert InfrastructureType[type_name.upper()].value == type_name


class TestSchemas:
    """Test Pydantic schemas."""

    def test_discovered_infrastructure_response_schema(self):
        """Test DiscoveredInfrastructureResponse schema validation."""
        item_id = uuid4()
        response = DiscoveredInfrastructureResponse(
            id=item_id,
            ip_address="192.168.1.100",
            hostname="test-server",
            infra_type=InfrastructureType.HOST,
            state=DiscoveredState.DISCOVERED,
            discovered_at=datetime.utcnow(),
            last_seen_at=datetime.utcnow(),
            confidence_score=85,
            availability_score=100,
            open_ports=[],
            tags=[],
            created_by="test",
        )

        assert response.id == item_id
        assert response.ip_address == "192.168.1.100"
        assert response.hostname == "test-server"
        assert response.infra_type == InfrastructureType.HOST
        assert response.state == DiscoveredState.DISCOVERED
        assert response.confidence_score == 85

    def test_discovered_stats_schema(self):
        """Test DiscoveredStatsSchema schema validation."""
        stats = DiscoveredStatsSchema(
            total_items=100,
            by_type={"host": 50, "database": 30, "kubernetes_cluster": 20},
            by_state={"discovered": 40, "onboarded": 60},
            by_state_detailed={
                "host": {"discovered": 20, "onboarded": 30},
                "database": {"discovered": 10, "onboarded": 20},
            },
            recently_discovered=10,
            pending_onboarding=5,
            onboarded=60,
            ignored=15,
        )

        assert stats.total_items == 100
        assert stats.by_type["host"] == 50
        assert stats.recently_discovered == 10
        assert stats.pending_onboarding == 5

    def test_onboarding_suggestion_schema(self):
        """Test OnboardingSuggestionSchema schema validation."""
        item_id = uuid4()
        suggestion = OnboardingSuggestionSchema(
            item_id=item_id,
            suggested_action="connect_k8s",
            action_label="Connect Kubernetes Cluster",
            confidence=95,
            reason="Kubernetes API server detected on port 6443",
            prerequisites=["Kubeconfig credentials"],
            estimated_effort="10 minutes",
        )

        assert suggestion.item_id == item_id
        assert suggestion.suggested_action == "connect_k8s"
        assert suggestion.confidence == 95
        assert len(suggestion.prerequisites) == 1


class TestDiscoveredStateEnum:
    """Test discovered state enum values."""

    def test_all_states_defined(self):
        """Test that all states are defined."""
        expected_states = [
            "discovered",
            "analyzed",
            "suggested",
            "pending_onboarding",
            "onboarding",
            "onboarded",
            "failed",
            "ignored",
        ]
        for state_name in expected_states:
            assert hasattr(DiscoveredState, state_name.upper())
            assert DiscoveredState[state_name.upper()].value == state_name
