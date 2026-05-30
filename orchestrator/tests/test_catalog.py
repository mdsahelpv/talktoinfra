"""Tests for the action catalog."""

from shared.python.catalog import build_default_catalog
from shared.python.models.action import PermissionTier, InfraCategory


def test_catalog_has_actions():
    catalog = build_default_catalog()
    assert len(catalog.actions) > 0, "Catalog should have actions registered"


def test_all_categories_present():
    catalog = build_default_catalog()
    categories = set()
    for a in catalog.actions.values():
        categories.add(a.category)
    for cat in InfraCategory:
        assert cat in categories, f"Missing category: {cat}"


def test_all_tiers_present():
    catalog = build_default_catalog()
    tiers = set()
    for a in catalog.actions.values():
        tiers.add(a.tier)
    for tier in PermissionTier:
        assert tier in tiers, f"Missing tier: {tier}"


def test_k8s_actions():
    catalog = build_default_catalog()
    k8s = catalog.list_by_category(InfraCategory.KUBERNETES)
    assert len(k8s) >= 8, f"Expected at least 8 K8s actions, got {len(k8s)}"


def test_network_actions():
    catalog = build_default_catalog()
    net = catalog.list_by_category(InfraCategory.NETWORK)
    assert len(net) >= 3, f"Expected at least 3 network actions, got {len(net)}"


def test_each_action_has_name_and_description():
    catalog = build_default_catalog()
    for name, action in catalog.actions.items():
        assert action.name == name
        assert action.description, f"Action {name} missing description"
