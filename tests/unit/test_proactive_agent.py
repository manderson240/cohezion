"""Unit tests for EVIHealer and proactive self-healing."""

from cohezion.proactive.evi_healer import EVIHealer


def test_evi_healer_approved_action() -> None:
    healer = EVIHealer()
    # quality_gap = 0.5, issue_severity = 0.9, cost = 0.5 -> EVI = (0.5 * 0.9) / 0.5 = 0.90 > 0.75
    action = healer.evaluate_healing_candidate(
        component="memory_pool",
        issue_description="Memory fragmentation above threshold",
        proposed_remediation="Purge non-essential LRU cache entries",
        quality_gap=0.5,
        issue_severity=0.9,
        remediation_cost=0.5,
    )

    assert action.approved is True
    assert action.evi_score > 0.75
    assert len(healer.get_action_history()) == 1


def test_evi_healer_rejected_action() -> None:
    healer = EVIHealer()
    # quality_gap = 0.1, issue_severity = 0.3, cost = 0.8 -> EVI = 0.0375 <= 0.75
    action = healer.evaluate_healing_candidate(
        component="telemetry",
        issue_description="Minor logging jitter",
        proposed_remediation="Restart logging daemon",
        quality_gap=0.1,
        issue_severity=0.3,
        remediation_cost=0.8,
    )

    assert action.approved is False
    assert action.evi_score <= 0.75
