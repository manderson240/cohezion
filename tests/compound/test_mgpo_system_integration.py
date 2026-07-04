"""SR1-level system integration test: VaultNeuron → MGPO → refinement cascade.

V-Model level: SR1 (System Requirement 1) — right-side verification.

Validates the full Loop-4 "return arrow":
  VaultNeuronWriter.query_category_success_rate()
    → SkillRefiner.mgpo_weight()        (real computation)
    → SkillRefiner.prioritized_skills() (real computation)
    → CompoundExecutor._batch_mgpo_refine()
    → SkillRefiner.refine() called with boundary skill first

Three skills with distinct success rates:
  "boundary_skill" sr=0.50 → weight ≈ 1.000  (capability boundary — should go first)
  "mastered_skill" sr=1.00 → weight ≈ 0.082  (fully mastered — deprioritised)
  "stuck_skill"    sr=0.00 → weight ≈ 0.082  (never succeeds  — deprioritised)

Unlike the MD-level tests (test_executor_mgpo_wiring.py), these tests wire a REAL
SkillRefiner so the MGPO math runs end-to-end. Only the vault I/O layer
(VaultNeuronWriter.get_instance) is mocked.
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.skill_refiner import SkillRefiner


# ── fixture data ──────────────────────────────────────────────────────────────

_SKILL_SUCCESS_RATES: dict[str, float] = {
    "boundary_skill": 0.50,  # capability boundary → highest MGPO weight
    "mastered_skill": 1.00,  # fully mastered     → low weight (symmetric)
    "stuck_skill": 0.00,     # never succeeds     → low weight (symmetric)
}


def _expected_weight(sr: float, gamma: float = 5.0) -> float:
    return math.exp(-gamma * abs(sr - 0.5))


def _vault_neuron_mock() -> MagicMock:
    """Return a VaultNeuronWriter stub with controlled per-skill success rates."""
    mock = MagicMock()
    mock.query_category_success_rate.side_effect = (
        lambda skill_name: _SKILL_SUCCESS_RATES.get(skill_name)
    )
    return mock


# ── SR1 structural guard ───────────────────────────────────────────────────────


def test_sr1_vault_neuron_interface_accessible():
    """VaultNeuronWriter.get_instance() must be importable — structural smoke-test."""
    from cohezion.learning.vault_neuron_reader import VaultNeuronWriter

    assert hasattr(VaultNeuronWriter, "get_instance")
    assert hasattr(VaultNeuronWriter, "reset_instance")


# ── SR1 weight computation (real SkillRefiner, mocked vault) ─────────────────


def test_mgpo_weight_reads_success_rate_from_vault():
    """SkillRefiner.mgpo_weight() must delegate to VaultNeuronWriter."""
    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance",
        return_value=_vault_neuron_mock(),
    ):
        refiner = SkillRefiner(mcp_client=None)
        w_boundary = refiner.mgpo_weight("boundary_skill")
        w_mastered = refiner.mgpo_weight("mastered_skill")
        w_stuck = refiner.mgpo_weight("stuck_skill")

    assert abs(w_boundary - _expected_weight(0.50)) < 1e-9, (
        f"boundary weight expected {_expected_weight(0.50):.4f}, got {w_boundary:.4f}"
    )
    assert abs(w_mastered - _expected_weight(1.00)) < 1e-9
    assert abs(w_stuck - _expected_weight(0.00)) < 1e-9


def test_boundary_skill_weight_exceeds_mastered_and_stuck():
    """MGPO must deprioritise both mastered and stuck skills below boundary."""
    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance",
        return_value=_vault_neuron_mock(),
    ):
        refiner = SkillRefiner(mcp_client=None)
        w_boundary = refiner.mgpo_weight("boundary_skill")
        w_mastered = refiner.mgpo_weight("mastered_skill")
        w_stuck = refiner.mgpo_weight("stuck_skill")

    assert w_boundary > w_mastered, "boundary must outweigh mastered"
    assert w_boundary > w_stuck, "boundary must outweigh stuck"
    # symmetry: |1.0 - 0.5| == |0.0 - 0.5|
    assert abs(w_mastered - w_stuck) < 1e-9, (
        "mastered and stuck are equidistant from 0.5 — must share equal weight"
    )


# ── SR1 ordering (real prioritized_skills) ────────────────────────────────────


def test_boundary_skill_ranks_first_in_prioritized_skills():
    """prioritized_skills() must place the capability-boundary skill at index 0."""
    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance",
        return_value=_vault_neuron_mock(),
    ):
        refiner = SkillRefiner(mcp_client=None)
        # Present all three in the worst possible order for a trivial sort
        candidates = ["mastered_skill", "stuck_skill", "boundary_skill"]
        ordered = refiner.prioritized_skills(candidates)

    assert ordered[0] == "boundary_skill", (
        f"prioritized_skills must rank boundary_skill first; got {ordered}"
    )


def test_prioritized_skills_descending_weight_order():
    """Each successive skill returned by prioritized_skills must have ≤ weight."""
    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance",
        return_value=_vault_neuron_mock(),
    ):
        refiner = SkillRefiner(mcp_client=None)
        candidates = list(_SKILL_SUCCESS_RATES.keys())
        ordered = refiner.prioritized_skills(candidates)
        weights = [refiner.mgpo_weight(s) for s in ordered]

    for i in range(len(weights) - 1):
        assert weights[i] >= weights[i + 1], (
            f"Weight must be non-increasing: position {i} ({weights[i]:.4f}) < "
            f"position {i+1} ({weights[i+1]:.4f})"
        )


# ── SR1 end-to-end cascade (real SkillRefiner + real CompoundExecutor) ────────


def test_batch_refine_fires_boundary_skill_first():
    """SR1 discriminating test: boundary skill must be first arg to refine()."""
    refine_calls: list[str] = []

    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance",
        return_value=_vault_neuron_mock(),
    ):
        refiner = SkillRefiner(mcp_client=None)
        # Spy on refine() — capture calls without touching the file system
        refiner.refine = lambda skill_name, **kwargs: refine_calls.append(skill_name)

        ex = CompoundExecutor(
            mcp_client=None,
            skill_refiner=refiner,
            enable_skill_refinement=True,
            enable_guardrails=False,
        )
        # 10 accumulated entries: 4 boundary, 3 mastered, 3 stuck (all three categories)
        ex._recent_skill_names = (
            ["boundary_skill"] * 4 + ["mastered_skill"] * 3 + ["stuck_skill"] * 3
        )
        ex._batch_mgpo_refine(top_k=3)

    assert refine_calls, "_batch_mgpo_refine must call refine() at least once"
    assert refine_calls[0] == "boundary_skill", (
        f"First refine() call must be boundary_skill (highest MGPO weight); "
        f"got {refine_calls}"
    )
    # Discriminating: mastered_skill must NOT appear before boundary_skill
    if "mastered_skill" in refine_calls:
        assert refine_calls.index("boundary_skill") < refine_calls.index("mastered_skill"), (
            "boundary_skill must precede mastered_skill in refine() call order"
        )


def test_batch_refine_calls_refine_for_top_k_skills():
    """_batch_mgpo_refine(top_k=2) must call refine() exactly twice."""
    refine_calls: list[str] = []

    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance",
        return_value=_vault_neuron_mock(),
    ):
        refiner = SkillRefiner(mcp_client=None)
        refiner.refine = lambda skill_name, **kwargs: refine_calls.append(skill_name)

        ex = CompoundExecutor(
            mcp_client=None,
            skill_refiner=refiner,
            enable_skill_refinement=True,
            enable_guardrails=False,
        )
        ex._recent_skill_names = list(_SKILL_SUCCESS_RATES.keys()) * 4
        ex._batch_mgpo_refine(top_k=2)

    assert len(refine_calls) == 2, (
        f"top_k=2 must produce exactly 2 refine() calls; got {len(refine_calls)}"
    )


# ── SR1 accumulator lifecycle ─────────────────────────────────────────────────


def test_accumulator_drained_after_batch():
    """_recent_skill_names must be empty after _batch_mgpo_refine() completes."""
    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance",
        return_value=_vault_neuron_mock(),
    ):
        refiner = SkillRefiner(mcp_client=None)
        refiner.refine = MagicMock(return_value=None)

        ex = CompoundExecutor(
            mcp_client=None,
            skill_refiner=refiner,
            enable_skill_refinement=True,
            enable_guardrails=False,
        )
        ex._recent_skill_names = list(_SKILL_SUCCESS_RATES.keys()) * 4
        ex._batch_mgpo_refine()

    assert ex._recent_skill_names == [], (
        "_recent_skill_names must be empty after batch refinement drains it"
    )


def test_check_mgpo_batch_fires_at_threshold_not_before():
    """_check_mgpo_batch must fire exactly at MGPO_BATCH_SIZE, not one below."""
    batch_size = CompoundExecutor.MGPO_BATCH_SIZE
    refine_calls: list[str] = []

    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter.get_instance",
        return_value=_vault_neuron_mock(),
    ):
        refiner = SkillRefiner(mcp_client=None)
        refiner.refine = lambda skill_name, **kwargs: refine_calls.append(skill_name)

        ex = CompoundExecutor(
            mcp_client=None,
            skill_refiner=refiner,
            enable_skill_refinement=True,
            enable_guardrails=False,
        )

        # Fill to batch_size - 1: must NOT fire
        ex._recent_skill_names = ["boundary_skill"] * (batch_size - 1)
        ex._check_mgpo_batch()
        assert refine_calls == [], (
            f"Batch must not fire below threshold ({batch_size - 1} < {batch_size})"
        )

        # Push to exactly batch_size: MUST fire
        ex._recent_skill_names.append("boundary_skill")
        ex._check_mgpo_batch()
        assert refine_calls, (
            f"Batch must fire at threshold ({batch_size} == {batch_size})"
        )
