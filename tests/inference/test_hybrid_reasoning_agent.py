"""Tests for Hybrid Reasoning Agent architecture (arXiv:2610.18861).

Verifies:
1. HybridLink residual adapter R(h_t) and Flume 256D manifold projection.
2. Continuous Working Memory multi-turn state accumulation without token re-encoding.
3. LatentController dynamic transitions (<latent> -> </latent>) and pseudo-text decoding.
4. HybridReasoningAgent end-to-end execution, tool action, and token reduction.
5. Exact latent-context rollout replay for hybrid policy factorization (Proposition 4.1).
"""

from __future__ import annotations

import numpy as np

from cohezion.inference.hybrid_reasoning_agent import (
    ContinuousWorkingMemory,
    HybridLink,
    HybridReasoningAgent,
    HybridStep,
    LatentController,
    Mode,
    TokenType,
)


def test_hybrid_link_residual_projection():
    """Verify HybridLink residual transformation R(h_t) and Flume 256D projection."""
    d_model = 768
    d_flume = 256
    link = HybridLink(d_model=d_model, d_flume=d_flume, seed=42)

    rng = np.random.default_rng(100)
    h_t = rng.normal(0, 1.0, d_model).astype(np.float32)

    # 1. Forward residual check
    e_next = link.forward(h_t)
    assert e_next.shape == (d_model,)
    # Residual property: e_next is not identical to h_t but strongly correlated
    assert not np.allclose(e_next, h_t)
    cos_sim = float(np.dot(e_next, h_t) / (np.linalg.norm(e_next) * np.linalg.norm(h_t)))
    assert cos_sim > 0.50

    # 2. Flume 256D manifold projection
    z_flume = link.encode_flume(h_t)
    assert z_flume.shape == (d_flume,)
    assert np.isclose(np.linalg.norm(z_flume), 1.0, atol=1e-5)


def test_continuous_working_memory():
    """Verify lossless multi-turn continuous working memory and deterministic hashing."""
    memory = ContinuousWorkingMemory(session_id="session_test_42")

    step1 = HybridStep(
        step_index=0,
        mode=Mode.TEXT,
        token_type=TokenType.TEXT,
        content="Analyze RSNA knee MRI slice sequence",
    )
    step2 = HybridStep(
        step_index=1,
        mode=Mode.LATENT,
        token_type=TokenType.LATENT,
        content="[latent_vector_step_1]",
        flume_z=[0.1] * 256,
        decoded_thought="copula_rank_normalization",
    )
    step3 = HybridStep(
        step_index=2,
        mode=Mode.TEXT,
        token_type=TokenType.TOOL_ACTION,
        content="CALL autoharness_verify()",
    )

    memory.append_step(step1)
    memory.append_step(step2)
    memory.append_step(step3)

    assert memory.total_memory_steps() == 3
    hash1 = memory.get_context_hash()
    assert isinstance(hash1, str)
    assert len(hash1) == 64

    # Appending another step alters the context hash deterministically
    step4 = HybridStep(
        step_index=3,
        mode=Mode.TEXT,
        token_type=TokenType.TEXT,
        content="Final prediction confirmed.",
    )
    memory.append_step(step4)
    hash2 = memory.get_context_hash()
    assert hash1 != hash2


def test_latent_controller_transitions():
    """Verify dynamic mode transitions and pseudo-text interpretability decoding."""
    controller = LatentController(d_model=768, exit_similarity_threshold=0.85, max_latent_steps=4)

    assert controller.entry_anchor == "<latent>"
    assert controller.exit_anchor == "</latent>"

    # 1. Exit condition via max steps
    dummy_vec = np.ones(768, dtype=np.float32)
    assert controller.should_exit_latent(dummy_vec, current_latent_step=1) is False
    assert controller.should_exit_latent(dummy_vec, current_latent_step=4) is True

    # 2. Pseudo-text interpretability decoding
    concept = controller.decode_latent_thought(dummy_vec)
    assert isinstance(concept, str)
    assert len(concept) > 0


def test_hybrid_turn_execution_and_token_reduction():
    """Verify complete hybrid turn execution, tool invocation, and token reduction."""
    agent = HybridReasoningAgent(
        session_id="hybrid_sess_001",
        d_model=768,
        d_flume=256,
    )

    tool_called = False

    def mock_autoharness(args_str: str) -> str:
        nonlocal tool_called
        tool_called = True
        return '{"status": "INVARIANT_VERIFIED", "ast_passed": true}'

    tools = {"autoharness_verify": mock_autoharness}

    trajectory = agent.execute_hybrid_turn(
        user_input="Find first-principles D4 dihedral symmetry for ARC task 007bbfb7",
        turn_index=1,
        tools=tools,
    )

    assert tool_called is True
    assert trajectory.latent_steps_count >= 1
    assert trajectory.text_steps_count >= 2
    assert trajectory.total_tokens_reduced > 0
    assert "Synthesized invariant solution" in trajectory.final_output

    # Check that latent steps were recorded with Flume vectors and decoded thoughts
    for l_step in trajectory.latent_steps:
        assert l_step.mode == Mode.LATENT
        assert l_step.flume_z is not None
        assert len(l_step.flume_z) == 256
        assert l_step.decoded_thought is not None


def test_exact_latent_rollout_replay():
    """Verify exact latent-context replay for Hybrid policy factorization (Proposition 4.1)."""
    agent = HybridReasoningAgent(
        session_id="hybrid_sess_replay",
        d_model=768,
        d_flume=256,
    )

    trajectory = agent.execute_hybrid_turn(
        user_input="Optimize RSNA knee inference window bounds",
        turn_index=1,
    )

    replay_info = agent.replay_hybrid_rollout(trajectory)
    assert replay_info["status"] == "REPLAY_EXACT"
    assert replay_info["policy_factorization_valid"] is True
    assert replay_info["sampled_text_count"] == len(trajectory.sampled_text_steps)
    assert replay_info["latent_context_count"] == len(trajectory.latent_steps)
    assert isinstance(replay_info["replay_context_hash"], str)
    assert replay_info["estimated_token_savings_pct"] > 50.0
