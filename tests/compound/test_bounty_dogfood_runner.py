"""Unit tests for BountyDogfoodHarness.

Validates end-to-end execution of Microsoft Agentic SDLC delivery primitives
(Plan -> Build -> Verify -> Observe) combined with SLEEP continual learning
and formal invariant verification on our live bounty targets.
"""

from __future__ import annotations

from cohezion.compound.agentic_delivery_primitives import DeliveryStage
from cohezion.compound.bounty_dogfood_runner import (
    BountyDogfoodHarness,
    BountyDogfoodResult,
)


def test_bounty_dogfood_harness_init() -> None:
    """Verify clean initialization of the dogfood harness."""
    harness = BountyDogfoodHarness()
    assert harness.memory is not None
    assert harness.pipeline is not None
    assert harness.sleep is not None
    assert harness.bounty_harness is not None


def test_bounty_dogfood_run_single_target() -> None:
    """Verify execution of a single bounty target through all 4 stages."""
    harness = BountyDogfoodHarness()

    vuln_code = """
contract TestContract {
    function getNextValidator() public {
        if (info.maxCapacity != 0 || totalStaked < info.maxCapacity) {
            return info.maxCapacity - totalStaked;
        }
    }
}
"""
    patch_code = """
contract TestContract {
    function getNextValidator() public {
        if (info.maxCapacity != 0 && totalStaked < info.maxCapacity) {
            return info.maxCapacity - totalStaked;
        }
    }
}
"""
    result = harness.run_target(
        target_id="TEST-TARGET-01",
        target_name="Test Protocol",
        bounty_pool_usd=50_000,
        source_code=vuln_code,
        patch_code=patch_code,
        component_name="TestContract",
        expected_rule="capacity_check_operator_inversion_underflow",
    )

    assert isinstance(result, BountyDogfoodResult)
    assert result.target_id == "TEST-TARGET-01"
    assert result.bounty_pool_usd == 50_000
    assert result.plan_artifact.stage == DeliveryStage.PLAN
    assert result.build_artifact.stage == DeliveryStage.BUILD
    assert result.verify_artifact.stage == DeliveryStage.VERIFY
    assert result.observe_artifact is not None
    assert result.observe_artifact.stage == DeliveryStage.OBSERVE
    assert result.verify_artifact.content["passed"] is True
    assert result.memory_utility > 0.8
    assert result.execution_latency_ms > 0.0


def test_bounty_dogfood_run_all_bounties() -> None:
    """Dogfood all three active bounties ($160k total pool) through the agentic pipeline."""
    harness = BountyDogfoodHarness()
    results = harness.run_all_bounties()

    assert len(results) == 3

    # Check Intuition Protocol
    c4_res = results[0]
    assert c4_res.target_id == "C4-INTUITION-01"
    assert c4_res.bounty_pool_usd == 100_000
    assert c4_res.verify_artifact.content["passed"] is True

    # Check Mystic Finance
    mystic_res = results[1]
    assert mystic_res.target_id == "CANTINA-MYSTIC-01"
    assert mystic_res.bounty_pool_usd == 20_000
    assert mystic_res.verify_artifact.content["passed"] is True

    # Check deBridge DLN
    debridge_res = results[2]
    assert debridge_res.target_id == "IMMUNEFI-DEBRIDGE-01"
    assert debridge_res.bounty_pool_usd == 40_000
    assert debridge_res.verify_artifact.content["passed"] is True

    # All targets must exceed 0.8 memory utility threshold
    for res in results:
        assert res.memory_utility >= 0.85
        assert res.violations_detected > 0

    # Ensure SLEEP consolidation ran
    assert harness.sleep.cycle_count == 1
    assert len(harness.sleep._history) == 1
    assert harness.sleep._history[0].overall_retention_score > 0.0
    assert harness.sleep._history[0].dreaming.dreams_verified > 0


def test_bounty_dogfood_unpatched_failure() -> None:
    """Verify that an ineffective patch fails the VERIFY gate."""
    harness = BountyDogfoodHarness()

    vuln_code = """
contract BadVault {
    function _rollover() internal {
        uint256 previousEpoch = currentEpochLocal - 1;
        totalUtilization[currentEpochLocal] = totalUtilization[previousEpoch];
    }
}
"""
    # Still broken
    bad_patch_code = vuln_code

    result = harness.run_target(
        target_id="TEST-FAIL-01",
        target_name="Failing Protocol",
        bounty_pool_usd=10_000,
        source_code=vuln_code,
        patch_code=bad_patch_code,
        component_name="BadVault",
        expected_rule="skipped_epoch_rollover_state_loss",
    )

    assert result.verify_artifact.content["passed"] is False
    assert len(result.verify_artifact.content["failures"]) > 0
    assert result.observe_artifact is None
    # Baseline vs failed with mem yields zero delta gain
    assert result.memory_utility == 0.0
