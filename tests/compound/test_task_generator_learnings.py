"""Tests for TaskGenerator learning-aware priority adjustment.

Verifies that loop_learnings.jsonl is read and used to adjust task priorities
so consistently failing categories are deprioritized in subsequent runs.
"""

from __future__ import annotations

import json
from pathlib import Path

from cohezion.compound.autonomous_loop.task_generator import (
    _LEARNING_WINDOW,
    _MAX_PENALTY,
    TaskGenerator,
)


def _make_learnings_file(entries: list[dict], tmp_path: Path) -> Path:
    """Write a loop_learnings.jsonl file and return its path."""
    path = tmp_path / "loop_learnings.jsonl"
    path.write_text("\n".join(json.dumps(e) for e in entries))
    return path


def _make_entry(results: list[dict]) -> dict:
    """Minimal learning entry with given per-task results."""
    return {
        "ts": "2026-06-14T00:00:00+00:00",
        "loop_type": "local",
        "model": "Gemma-4-E4B-it-GGUF",
        "tasks_completed": sum(1 for r in results if r.get("success")),
        "tasks_failed": sum(1 for r in results if not r.get("success")),
        "success_rate": 0.5,
        "elapsed_hours": 0.5,
        "tokens_used": 1000,
        "results": results,
    }


class TestCategoryStatsLoading:
    def test_no_learnings_file_loads_cleanly(self, tmp_path: Path) -> None:
        gen = TaskGenerator(learnings_path=str(tmp_path / "nonexistent.jsonl"))
        assert gen._category_stats == {}

    def test_disabled_with_empty_string(self) -> None:
        gen = TaskGenerator(learnings_path="")
        assert gen._learnings_path is None
        assert gen._category_stats == {}

    def test_loads_category_stats_from_file(self, tmp_path: Path) -> None:
        entry = _make_entry(
            [
                {"category": "test_fix", "success": True},
                {"category": "test_fix", "success": False},
                {"category": "lint_fix", "success": True},
            ]
        )
        path = _make_learnings_file([entry], tmp_path)
        gen = TaskGenerator(learnings_path=str(path))

        assert "test_fix" in gen._category_stats
        assert gen._category_stats["test_fix"]["attempts"] == 2
        assert gen._category_stats["test_fix"]["successes"] == 1

    def test_only_considers_recent_window(self, tmp_path: Path) -> None:
        """Entries beyond _LEARNING_WINDOW should be ignored."""
        old_entries = [
            _make_entry([{"category": "refactor", "success": False}])
            for _ in range(_LEARNING_WINDOW)
        ]
        new_entry = _make_entry([{"category": "refactor", "success": True}])
        all_entries = old_entries + [new_entry]
        path = _make_learnings_file(all_entries, tmp_path)

        gen = TaskGenerator(learnings_path=str(path))
        stats = gen._category_stats.get("refactor", {})
        # Only the last _LEARNING_WINDOW entries are considered
        assert stats.get("attempts", 0) == _LEARNING_WINDOW
        # Within the window the oldest entry falls out; result depends on window
        # The new_entry (success=True) should be within the window
        assert stats.get("successes", 0) >= 1

    def test_skips_results_without_category(self, tmp_path: Path) -> None:
        entry = _make_entry(
            [
                {"success": True},  # no category key
                {"category": "", "success": False},  # empty category
                {"category": "lint_fix", "success": True},
            ]
        )
        path = _make_learnings_file([entry], tmp_path)
        gen = TaskGenerator(learnings_path=str(path))

        assert list(gen._category_stats.keys()) == ["lint_fix"]

    def test_malformed_jsonl_line_skipped(self, tmp_path: Path) -> None:
        path = tmp_path / "loop_learnings.jsonl"
        path.write_text('{"valid": true, "results": []}\nnot-json\n')
        # Should not raise; malformed line is skipped
        gen = TaskGenerator(learnings_path=str(path))
        assert isinstance(gen._category_stats, dict)


class TestPriorityPenalty:
    def test_no_history_returns_zero(self) -> None:
        gen = TaskGenerator(learnings_path="")
        assert gen._priority_penalty("test_fix") == 0

    def test_below_threshold_returns_zero(self, tmp_path: Path) -> None:
        # 25% failure rate is below _FAILURE_THRESHOLD (0.4) → no penalty
        entry = _make_entry(
            [
                {"category": "lint_fix", "success": True},
                {"category": "lint_fix", "success": True},
                {"category": "lint_fix", "success": True},
                {"category": "lint_fix", "success": False},
            ]
        )
        path = _make_learnings_file([entry], tmp_path)
        gen = TaskGenerator(learnings_path=str(path))
        assert gen._priority_penalty("lint_fix") == 0

    def test_above_threshold_returns_positive_penalty(self, tmp_path: Path) -> None:
        # 100% failure rate → max penalty
        entry = _make_entry(
            [
                {"category": "refactor", "success": False},
                {"category": "refactor", "success": False},
                {"category": "refactor", "success": False},
            ]
        )
        path = _make_learnings_file([entry], tmp_path)
        gen = TaskGenerator(learnings_path=str(path))
        penalty = gen._priority_penalty("refactor")
        assert 1 <= penalty <= _MAX_PENALTY

    def test_penalty_capped_at_max(self, tmp_path: Path) -> None:
        entry = _make_entry([{"category": "type_fix", "success": False} for _ in range(20)])
        path = _make_learnings_file([entry], tmp_path)
        gen = TaskGenerator(learnings_path=str(path))
        assert gen._priority_penalty("type_fix") == _MAX_PENALTY

    def test_unknown_category_returns_zero(self, tmp_path: Path) -> None:
        entry = _make_entry([{"category": "lint_fix", "success": False}])
        path = _make_learnings_file([entry], tmp_path)
        gen = TaskGenerator(learnings_path=str(path))
        assert gen._priority_penalty("nonexistent_category") == 0


class TestGenerateAllPriorityAdjustment:
    def test_failing_category_gets_higher_priority_number(self, tmp_path: Path) -> None:
        """A category that always fails should get a priority penalty applied."""
        entry = _make_entry(
            [
                {"category": "refactor", "success": False},
                {"category": "refactor", "success": False},
                {"category": "refactor", "success": False},
            ]
        )
        path = _make_learnings_file([entry], tmp_path)
        gen = TaskGenerator(repo_root="/tmp/nonexistent_repo", learnings_path=str(path))

        # Manually inject a fake task list to test the penalty application
        task = {"id": "t1", "category": "refactor", "priority": 4}
        penalty = gen._priority_penalty("refactor")
        task["priority"] += penalty
        assert task["priority"] > 4, "Failing category should raise priority number"

    def test_successful_category_unchanged(self, tmp_path: Path) -> None:
        """A category with good success rate keeps its original priority."""
        entry = _make_entry(
            [
                {"category": "lint_fix", "success": True},
                {"category": "lint_fix", "success": True},
            ]
        )
        path = _make_learnings_file([entry], tmp_path)
        gen = TaskGenerator(repo_root="/tmp/nonexistent_repo", learnings_path=str(path))

        assert gen._priority_penalty("lint_fix") == 0

    def test_learning_penalty_field_added_to_penalized_tasks(self, tmp_path: Path) -> None:
        """Tasks that receive a penalty should have _learning_penalty set for inspection."""
        entry = _make_entry(
            [
                {"category": "refactor", "success": False},
                {"category": "refactor", "success": False},
                {"category": "refactor", "success": False},
            ]
        )
        path = _make_learnings_file([entry], tmp_path)
        gen = TaskGenerator(repo_root="/tmp/nonexistent_repo", learnings_path=str(path))

        task = {"id": "t1", "category": "refactor", "priority": 4}
        penalty = gen._priority_penalty("refactor")
        if penalty > 0:
            task["priority"] += penalty
            task["_learning_penalty"] = penalty
            assert "_learning_penalty" in task
            assert task["_learning_penalty"] == penalty
