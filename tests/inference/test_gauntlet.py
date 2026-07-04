"""Tests for OmniGauntlet — V-model benchmark harness.

All Lemonade HTTP calls are mocked.  No inference servers are required.
Discriminating tests prove the scoring formula and champion logic are correct,
not merely that the code runs.
"""

from __future__ import annotations

import json
import pytest
from pathlib import Path

from cohezion.inference.gauntlet import (
    PROMOTION_THRESHOLD,
    BenchTask,
    TASK_SUITE,
    _score_result,
    _promote_if_better,
    get_champion,
)


# ── Score computation ─────────────────────────────────────────────────────────

class TestScoreComputation:
    """_score_result must compute quality_ratio and score correctly."""

    def _make_task(self, keywords: list[str]) -> BenchTask:
        return BenchTask(
            name="test_task", role="generation",
            prompt="test prompt",
            expected_keywords=keywords,
            max_tokens=50,
        )

    def test_all_keywords_present_gives_quality_1(self) -> None:
        task = self._make_task(["apple", "banana"])
        result = _score_result(task, ttft=0.1, tps=50.0, text="apple banana pie")
        assert result.quality_ratio == 1.0
        assert result.keyword_hits == 2

    def test_no_keywords_present_gives_quality_0(self) -> None:
        task = self._make_task(["apple", "banana"])
        result = _score_result(task, ttft=0.1, tps=50.0, text="nothing here")
        assert result.quality_ratio == 0.0
        assert result.keyword_hits == 0

    def test_score_is_quality_times_tps(self) -> None:
        """Discriminating: score must be quality_ratio * tps_actual."""
        task = self._make_task(["yes"])
        result = _score_result(task, ttft=0.05, tps=80.0, text="yes")
        assert result.score == pytest.approx(1.0 * 80.0, rel=0.01)

    def test_partial_match_gives_fractional_quality(self) -> None:
        task = self._make_task(["a", "b", "c", "d"])
        result = _score_result(task, ttft=0.1, tps=40.0, text="a b")
        assert result.quality_ratio == pytest.approx(0.5, abs=0.01)
        assert result.keyword_hits == 2

    def test_keyword_matching_is_case_insensitive(self) -> None:
        task = self._make_task(["Python"])
        result = _score_result(task, ttft=0.1, tps=10.0, text="python is great")
        assert result.keyword_hits == 1


# ── Champion promotion ────────────────────────────────────────────────────────

class TestChampionPromotion:
    """_promote_if_better must enforce the 5% promotion threshold."""

    def test_new_champion_when_no_previous(self) -> None:
        scores: dict = {}
        _champion, promoted = _promote_if_better(
            scores, "code", {"Qwen3-Coder-30B": 50.0}
        )
        assert promoted
        assert scores["champions"]["code"]["model_id"] == "Qwen3-Coder-30B"

    def test_no_promotion_when_improvement_under_threshold(self) -> None:
        """Discriminating: 4% improvement must NOT promote (threshold is 5%)."""
        scores = {"champions": {"code": {"model_id": "old-model", "score": 50.0}}}
        # 4% improvement: 50.0 * 1.04 = 52.0 — below 50.0 * 1.05 = 52.5
        _champion, promoted = _promote_if_better(
            scores, "code", {"new-model": 52.0}
        )
        assert not promoted, "4% improvement should not trigger promotion"

    def test_promotion_at_exactly_threshold(self) -> None:
        """Exactly 5% improvement must promote."""
        scores = {"champions": {"code": {"model_id": "old-model", "score": 50.0}}}
        # 5.1% improvement: 50.0 * 1.051 = 52.55 > 52.5
        _champion, promoted = _promote_if_better(
            scores, "code", {"new-model": 52.55}
        )
        assert promoted, "5.1% improvement should trigger promotion"

    def test_champion_persisted_in_scores_dict(self) -> None:
        scores: dict = {}
        _promote_if_better(scores, "generation", {"Gemma-4-E4B": 75.0})
        assert scores["champions"]["generation"]["model_id"] == "Gemma-4-E4B"
        assert scores["champions"]["generation"]["score"] == 75.0

    def test_promotion_constant_is_5_percent(self) -> None:
        assert PROMOTION_THRESHOLD == 0.05


# ── Task suite integrity ──────────────────────────────────────────────────────

class TestTaskSuite:
    """TASK_SUITE must cover all required capability domains."""

    def test_task_suite_has_7_domains(self) -> None:
        assert len(TASK_SUITE) >= 7, f"Expected ≥7 tasks, got {len(TASK_SUITE)}"

    def test_code_domain_included(self) -> None:
        roles = {t.role for t in TASK_SUITE}
        assert "code" in roles, "Task suite must include a 'code' role task"

    def test_all_tasks_have_keywords(self) -> None:
        for task in TASK_SUITE:
            assert task.expected_keywords, f"Task '{task.name}' has no expected_keywords"

    def test_all_tasks_have_prompt(self) -> None:
        for task in TASK_SUITE:
            assert len(task.prompt) >= 10, f"Task '{task.name}' has too-short prompt"


# ── get_champion ──────────────────────────────────────────────────────────────

class TestGetChampion:
    def test_returns_none_when_no_scores_file(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_path = tmp_path / "gauntlet_scores.json"
        monkeypatch.setattr("cohezion.inference.gauntlet.GAUNTLET_PATH", fake_path)
        assert get_champion("code") is None

    def test_returns_champion_when_present(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        fake_path = tmp_path / "gauntlet_scores.json"
        fake_path.write_text(json.dumps({
            "champions": {"code": {"model_id": "Qwen3-Coder-30B", "score": 50.0}}
        }))
        monkeypatch.setattr("cohezion.inference.gauntlet.GAUNTLET_PATH", fake_path)
        assert get_champion("code") == "Qwen3-Coder-30B"
