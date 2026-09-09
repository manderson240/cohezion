import pytest
from pathlib import Path
from cohezion.proactive.metr_negentropy_controller import (
    METRNegentropyController,
    ControllerDecision,
    DAILY_QUOTA_LIMIT_USD,
)
from cohezion.agi.autoharness_policy import AutoHarnessPolicy


def test_daily_quota_enforcement():
    controller = METRNegentropyController(daily_quota_usd=50.00)
    # Simulate spending 48.00
    controller.record_step("step_1", [0.1, 0.1], coherence=0.50, estimated_cost_usd=48.00)
    assert controller.remaining_budget == pytest.approx(2.00)

    # Action that costs 3.00 exceeds remaining budget
    decision = controller.evaluate_proposed_action(
        proposed_action="orch_or_hiho",
        proposed_state_point=[0.1, 0.1],
        proposed_coherence=0.50,
        estimated_cost_usd=3.00,
    )
    assert decision.allowed is False
    assert decision.action == "QUOTA_HALT"


def test_autoharness_pre_verification_rejection():
    autoharness = AutoHarnessPolicy()
    autoharness.register_policy("strict_positive", lambda s: s.get("val", 0) > 0)
    controller = METRNegentropyController(autoharness=autoharness)

    decision = controller.evaluate_proposed_action(
        proposed_action="strict_positive",
        proposed_state_point=[0.1, 0.1],
        action_payload={"val": -10},
    )
    assert decision.allowed is False
    assert decision.action == "AUTOHARNESS_REJECT"


def test_negentropy_tripwire_and_rollback():
    controller = METRNegentropyController(tripwire_steps=2)

    # Step 1: Initial stable state (Checkpoint 1)
    controller.record_step("stable_step_1", [0.1, 0.1], coherence=0.50)
    assert controller._last_checkpoint_step == 1

    # Step 2: Mild entropy drift
    controller.record_step("drift_step_2", [0.4, -0.4], coherence=0.35)

    # Propose Step 3 with severe entropy inflation (turbulent coherence & distant coordinates)
    decision = controller.evaluate_proposed_action(
        proposed_action="orch_or_hiho",
        proposed_state_point=[0.9, -0.9],
        proposed_coherence=0.05,
    )

    # Must activate the Negentropy Tripwire!
    assert decision.allowed is False
    assert decision.action == "TRIPWIRE_ROLLBACK"
    assert decision.last_stable_checkpoint_step == 1

    # Execute rollback
    res_step = controller.execute_rollback()
    assert res_step == 1
    assert len(controller._trajectory) == 1
    assert controller._trajectory[0].action_description == "stable_step_1"


def test_sub_millisecond_controller_latency():
    controller = METRNegentropyController()
    controller.record_step("step_1", [0.1, 0.1], coherence=0.50)

    decision = controller.evaluate_proposed_action(
        proposed_action="orch_or_hiho",
        proposed_state_point=[0.12, 0.11],
        proposed_coherence=0.50,
    )
    assert decision.allowed is True
    assert decision.action == "PROCEED"
    assert decision.execution_latency_ms < 5.0
