"""Unit tests for the Agentic Software Delivery Primitives."""

from __future__ import annotations

import pytest

from cohezion.compound.agentic_delivery_primitives import (
    AgenticSoftwareDeliveryPipeline,
    DeliveryArtifact,
    DeliveryArtifactType,
    DeliveryContract,
    DeliveryStage,
    PurposeDrivenMemory,
)


@pytest.fixture
def memory() -> PurposeDrivenMemory:
    """Fixture providing a fresh PurposeDrivenMemory instance."""
    return PurposeDrivenMemory()


@pytest.fixture
def pipeline(memory: PurposeDrivenMemory) -> AgenticSoftwareDeliveryPipeline:
    """Fixture providing an AgenticSoftwareDeliveryPipeline wired with memory."""
    return AgenticSoftwareDeliveryPipeline(memory=memory)


def test_delivery_artifact_structure() -> None:
    """Ensure DeliveryArtifact enforces correct immutability and validity checks."""
    artifact = DeliveryArtifact(
        artifact_id="plan_vault_1",
        stage=DeliveryStage.PLAN,
        artifact_type=DeliveryArtifactType.GOAL_SPEC,
        title="Plan: Invariant Hardening",
        content={"intent": "Eliminate underflow", "acceptance_criteria": ["Zero underflow"]},
    )
    assert artifact.is_valid_for_next_stage()
    assert artifact.stage == DeliveryStage.PLAN

    # Incomplete artifact fails validity check
    invalid_art = DeliveryArtifact(
        artifact_id="",
        stage=DeliveryStage.PLAN,
        artifact_type=DeliveryArtifactType.GOAL_SPEC,
        title="",
        content={},
    )
    assert not invalid_art.is_valid_for_next_stage()


def test_delivery_contract_validation() -> None:
    """Ensure formal stage handover contracts enforce boundary requirements."""
    contract = DeliveryContract(
        source_stage=DeliveryStage.PLAN,
        target_stage=DeliveryStage.BUILD,
        required_artifact_types=[DeliveryArtifactType.GOAL_SPEC],
        custom_validators=[lambda a: "intent" in a.content],
    )

    valid_plan = DeliveryArtifact(
        artifact_id="plan_1",
        stage=DeliveryStage.PLAN,
        artifact_type=DeliveryArtifactType.GOAL_SPEC,
        title="Valid Plan",
        content={"intent": "Build feature"},
    )
    valid, msg = contract.validate_handover(valid_plan)
    assert valid
    assert "satisfied" in msg

    # Invalid stage mismatch
    wrong_stage = DeliveryArtifact(
        artifact_id="build_1",
        stage=DeliveryStage.BUILD,
        artifact_type=DeliveryArtifactType.GOAL_SPEC,
        title="Wrong Stage",
        content={"intent": "Build feature"},
    )
    valid, msg = contract.validate_handover(wrong_stage)
    assert not valid
    assert "does not match expected source" in msg


def test_purpose_driven_memory_past_mistakes_and_utility(memory: PurposeDrivenMemory) -> None:
    """Ensure purpose-driven memory indexes defects and computes utility evaluation score."""
    verify_fail = DeliveryArtifact(
        artifact_id="verify_vault_1",
        stage=DeliveryStage.VERIFY,
        artifact_type=DeliveryArtifactType.VERIFICATION_EVIDENCE,
        title="Verification failure",
        content={
            "component": "PortfolioVault",
            "passed": False,
            "failures": ["Arithmetic underflow in updateNav()"],
        },
    )
    memory.record_artifact(verify_fail)

    mistakes = memory.query_past_mistakes("PortfolioVault")
    assert len(mistakes) == 1
    assert "Arithmetic underflow" in mistakes[0]["failure"]

    # Evaluate memory utility
    utility = memory.evaluate_memory_utility(
        task_id="task_1",
        success_with_mem=True,
        success_baseline=False,
        lookup_latency_ms=10.0,
    )
    # Gain = 1.0 - 0.0 = 1.0. Norm latency = 0.1. Score = 1.0 / 1.1 = ~0.909
    assert utility > 0.8
    assert memory.total_artifacts == 1


def test_pipeline_end_to_end_lifecycle(pipeline: AgenticSoftwareDeliveryPipeline) -> None:
    """Ensure full Plan -> Build -> Verify -> Observe cycle executes smoothly."""
    # 1. Plan
    plan_art = pipeline.execute_plan(
        component="LendingPool",
        intent="Support multi-asset flashloans safely",
        constraints=["ReentrancyGuard", "Zero flashloan fee leakage"],
        acceptance_criteria=["Must revert on reentrant calls", "Balance delta >= fee"],
    )
    assert plan_art.stage == DeliveryStage.PLAN

    # 2. Build
    def mock_build(plan_content: dict) -> dict:
        return {
            "diff_or_code": "function flashloan() external nonReentrant { ... }",
            "rationale": "Applied nonReentrant modifier and CEI pattern",
            "modified_files": ["LendingPool.sol"],
            "evidence": ["Compiled with solc 0.8.28"],
        }

    build_art = pipeline.execute_build(plan_art, mock_build)
    assert build_art.stage == DeliveryStage.BUILD

    # 3. Verify
    def mock_verify(build_content: dict) -> tuple[bool, list[str], list[str]]:
        # Verification passes
        return True, ["Property verified: nonReentrant modifier present"], []

    verify_art = pipeline.execute_verify(build_art, mock_verify)
    assert verify_art.stage == DeliveryStage.VERIFY
    assert verify_art.content["passed"] is True

    # 4. Observe
    def mock_observe(verify_content: dict) -> dict:
        return {
            "metrics": {"requests_served": 5000, "failed_invariants": 0},
            "anomalies": [],
            "synthesized_learnings": ["Flashloan reentrancy protection verified in prod"],
        }

    observe_art = pipeline.execute_observe(verify_art, mock_observe)
    assert observe_art.stage == DeliveryStage.OBSERVE
    assert len(observe_art.content["synthesized_learnings"]) == 1

    # Check Sleep experience export
    sleep_exp = pipeline.export_sleep_experience(observe_art)
    assert sleep_exp["reward"] == 1.0
    assert sleep_exp["loss"] == 0.0
    assert "anomalies=0" in sleep_exp["trace"]


def test_pipeline_contract_breach_rejection(pipeline: AgenticSoftwareDeliveryPipeline) -> None:
    """Ensure build cannot proceed if plan artifact breaches required contract fields."""
    invalid_plan = DeliveryArtifact(
        artifact_id="bad_plan",
        stage=DeliveryStage.PLAN,
        artifact_type=DeliveryArtifactType.GOAL_SPEC,
        title="Bad Plan",
        content={"intent": "Only intent, missing acceptance_criteria"},
    )
    with pytest.raises(ValueError, match="Plan -> Build Contract Breach"):
        pipeline.execute_build(invalid_plan, lambda c: {})
