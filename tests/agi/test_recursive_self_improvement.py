"""Unit tests for Recursive Self-Improvement Engine (Cohezion improving Cohezion)."""

from __future__ import annotations

import pytest

from cohezion.agi.recursive_self_improvement import (
    RecursiveSelfImprovementEngine,
    SelfImprovementResult,
)


@pytest.mark.asyncio
async def test_recursive_self_improvement_cycle_execution() -> None:
    """Verify end-to-end execution of a verified recursive self-improvement cycle."""
    engine = RecursiveSelfImprovementEngine()
    result = await engine.execute_recursive_improvement_cycle()

    assert isinstance(result, SelfImprovementResult)
    assert result.cycle_id.startswith("rsi_cycle_")
    assert len(result.diagnosed_optimizations) >= 4

    # Terminal-RSI Invariant: Verified success must score >= 1.0
    assert result.terminal_rsi_spr >= 1.0
    assert result.terminal_rsi_spr < 2.0

    # Negentropy Invariant: Delta S <= 0 (state variance/entropy reduction)
    assert result.delta_entropy <= 0.0

    # ZKFV Formal Verification Invariant
    assert result.zkfv_verified is True

    # Poincaré Manifold Isomorphic Alignment Invariant
    assert 0.0 <= result.poincare_alignment_score <= 1.0

    # Review Score Invariant
    assert result.review_score > 0.0

    # Execution Latency Invariant
    assert result.execution_time_ms > 0.0


@pytest.mark.asyncio
async def test_diagnosed_optimizations_cover_hardware_and_polyglot() -> None:
    """Verify that self-diagnosis dynamically audits Zen 5, AVX-512, and Rust bridges."""
    engine = RecursiveSelfImprovementEngine()
    result = await engine.execute_recursive_improvement_cycle()

    diagnoses_text = " ".join(result.diagnosed_optimizations)
    assert "Zen 5" in diagnoses_text
    assert "AVX-512" in diagnoses_text
    assert "Poincaré" in diagnoses_text
    assert "Terminal-RSI" in diagnoses_text


@pytest.mark.asyncio
async def test_spr_reward_failure_vs_success_separation() -> None:
    """Verify strict mathematical separation of unverified vs verified outcomes."""
    engine = RecursiveSelfImprovementEngine()

    # Unverified / partial failure must score strictly < 1.0
    r_fail = engine.spr.compute_reward(strict_success=False, passed_checks=10)
    assert 0.0 <= r_fail < 1.0

    # Verified success must score in [1.0, 2.0)
    r_success = engine.spr.compute_reward(strict_success=True, passed_checks=10)
    assert 1.0 <= r_success < 2.0
    assert r_success > r_fail
