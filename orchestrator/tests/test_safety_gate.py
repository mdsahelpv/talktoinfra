"""Tests for the safety gate."""

import pytest

from src.safety.gate import SafetyGate
from shared.python.models.action import ActionDefinition, PermissionTier, InfraCategory


@pytest.fixture
def gate():
    return SafetyGate()


@pytest.fixture
def read_action():
    return ActionDefinition(
        name="test_read",
        description="Test read action",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.READ,
    )


@pytest.fixture
def mutate_action():
    return ActionDefinition(
        name="test_mutate",
        description="Test mutate action",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.MUTATE,
    )


@pytest.fixture
def destructive_action():
    return ActionDefinition(
        name="test_destructive",
        description="Test destructive action",
        category=InfraCategory.KUBERNETES,
        tier=PermissionTier.DESTRUCTIVE,
    )


@pytest.mark.asyncio
async def test_read_auto_approved(gate, read_action):
    allowed, reason = await gate.check(read_action, {})
    assert allowed is True
    assert "auto-approved" in reason.lower()


@pytest.mark.asyncio
async def test_mutate_requires_approval(gate, mutate_action):
    allowed, reason = await gate.check(mutate_action, {})
    assert allowed is False
    assert "approval" in reason.lower()


@pytest.mark.asyncio
async def test_destructive_requires_fresh_approval(gate, destructive_action):
    allowed, reason = await gate.check(destructive_action, {})
    assert allowed is False
    assert "fresh" in reason.lower()


def test_mark_approved(gate, mutate_action):
    gate.mark_approved("session_1", "test_mutate", PermissionTier.MUTATE)
    assert gate.is_approved_in_session("session_1", "test_mutate", PermissionTier.MUTATE)
    assert not gate.is_approved_in_session("session_2", "test_mutate", PermissionTier.MUTATE)


def test_destructive_not_remembered(gate, destructive_action):
    gate.mark_approved("session_1", "test_destructive", PermissionTier.DESTRUCTIVE)
    assert not gate.is_approved_in_session("session_1", "test_destructive", PermissionTier.DESTRUCTIVE)
