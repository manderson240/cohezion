"""Unit tests for AutoHarness Submission Guard (ARC-AGI-2).

Verifies fail-loud path resolution, non-empty invariants, ragged row rejection,
and deterministic fallback generation.
"""

import json
from pathlib import Path
import pytest

from cohezion.arc.submission_guard import (
    AutoHarnessSubmissionGuard,
    DatasetPathResolutionError,
    DeterministicTaskFallback,
    DynamicPathResolver,
    SubmissionInvariantViolationError,
)


@pytest.fixture
def mock_arc_environment(tmp_path: Path):
    """Sets up a realistic mock Kaggle directory layout."""
    input_dir = tmp_path / "kaggle" / "input" / "arc-prize-2026-v3"
    input_dir.mkdir(parents=True)

    challenges_data = {
        "007bbfb7": {
            "train": [
                {"input": [[0, 1], [1, 0]], "output": [[1, 2], [2, 1]]}
            ],
            "test": [
                {"input": [[0, 7], [7, 0]]}
            ]
        },
        "00d62c1b": {
            "train": [
                {"input": [[3, 3, 3], [3, 0, 3]], "output": [[4, 4, 4], [4, 0, 4]]}
            ],
            "test": [
                {"input": [[3, 3], [3, 3]]},
                {"input": [[0, 3], [3, 0]]}
            ]
        }
    }
    challenges_file = input_dir / "arc-agi_test_challenges.json"
    challenges_file.write_text(json.dumps(challenges_data))

    return tmp_path, challenges_file, challenges_data


def test_dynamic_path_resolution_exact(mock_arc_environment):
    _, challenges_file, _ = mock_arc_environment
    resolved = DynamicPathResolver.resolve_challenges_file(challenges_file)
    assert resolved == challenges_file.resolve()


def test_dynamic_path_resolution_search_discovery(mock_arc_environment, monkeypatch):
    tmp_path, challenges_file, _ = mock_arc_environment
    monkeypatch.setattr(DynamicPathResolver, "FALLBACK_SEARCH_ROOTS", [tmp_path])
    resolved = DynamicPathResolver.resolve_challenges_file()
    assert resolved == challenges_file.resolve()


def test_dynamic_path_resolution_fail_loud(tmp_path, monkeypatch):
    empty_dir = tmp_path / "empty_kaggle"
    empty_dir.mkdir()
    monkeypatch.setattr(DynamicPathResolver, "FALLBACK_SEARCH_ROOTS", [empty_dir])
    with pytest.raises(DatasetPathResolutionError) as exc_info:
        DynamicPathResolver.resolve_challenges_file()
    assert "FATAL: Unable to resolve ARC test challenges JSON file" in str(exc_info.value)


def test_deterministic_fallback_identity_and_bounds(mock_arc_environment):
    _, _, challenges_data = mock_arc_environment
    task = challenges_data["007bbfb7"]
    fallback = DeterministicTaskFallback.generate_task_fallback(task)

    assert len(fallback) == 1
    assert "attempt_1" in fallback[0]
    assert "attempt_2" in fallback[0]
    assert fallback[0]["attempt_1"] == [[0, 7], [7, 0]]
    assert len(fallback[0]["attempt_2"]) == 2
    assert len(fallback[0]["attempt_2"][0]) == 2


def test_guard_valid_submission_passes(mock_arc_environment, tmp_path):
    _, challenges_file, _ = mock_arc_environment
    guard = AutoHarnessSubmissionGuard(challenges_file)

    valid_sub = {
        "007bbfb7": [{"attempt_1": [[1, 2]], "attempt_2": [[1, 2]]}],
        "00d62c1b": [
            {"attempt_1": [[3]], "attempt_2": [[3]]},
            {"attempt_1": [[0, 3]], "attempt_2": [[0, 3]]},
        ],
    }

    report = guard.validate_submission_dict(valid_sub)
    assert report.is_valid
    assert len(report.defects) == 0

    out_file = tmp_path / "submission.json"
    written_path = guard.write_atomic_submission(valid_sub, out_file)
    assert written_path.exists()
    assert json.loads(written_path.read_text()) == valid_sub


def test_guard_rejects_empty_grid(mock_arc_environment):
    _, challenges_file, _ = mock_arc_environment
    guard = AutoHarnessSubmissionGuard(challenges_file)

    sub_with_empty = {
        "007bbfb7": [{"attempt_1": [], "attempt_2": [[1]]}],
        "00d62c1b": [
            {"attempt_1": [[3]], "attempt_2": [[3]]},
            {"attempt_1": [[0, 3]], "attempt_2": [[0, 3]]},
        ],
    }

    report = guard.validate_submission_dict(sub_with_empty)
    assert not report.is_valid
    assert any("empty or non-list grid" in d for d in report.defects)


def test_guard_rejects_missing_task_without_auto_repair(mock_arc_environment):
    _, challenges_file, _ = mock_arc_environment
    guard = AutoHarnessSubmissionGuard(challenges_file)

    sub_missing_task = {
        "007bbfb7": [{"attempt_1": [[1]], "attempt_2": [[1]]}],
    }

    report = guard.validate_submission_dict(sub_missing_task)
    assert not report.is_valid
    assert any("Missing 1 tasks" in d for d in report.defects)

    with pytest.raises(SubmissionInvariantViolationError):
        guard.write_atomic_submission(sub_missing_task, auto_repair=False)


def test_guard_auto_repairs_dropped_tasks(mock_arc_environment, tmp_path):
    _, challenges_file, _ = mock_arc_environment
    guard = AutoHarnessSubmissionGuard(challenges_file)

    sub_missing_task = {
        "007bbfb7": [{"attempt_1": [[1]], "attempt_2": [[1]]}],
    }

    out_file = tmp_path / "repaired_submission.json"
    written_path = guard.write_atomic_submission(sub_missing_task, out_file, auto_repair=True)
    assert written_path.exists()

    repaired_data = json.loads(written_path.read_text())
    assert "00d62c1b" in repaired_data
    assert len(repaired_data["00d62c1b"]) == 2


def test_guard_safe_execute_task_recovers_from_exception(mock_arc_environment):
    _, challenges_file, _ = mock_arc_environment
    guard = AutoHarnessSubmissionGuard(challenges_file)

    def crashing_worker(task_data):
        raise RuntimeError("CUDA out of memory in test-time training loop!")

    preds = guard.safe_execute_task("007bbfb7", crashing_worker)
    assert len(preds) == 1
    assert preds[0]["attempt_1"] == [[0, 7], [7, 0]]
    assert len(preds[0]["attempt_2"]) == 2
