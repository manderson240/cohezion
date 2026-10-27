"""Tests for EmergentPlayEngine and AutotelicPlaySandbox.

Validates the implementation of MIT CSAIL's 'Is this machine playing?' (arXiv:2610.07130).
"""

import json
from pathlib import Path
import pytest

from cohezion.agi.emergent_play_sandbox import (
    AffordanceType,
    ARC3PlaygroundAdapter,
    BubblewrapSandboxSpec,
    DualMemoryManager,
    DynamicContextResetManager,
    EmergentPlayEngine,
    EmpiricalPlayBenchmarkScorecard,
    EndogenousChallenge,
    EpisodicMemoryEntry,
    HourlySessionResetManager,
    PlayCriterion,
    SemanticAffordance,
)


@pytest.fixture
def temp_workspace(tmp_path: Path) -> Path:
    """Fixture providing an isolated workspace path."""
    ws = tmp_path / "sandbox_workspace"
    ws.mkdir(parents=True, exist_ok=True)
    return ws


def test_burghardt_four_criteria(temp_workspace: Path):
    """Test that all four Burghardt hallmarks of cognitive play are formally audited."""
    engine = EmergentPlayEngine("session_001", temp_workspace)

    # 1. Rule self-imposition
    engine.create_spontaneous_game(
        challenge_id="floor_is_lava",
        name="The Floor is Lava",
        rules="Traverse between mesa sentinels with 0 ground touches",
        target_metric="ground_touches",
        threshold=0.0,
    )

    # 2. Make-believe & structured variation in actions
    for step in range(5):
        engine.perform_action(
            step=step,
            action="JUMP_HOP",
            params={"target": f"sentinel_{step}", "variation_delta": 0.05 * step},
            observation={"landed": True, "ground_touches": 0},
            symbolic_pretense="Sentinels imagined as airships in a fleet",
            hypothesized_cause="Airborne momentum conservation",
        )

    audit = engine.audit_burghardt_play_criteria()
    assert audit["all_criteria_satisfied"] is True
    assert audit["rule_self_imposition_count"] >= 1
    assert audit["structured_variation_count"] >= 5
    assert audit["make_believe_count"] >= 5
    assert audit["active_challenges_count"] >= 1


def test_honest_self_invalidation():
    """Test honest self-invalidation when success violates physical reality bounds (Sec 4.4)."""
    challenge = EndogenousChallenge(
        challenge_id="juggling_marathon",
        name="50-Cycle Juggling Marathon",
        rule_description="Catch cube 50 consecutive times in mid-air",
        target_metric="catches",
        threshold_value=50.0,
    )

    # Degenerate attempt: 50 catches completed in 0.2s (impossible without immediate recapture)
    success, reason = challenge.evaluate_attempt(
        achieved_value=50.0,
        execution_duration=0.2,
        min_physical_duration=2.5,
    )
    assert success is False
    assert "Degenerate achievement invalidated" in reason
    assert challenge.strictness_level == 2
    assert len(challenge.invalidation_history) == 1

    # Legitimate attempt: 50 catches completed in 3.8s (valid flight time)
    success_legit, reason_legit = challenge.evaluate_attempt(
        achieved_value=50.0,
        execution_duration=3.8,
        min_physical_duration=2.5,
    )
    assert success_legit is True
    assert challenge.current_record == 50.0
    assert "Legitimate achievement validated" in reason_legit


def test_dual_memory_and_causal_ablation(temp_workspace: Path):
    """Test dual-store memory persistence and causal ablation (Cloos et al. Sec 5.2)."""
    memory = DualMemoryManager(temp_workspace)

    # Register semantic affordances
    aff1 = SemanticAffordance(
        affordance_id="ROCK_SHATTERING",
        affordance_type=AffordanceType.PROP_FRACTURE,
        predicate_rule="ImpactVelocity >= 12.0 -> Rock spawns 3 Cubes",
        preconditions={"min_throw_speed": 12.0},
        outcomes={"cubes_spawned": 3},
        discovered_session="session_001",
    )
    aff2 = SemanticAffordance(
        affordance_id="SENTINEL_HOPPING",
        affordance_type=AffordanceType.AIRBORNE_CHAIN,
        predicate_rule="HopDistance <= 2.5 -> Continuous Airborne Traversal",
        preconditions={"max_gap": 2.5},
        outcomes={"ground_touches": 0},
        discovered_session="session_001",
    )
    memory.register_affordance(aff1)
    memory.register_affordance(aff2)

    # Log episodic entries
    entry1 = EpisodicMemoryEntry(
        step=1,
        session_id="session_001",
        action="THROW_ROCK",
        params={"speed": 15.0},
        observation={"cubes_spawned": 3},
        hypothesized_cause="Rock_Shattering threshold exceeded",
    )
    entry2 = EpisodicMemoryEntry(
        step=2,
        session_id="session_001",
        action="JUMP_HOP",
        params={"dist": 2.0},
        observation={"ground_touches": 0},
        hypothesized_cause="Sentinel_Hopping trajectory verified",
    )
    memory.log_episode(entry1)
    memory.log_episode(entry2)

    assert memory.has_affordance("ROCK_SHATTERING") is True
    assert memory.has_affordance("SENTINEL_HOPPING") is True
    assert len(memory.episodic_entries) == 2

    # Verify physical file existence
    assert memory.episodic_path.exists()
    assert memory.semantic_path.exists()

    # Perform causal ablation of ROCK_SHATTERING
    ablated = memory.ablate_affordance("ROCK_SHATTERING")
    assert ablated is True
    assert memory.has_affordance("ROCK_SHATTERING") is False
    assert memory.has_affordance("SENTINEL_HOPPING") is True

    # Episodic entry referencing Rock_Shattering is excised
    assert len(memory.episodic_entries) == 1
    assert memory.episodic_entries[0].action == "JUMP_HOP"


def test_scientist_in_the_crib_counterfactual(temp_workspace: Path):
    """Test counterfactual parameter sweeps isolating physical causal thresholds (Sec 7.2)."""
    engine = EmergentPlayEngine("session_001", temp_workspace)

    # Mock environment where climbing succeeds only when wall height <= 1.5
    def mock_climb_env(state: dict, action: str, height: float) -> dict:
        return {"success": height <= 1.5, "measured_height": height}

    finding = engine.scientist.evaluate_counterfactual(
        base_state={"pos": (0, 0)},
        intervention_action="CLIMB_LEDGE",
        intervention_param="ledge_height",
        test_values=[0.5, 1.0, 1.5, 2.0, 2.5],
        execution_env=mock_climb_env,
    )

    assert finding["isolated"] is True
    assert finding["threshold"] == pytest.approx(1.75, abs=0.1)


def test_arc3_childhood_pre_play(temp_workspace: Path):
    """Test ARC-AGI-3 childhood pre-play affordance discovery without reward lock-in."""
    engine = EmergentPlayEngine("session_arc3", temp_workspace)
    adapter = ARC3PlaygroundAdapter(engine)

    initial_grid = [[0 for _ in range(10)] for _ in range(10)]
    summary = adapter.run_childhood_exploration(initial_grid=initial_grid, step_budget=15)

    assert summary["steps_completed"] == 15
    assert summary["unique_states_explored"] > 1
    assert summary["affordances_mapped"] is True
    assert engine.memory.has_affordance("GRID_BLOCK_PUSHABLE") is True



def test_hourly_session_reset_and_rehydration(temp_workspace: Path):
    """Test hourly session resets with episodic compaction and semantic rehydration (Appendix A.4)."""
    memory = DualMemoryManager(temp_workspace)
    aff = SemanticAffordance(
        affordance_id="ROCK_IMPACT_CLEAVAGE",
        affordance_type=AffordanceType.PROP_FRACTURE,
        predicate_rule="Impact >= 10.0 -> Cube generation",
        preconditions={"speed": 10.0},
        outcomes={"spawned": 3},
        discovered_session="session_000",
    )
    memory.register_affordance(aff)

    # Log 3 episodic entries
    for i in range(3):
        entry = EpisodicMemoryEntry(
            step=i,
            session_id="session_000",
            action=f"ACTION_{i}",
            params={"val": i},
            observation={"success": True},
            symbolic_pretense=f"Metaphor {i}",
        )
        memory.log_episode(entry)

    reset_mgr = HourlySessionResetManager(memory, soul_text="Eko is an autotelic explorer.")
    assert "You will be reset in 5 minutes" in reset_mgr.trigger_pre_reset_warning()

    state = reset_mgr.advance_session()
    assert state["session_index"] == 1
    assert state["new_session_id"] == "session_001"
    prompt = state["rehydrated_system_prompt"]
    assert "Eko is an autotelic explorer." in prompt
    assert "ROCK_IMPACT_CLEAVAGE" in prompt
    assert "Metaphor 0" in prompt
    assert state["episodic_entries_count"] == 3


def test_bubblewrap_sandbox_spec(temp_workspace: Path):
    """Test bubblewrap security sandbox containment specification (Appendix A.5)."""
    from cohezion.agi.emergent_play_sandbox import BubblewrapSandboxSpec

    spec = BubblewrapSandboxSpec(workspace_dir=temp_workspace)
    args = spec.build_bwrap_args()
    assert "bwrap" in args
    assert "--unshare-all" in args
    assert "/workspace" in args
    assert "--chdir" in args


def test_empirical_play_benchmark_scorecard():
    """Test quantitative evaluation metrics between 30h play and 0h naive baseline (Sec 5.1)."""
    from cohezion.agi.emergent_play_sandbox import EmpiricalPlayBenchmarkScorecard

    ref_30h = EmpiricalPlayBenchmarkScorecard.reference_30h_mean()
    ref_0h = EmpiricalPlayBenchmarkScorecard.reference_0h_mean()

    lift = ref_30h.evaluate_relative_lift(ref_0h)
    assert lift["many_5_towers_lift"] == pytest.approx(250.0, abs=1.0)
    assert lift["objects_on_spire_lift"] == pytest.approx(233.33, abs=1.0)
    assert lift["tallest_tower_lift"] == pytest.approx(53.33, abs=1.0)
    assert lift["throw_success_delta"] == 1.0


def test_dynamic_context_reset_manager_watermarking(temp_workspace: Path):
    """Test dynamic context token watermarking (75% warning, 85% reset) replacing fixed hourly clock."""
    memory = DualMemoryManager(temp_workspace)
    manager = DynamicContextResetManager(
        memory_manager=memory,
        max_context_tokens=10_000,
        warning_watermark=0.75,
        reset_watermark=0.85,
    )

    # 1. Turn 1: 5,000 tokens (50% utilization) -> No warning, no reset
    turn1 = manager.record_turn(tokens_used=5000, action="MOVE_FORWARD")
    assert turn1["utilization"] == 0.50
    assert turn1["warn_needed"] is False
    assert turn1["should_reset"] is False

    # 2. Turn 2: 2,600 tokens (76% cumulative) -> Triggers warning watermark
    turn2 = manager.record_turn(tokens_used=2600, action="JUMP")
    assert turn2["utilization"] == 0.76
    assert turn2["warn_needed"] is True
    assert turn2["should_reset"] is False

    # 3. Turn 3: 1,000 tokens (86% cumulative) -> Triggers dynamic reset watermark
    turn3 = manager.record_turn(tokens_used=1000, action="THROW")
    assert turn3["utilization"] == 0.86
    assert turn3["should_reset"] is True
    assert "Token context watermark reached: 86.0%" in turn3["reset_reason"]

    # Advance session resets tokens and clears warning
    adv = manager.advance_session()
    assert adv["session_index"] == 1
    assert adv["new_session_id"] == "session_001"
    assert manager.cumulative_tokens == 0
    assert manager.warning_issued is False


def test_dynamic_context_reset_manager_entropy_stagnation(temp_workspace: Path):
    """Test behavioral stagnation reset when action entropy collapses due to idling loops."""
    memory = DualMemoryManager(temp_workspace)
    manager = DynamicContextResetManager(
        memory_manager=memory,
        max_context_tokens=100_000,
        min_action_entropy=0.40,
        entropy_window=10,
    )

    # Simulate 10 turns of identical action (cyclic entrapment: IDLE, IDLE, IDLE...)
    for step in range(9):
        status = manager.record_turn(tokens_used=100, action="IDLE")
        assert status["should_reset"] is False

    # 10th consecutive identical action causes Shannon entropy to hit 0.0 < 0.40
    status_10 = manager.record_turn(tokens_used=100, action="IDLE")
    assert status_10["action_entropy"] == pytest.approx(0.0)
    assert status_10["should_reset"] is True
    assert "Behavioral action entropy collapsed" in status_10["reset_reason"]
