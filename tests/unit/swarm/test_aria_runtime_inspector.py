"""Unit tests for ARIA (Agent Runtime Inspection and Amendment) framework (arXiv:2610.20780).

Validates:
- Real-time trajectory event stream and state hashing.
- In-flight cascade anomaly detection (loops, verifier drops, fan-out risk).
- Intervention mode recommendation (OBSERVE, PAUSE, REPLACE_CONTINUATION, ROLLBACK).
- Compute-aware continuation replacement and atomic checkpointing.
"""

from __future__ import annotations

from cohezion.swarm.aria_runtime_inspector import (
    ARIAAmendmentEngine,
    ARIARuntimeInspector,
    InterventionMode,
    TrajectoryEvent,
)


def test_trajectory_event_state_hash() -> None:
    e1 = TrajectoryEvent(
        run_id="run_100",
        agent_id="agent_planner",
        step_id="step_1",
        observation={"goal": "solve_arc", "task_id": "007"},
        action="inspect_grid_dimensions",
    )
    e2 = TrajectoryEvent(
        run_id="run_100",
        agent_id="agent_planner",
        step_id="step_2",
        observation={"goal": "solve_arc", "task_id": "007"},
        action="inspect_grid_dimensions",
    )
    # Identical state and action yield identical deterministic hash
    assert e1.state_hash == e2.state_hash
    assert len(e1.state_hash) == 12


def test_detect_repetitive_loop_and_high_fanout() -> None:
    inspector = ARIARuntimeInspector(loop_threshold=3)
    run_id = "swarm_exec_001"

    # Step 1: Normal step
    e1 = TrajectoryEvent(
        run_id=run_id,
        agent_id="coder",
        step_id="s1",
        action="read_file_config",
        verifier_score=0.95,
    )
    r1 = inspector.record_step(e1)
    assert r1.recommended_mode == InterventionMode.OBSERVE
    assert r1.risk_score == 0.0

    # Steps 2 and 3: Identical repetitive actions with high fanout
    e2 = TrajectoryEvent(
        run_id=run_id,
        agent_id="coder",
        step_id="s2",
        action="read_file_config",
        verifier_score=0.90,
    )
    inspector.record_step(e2)

    e3 = TrajectoryEvent(
        run_id=run_id,
        agent_id="coder",
        step_id="s3",
        action="read_file_config",
        confidence=0.40,
        downstream_agent_count=4,
        verifier_score=0.85,
    )
    r3 = inspector.record_step(e3)

    assert "repetitive_action_loop" in r3.anomaly_types
    assert "high_fanout_ambiguity" in r3.anomaly_types
    assert r3.risk_score >= 0.70
    assert r3.recommended_mode == InterventionMode.REPLACE_CONTINUATION
    assert r3.checkpoint_recommended


def test_detect_verifier_collapse_triggers_rollback() -> None:
    inspector = ARIARuntimeInspector(verifier_collapse_floor=0.40)
    run_id = "swarm_exec_002"

    e1 = TrajectoryEvent(
        run_id=run_id,
        agent_id="executor",
        step_id="s1",
        action="apply_ast_patch",
        verifier_score=0.92,
    )
    inspector.record_step(e1)

    # Catastrophic verifier collapse
    e2 = TrajectoryEvent(
        run_id=run_id,
        agent_id="executor",
        step_id="s2",
        action="delete_critical_subgraph",
        verifier_score=0.20,
    )
    r2 = inspector.record_step(e2)

    assert "verifier_score_collapse" in r2.anomaly_types
    assert r2.risk_score >= 0.85
    assert r2.recommended_mode == InterventionMode.ROLLBACK


def test_aria_amendment_engine_continuation_replacement() -> None:
    inspector = ARIARuntimeInspector()
    run_id = "swarm_exec_003"

    # Evaluator assigns scores based on semantic safety
    def mock_verifier(obs: dict, act: str) -> float:
        if act == "compile_zero_knowledge_verifier":
            return 0.95
        if act == "unsafe_bypass_eval":
            return 0.10
        return 0.50

    engine = ARIAAmendmentEngine(inspector=inspector, verifier_fn=mock_verifier)

    # Initial safe step
    e1 = TrajectoryEvent(
        run_id=run_id,
        agent_id="agent_1",
        step_id="s1",
        action="init_environment",
        verifier_score=0.90,
    )
    inspector.record_step(e1)
    ckpt_id = engine.checkpoint(run_id)
    assert ckpt_id.startswith("ckpt_swarm_exec_003_")

    # Faulty step with low verifier score
    e2 = TrajectoryEvent(
        run_id=run_id,
        agent_id="agent_2",
        step_id="s2",
        action="unsafe_bypass_eval",
        verifier_score=0.25,
    )
    assessment = inspector.record_step(e2)

    candidates = [
        "unsafe_bypass_eval",
        "neutral_noop",
        "compile_zero_knowledge_verifier",
    ]

    ok, adopted_action, rationale = engine.amend_continuation(
        run_id=run_id,
        assessment=assessment,
        candidate_continuations=candidates,
        compute_budget=2,
    )

    assert ok
    assert adopted_action == "compile_zero_knowledge_verifier"
    assert "Accepted amendment" in rationale

    # Verify history in inspector was atomically amended
    history = inspector.trajectories[run_id]
    assert len(history) == 2
    assert history[-1].action == "compile_zero_knowledge_verifier"
    assert history[-1].verifier_score == 0.95
    assert history[-1].metadata.get("aria_amended") is True


def test_aria_amendment_engine_fallback_on_inadequate_candidates() -> None:
    inspector = ARIARuntimeInspector()
    run_id = "swarm_exec_004"

    engine = ARIAAmendmentEngine(inspector=inspector, verifier_fn=lambda obs, act: 0.30)

    e1 = TrajectoryEvent(
        run_id=run_id,
        agent_id="agent_1",
        step_id="s1",
        action="failing_action",
        verifier_score=0.20,
    )
    assessment = inspector.record_step(e1)

    ok, adopted_action, rationale = engine.amend_continuation(
        run_id=run_id,
        assessment=assessment,
        candidate_continuations=["inadequate_candidate_1"],
        compute_budget=1,
    )

    assert not ok
    assert adopted_action == "aria_safe_deterministic_hold"
    assert "fallback to safe hold" in rationale
