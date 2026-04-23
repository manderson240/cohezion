"""Tests for PhiScoreJudger reward mapping."""

from __future__ import annotations

import pytest

from cohezion.agentjet.judger import PhiScoreJudger


@pytest.fixture
def judger() -> PhiScoreJudger:
    return PhiScoreJudger()


def test_judge_phi_1_0_returns_1_0(judger: PhiScoreJudger) -> None:
    result = judger.judge({"phi_score": 1.0})
    assert result == pytest.approx(1.0)


def test_judge_phi_0_7_returns_0_4(judger: PhiScoreJudger) -> None:
    # phi=0.7 is exactly at hiho_high boundary: 0.7 * 2 - 1 = 0.4
    result = judger.judge({"phi_score": 0.7})
    assert result == pytest.approx(0.4)


def test_judge_phi_0_85_returns_0_7(judger: PhiScoreJudger) -> None:
    # phi=0.85: 0.85 * 2 - 1 = 0.7
    result = judger.judge({"phi_score": 0.85})
    assert result == pytest.approx(0.7)


def test_judge_phi_0_4_is_hiho_band_start(judger: PhiScoreJudger) -> None:
    # phi=0.4 is exactly at hiho_low: (0.4 - 0.4) / 0.3 * 0.2 = 0.0
    result = judger.judge({"phi_score": 0.4})
    assert result == pytest.approx(0.0)
    # Confirm it is NOT a HIHO violation (which would be -1.0)
    assert result >= 0.0


def test_judge_phi_0_55_hiho_band(judger: PhiScoreJudger) -> None:
    # phi=0.55 in [0.4, 0.7): (0.55 - 0.4) / 0.3 * 0.2 = 0.1
    result = judger.judge({"phi_score": 0.55})
    assert result == pytest.approx(0.1)


def test_judge_phi_0_39_hiho_violation(judger: PhiScoreJudger) -> None:
    # phi=0.39 < hiho_low=0.4 → hard penalty
    result = judger.judge({"phi_score": 0.39})
    assert result == -1.0


def test_judge_phi_0_0_returns_negative_one(judger: PhiScoreJudger) -> None:
    result = judger.judge({"phi_score": 0.0})
    assert result == -1.0


def test_batch_judge_returns_list_of_rewards(judger: PhiScoreJudger) -> None:
    rollouts = [
        {"phi_score": 1.0},
        {"phi_score": 0.55},
        {"phi_score": 0.0},
    ]
    rewards = judger.batch_judge(rollouts)
    assert len(rewards) == 3
    assert rewards[0] == pytest.approx(1.0)
    assert rewards[1] == pytest.approx(0.1)
    assert rewards[2] == -1.0


def test_configurable_boundaries_low_0_3_high_0_8() -> None:
    j = PhiScoreJudger(hiho_low=0.3, hiho_high=0.8)
    # phi=0.5 in band [0.3, 0.8): (0.5 - 0.3) / 0.5 * 0.2 = 0.08
    result = j.judge({"phi_score": 0.5})
    assert result == pytest.approx(0.08)
    # phi=0.29 → violation
    assert j.judge({"phi_score": 0.29}) == -1.0
    # phi=0.9 → positive: 0.9*2-1 = 0.8
    assert j.judge({"phi_score": 0.9}) == pytest.approx(0.8)


def test_invalid_boundaries_raises_value_error() -> None:
    with pytest.raises(ValueError, match="HIHO band"):
        PhiScoreJudger(hiho_low=0.9, hiho_high=0.1)


def test_invalid_boundary_equal_raises_value_error() -> None:
    with pytest.raises(ValueError):
        PhiScoreJudger(hiho_low=0.5, hiho_high=0.5)


def test_judge_missing_phi_score_returns_negative_one(judger: PhiScoreJudger) -> None:
    result = judger.judge({})
    assert result == -1.0


def test_judge_non_numeric_phi_score_returns_negative_one(judger: PhiScoreJudger) -> None:
    result = judger.judge({"phi_score": "not_a_number"})
    assert result == -1.0
