"""Unit tests for Architectural Upgrades (EventBus Decoupled Kanban, Poincaré Quarantine, AutoHarness Synthesis)."""

from cohezion.agi.autoharness_policy import AutoHarnessPolicy
from cohezion.core.event_bus import EventBus, EventType
from cohezion.data_mesh.kanban_bridge import register_event_bus_subscriptions
from cohezion.proactive.evi_healer import EVIHealer


def test_upgrade_1_decoupled_event_bus_kanban_subscription() -> None:
    bus = EventBus()
    register_event_bus_subscriptions(bus)

    assert EventType.DATA_PRODUCT_CREATED in bus._handlers
    assert EventType.AGENT_COMPLETE in bus._handlers
    assert EventType.METRIC_UPDATE in bus._handlers


def test_upgrade_2_poincare_trajectory_anomaly_quarantine() -> None:
    healer = EVIHealer()

    # Test normal trajectory drift (drift = 0.5 <= 1.5)
    action_normal = healer.evaluate_trajectory_anomaly(drift=0.5, component="agent_alpha")
    assert action_normal.approved is False or action_normal.evi_score <= 0.75

    # Test anomalous trajectory drift (drift = 2.4 > 1.5)
    action_anomalous = healer.evaluate_trajectory_anomaly(drift=2.4, component="agent_beta")
    assert action_anomalous.approved is True
    assert action_anomalous.evi_score > 0.75
    assert "poincare_quarantine" in action_anomalous.component


def test_upgrade_3_autoharness_policy_synthesis() -> None:
    policy = AutoHarnessPolicy()
    rule_name = policy.synthesize_policy_for_paper(
        title="Zero-Latency Bytecode Verification for Multi-Agent Swarms",
        abstract="Introduces deterministic AST policies for AI agent safety.",
    )
    assert rule_name in policy._verifiers
    res = policy.verify_code("def safe_code() -> None:\n    pass\n")
    assert res.valid is True
