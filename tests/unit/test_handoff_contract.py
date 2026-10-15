"""Unit tests for Structured Inter-Agent Handoff Contracts & Trajectory Gating."""

import pytest
from cohezion.swarm.handoff_contract import (
    AgentRole,
    ConflictResolutionStrategy,
    CriticEvaluationResult,
    SwarmConflictResolver,
    TaskHandoffContract,
    TaskStatus,
)


def test_handoff_contract_lifecycle_and_circuit_breaker():
    contract = TaskHandoffContract(
        contract_id="contract_test_01",
        parent_task_id="task_arc_01",
        source_agent="supervisor_0",
        source_role=AgentRole.SUPERVISOR,
        target_agent="proposer_npu",
        target_role=AgentRole.PROPOSER,
        task_intent="Synthesize D4 dihedral transformation function",
        input_payload={"grid": [[1, 2], [3, 4]]},
        acceptance_criteria=["f(g*x) == g*f(x)", "Zero syntax errors"],
        max_recursion_depth=3,
        max_token_ceiling=1000,
    )

    can_proceed, msg = contract.can_proceed()
    assert can_proceed is True
    assert msg == "Nominal"

    # Record step 1
    contract.record_step(
        agent_id="proposer_npu",
        role=AgentRole.PROPOSER,
        action_type="code_generation",
        tokens=300,
        duration_ms=2100.0,
        passed_validation=True,
    )
    assert contract.recursion_depth == 1
    assert contract.accumulated_tokens == 300
    assert len(contract.trajectory) == 1

    # Record step 2
    contract.record_step(
        agent_id="critic_agent",
        role=AgentRole.CRITIC,
        action_type="adversarial_red_team",
        tokens=400,
        duration_ms=1500.0,
        passed_validation=True,
    )
    assert contract.recursion_depth == 2
    assert contract.accumulated_tokens == 700

    # Step 3 exceeds token ceiling if +400 tokens added (700 + 400 = 1100 > 1000)
    contract.record_step(
        agent_id="proposer_npu",
        role=AgentRole.PROPOSER,
        action_type="code_repair",
        tokens=400,
        duration_ms=2000.0,
        passed_validation=True,
    )
    can_proceed, msg = contract.can_proceed()
    assert can_proceed is False
    assert "Recursion depth limit reached" in msg or "Token ceiling exceeded" in msg


def test_swarm_conflict_resolver_debate_and_critique():
    contract = TaskHandoffContract(
        contract_id="contract_test_02",
        parent_task_id="task_rsna_01",
        source_agent="proposer_0",
        source_role=AgentRole.PROPOSER,
        target_agent="critic_0",
        target_role=AgentRole.CRITIC,
        task_intent="Evaluate JSN Monotonicity",
        input_payload={"features": {"jsn": 0.4}},
        acceptance_criteria=["Monotonic decrease with KL grade"],
        max_recursion_depth=5,
        max_token_ceiling=5000,
    )

    # Reject case: needs debate and critique
    critique_fail = CriticEvaluationResult(
        contract_id="contract_test_02",
        critic_agent="critic_0",
        approved=False,
        critique_score=0.45,
        identified_defects=["Non-monotonic gradient inversion detected at slice 12"],
        recommended_strategy=ConflictResolutionStrategy.DEBATE_AND_CRITIQUE,
    )
    status = SwarmConflictResolver.resolve_critique(contract, critique_fail)
    assert status == TaskStatus.CRITIQUED

    # Approve case: passes threshold >= 0.85
    critique_pass = CriticEvaluationResult(
        contract_id="contract_test_02",
        critic_agent="critic_0",
        approved=True,
        critique_score=0.92,
        identified_defects=[],
        recommended_strategy=ConflictResolutionStrategy.DEBATE_AND_CRITIQUE,
    )
    status_pass = SwarmConflictResolver.resolve_critique(contract, critique_pass)
    assert status_pass == TaskStatus.VERIFIED
