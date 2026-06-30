"""TDD tests for MGPO capability-boundary prioritization in SkillRefiner (Task #16).

MGPO = Marginal Gain Prioritization at the Operational boundary.

The formula: w(skill) = exp(-γ * |success_rate - 0.5|)

Skills at success_rate ≈ 0.5 (capability boundary) get weight ≈ 1.0 (highest
priority). Skills that are already mastered (≈1.0) or completely stuck (≈0.0)
get lower weights — they yield less improvement per refinement token spent.

VaultNeuronWriter.query_category_success_rate() is the live data feed.

These tests MUST fail before the implementation lands:
  - test_mgpo_weight_exists             → AttributeError until added
  - test_mgpo_weight_boundary           → correct math required
  - test_prioritized_skills_ordering    → method missing until added
"""

from __future__ import annotations

import math
from unittest.mock import MagicMock, patch


from cohezion.compound.skill_refiner import SkillRefiner


# ── math invariants ──────────────────────────────────────────────────────────


def test_mgpo_weight_exists():
    """SkillRefiner must expose mgpo_weight(skill_name, gamma) classmethod or method."""
    refiner = SkillRefiner()
    assert hasattr(refiner, "mgpo_weight"), "mgpo_weight() method missing from SkillRefiner"


def test_mgpo_weight_boundary_is_one():
    """success_rate=0.5 → weight=1.0 regardless of gamma (exp(0) = 1)."""
    refiner = SkillRefiner()
    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter"
    ) as mock_vnw_cls:
        mock_vnw = MagicMock()
        mock_vnw.query_category_success_rate.return_value = 0.5
        mock_vnw_cls.get_instance.return_value = mock_vnw

        w = refiner.mgpo_weight("routing")
        assert abs(w - 1.0) < 1e-9, f"Expected weight=1.0 at boundary, got {w}"


def test_mgpo_weight_mastered_is_lower():
    """success_rate=1.0 → weight < 1.0 (skill already mastered, deprioritize)."""
    refiner = SkillRefiner()
    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter"
    ) as mock_vnw_cls:
        mock_vnw = MagicMock()
        mock_vnw.query_category_success_rate.return_value = 1.0
        mock_vnw_cls.get_instance.return_value = mock_vnw

        w = refiner.mgpo_weight("routing", gamma=5.0)
        assert w < 1.0, "Mastered skill (success_rate=1.0) must be deprioritized vs boundary"
        expected = math.exp(-5.0 * abs(1.0 - 0.5))
        assert abs(w - expected) < 1e-9, f"Weight must follow exp(-γ|sr-0.5|), got {w}"


def test_mgpo_weight_stuck_is_lower():
    """success_rate=0.0 → weight < 1.0 (skill stuck, deprioritize vs boundary)."""
    refiner = SkillRefiner()
    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter"
    ) as mock_vnw_cls:
        mock_vnw = MagicMock()
        mock_vnw.query_category_success_rate.return_value = 0.0
        mock_vnw_cls.get_instance.return_value = mock_vnw

        w = refiner.mgpo_weight("routing", gamma=5.0)
        assert w < 1.0, "Stuck skill (success_rate=0.0) must be deprioritized vs boundary"
        # By symmetry, same as mastered
        expected = math.exp(-5.0 * 0.5)
        assert abs(w - expected) < 1e-9


def test_mgpo_weight_symmetry():
    """Weight is symmetric: sr=0.3 and sr=0.7 must produce identical weights."""
    refiner = SkillRefiner()
    gamma = 5.0

    def make_mock(sr: float) -> MagicMock:
        m = MagicMock()
        m.query_category_success_rate.return_value = sr
        return m

    with patch("cohezion.compound.skill_refiner.VaultNeuronWriter") as mock_cls:
        mock_cls.get_instance.return_value = make_mock(0.3)
        w_low = refiner.mgpo_weight("cat", gamma=gamma)

        mock_cls.get_instance.return_value = make_mock(0.7)
        w_high = refiner.mgpo_weight("cat", gamma=gamma)

    assert abs(w_low - w_high) < 1e-9, (
        f"MGPO weight must be symmetric: sr=0.3 gave {w_low}, sr=0.7 gave {w_high}"
    )


def test_mgpo_weight_no_data_returns_one():
    """When VaultNeuronWriter returns None (no data), default weight=1.0 (treat as boundary)."""
    refiner = SkillRefiner()
    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter"
    ) as mock_vnw_cls:
        mock_vnw = MagicMock()
        mock_vnw.query_category_success_rate.return_value = None
        mock_vnw_cls.get_instance.return_value = mock_vnw

        w = refiner.mgpo_weight("new_skill")
        assert abs(w - 1.0) < 1e-9, "No-data → weight=1.0 (treat as unexplored boundary)"


# ── ordering / queue logic ────────────────────────────────────────────────────


def test_prioritized_skills_exists():
    """SkillRefiner must expose prioritized_skills(skill_names, gamma) method."""
    refiner = SkillRefiner()
    assert hasattr(refiner, "prioritized_skills"), (
        "prioritized_skills() method missing from SkillRefiner"
    )


def test_prioritized_skills_ordering():
    """Skills at capability boundary (sr≈0.5) must rank above mastered/stuck skills."""
    refiner = SkillRefiner()

    success_rates = {
        "routing": 0.5,   # boundary — should be first
        "search": 1.0,    # mastered — lower priority
        "codegen": 0.0,   # stuck — lower priority
        "planning": 0.48, # near-boundary — high priority
    }

    def fake_query(category: str, limit: int = 100) -> float | None:
        return success_rates.get(category)

    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter"
    ) as mock_vnw_cls:
        mock_vnw = MagicMock()
        mock_vnw.query_category_success_rate.side_effect = fake_query
        mock_vnw_cls.get_instance.return_value = mock_vnw

        ordered = refiner.prioritized_skills(list(success_rates.keys()), gamma=5.0)

    assert ordered[0] in ("routing", "planning"), (
        f"Boundary skill must rank first; got {ordered[0]}"
    )
    assert "search" not in ordered[:2] and "codegen" not in ordered[:2], (
        "Mastered and stuck skills must not be in top-2"
    )
    assert len(ordered) == 4, "All skills must be returned (sorted)"


def test_prioritized_skills_empty_input():
    """prioritized_skills([]) must return [] without error."""
    refiner = SkillRefiner()
    with patch("cohezion.compound.skill_refiner.VaultNeuronWriter"):
        result = refiner.prioritized_skills([])
    assert result == []


def test_prioritized_skills_descending_weight():
    """prioritized_skills must sort descending by MGPO weight."""
    refiner = SkillRefiner()

    rates = {"a": 0.5, "b": 0.8, "c": 0.2, "d": 0.51}

    def fake_query(category: str, limit: int = 100) -> float | None:
        return rates.get(category)

    with patch(
        "cohezion.compound.skill_refiner.VaultNeuronWriter"
    ) as mock_vnw_cls:
        mock_vnw = MagicMock()
        mock_vnw.query_category_success_rate.side_effect = fake_query
        mock_vnw_cls.get_instance.return_value = mock_vnw

        ordered = refiner.prioritized_skills(list(rates.keys()), gamma=5.0)
        weights = [
            math.exp(-5.0 * abs((rates.get(s) or 0.5) - 0.5)) for s in ordered
        ]

    for i in range(len(weights) - 1):
        assert weights[i] >= weights[i + 1], (
            f"Weight must be non-increasing: {ordered[i]}={weights[i]:.4f} "
            f"> {ordered[i+1]}={weights[i+1]:.4f}"
        )
