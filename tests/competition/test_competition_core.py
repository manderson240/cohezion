"""Focused tests for the competition module's core APIs.

This file exercises the most critical entry points in the competition package:
- experience_solver.try_program_on_train
- experience_solver.build_prediction
- portfolio_manager.expected_value / alignment_gate  
- kaggle_submission_arc.solve_task

The competition submodule relies on local imports (arc_solver, experience_vault)
that are not on the package namespace, so we mock them via sys.modules at module
import time and use @patch at source level inside tests.
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Module-level mocking: arc_solver and experience_vault must be resolvable
# before importing competition submodules that use bare import statements.
# ---------------------------------------------------------------------------
_mock_arc: ModuleType = MagicMock()
_mock_arc.Grid = list[list[int]]
_mock_arc.deepcopy_grid = lambda g: [row[:] for row in g] if g else []
_mock_arc.grids_equal = lambda a, b: a == b


class _FakeProgram:
    """Stand-in for a DSL program callable."""

    def __init__(self, name: str = "identity") -> None:
        self._name = name

    def __call__(self, g: list[list[int]]) -> list[list[int]] | None:
        return [row[:] for row in g]

    def __repr__(self) -> str:  # noqa: D105
        return f"_FakeProgram({self._name})"


_mock_arc.apply_program = MagicMock(side_effect=lambda g, prog: [row[:] for row in g])
_mock_arc.search_program = MagicMock(return_value=[_FakeProgram("identity")])
_mock_arc.Program = _FakeProgram

sys.modules.setdefault("arc_solver", _mock_arc)

_mock_vault: ModuleType = MagicMock()
_mock_vault.ExperienceVault = MagicMock()  # type: ignore[ assignment]
_mock_vault.extract_signature = MagicMock(return_value=MagicMock())

sys.modules.setdefault("experience_vault", _mock_vault)

# Now safe to import competition modules.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "cohezion" / "competition"))

from experience_solver import build_prediction, solve_with_experience, try_program_on_train
from kaggle_submission_arc import solve_task  # type: ignore[import-untyped]
from portfolio_manager import alignment_gate, expected_value  # type: ignore[import-untyped]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------
class TestExperienceSolver:
    """Tests for the experience_solver core helpers."""

    def test_try_program_on_train_valid(self):
        """try_program_on_train returns True when all examples match."""
        program = [_FakeProgram()]
        train = [{"input": [[1, 2], [3, 4]], "output": [[1, 2], [3, 4]]}]

        with patch("experience_solver.apply_program", return_value=train[0]["output"]):
            with patch("experience_solver.grids_equal", return_value=True):
                result = try_program_on_train(program, train)

        assert result is True

    def test_try_program_on_train_invalid(self):
        """try_program_on_train returns False when at least one example mismatches."""
        program = [_FakeProgram()]
        train = [{"input": [[1]], "output": [[9]]}]

        with patch("experience_solver.apply_program", return_value=[[9]]):
            with patch("experience_solver.grids_equal", return_value=False):
                result = try_program_on_train(program, train)

        assert result is False

    def test_try_program_on_train_empty_program(self):
        """Empty program short-circuits to False."""
        assert try_program_on_train([], []) is False

    def test_build_prediction_identity(self):
        """build_prediction wraps test examples in attempt_1 / attempt_2."""
        task = {"id": "t1", "test": [{"input": [[1, 0], [0, 1]]}]}
        program = [_FakeProgram()]

        result = build_prediction(task, program)

        assert "t1" in result
        assert len(result["t1"]) == 1
        assert "attempt_1" in result["t1"][0]
        assert "attempt_2" in result["t1"][0]
        # The API wraps the grid in a list: {"attempt_1": [grid]}
        assert result["t1"][0]["attempt_1"][0] == [[1, 0], [0, 1]]
        assert result["t1"][0]["attempt_2"][0] == [[1, 0], [0, 1]]

    @patch("experience_solver.search_program")
    @patch("experience_solver.try_program_on_train")
    def test_solve_with_experience_finds_similar(self, mock_try: MagicMock, mock_search: MagicMock):
        """solve_with_experience reuses a similar solved entry when it matches."""
        sig = MagicMock()
        entry = MagicMock()
        entry.solved = True
        entry.task_id = "ref_1"
        entry.signature = sig
        vault = MagicMock()
        vault.find_similar.return_value = [(0.1, entry)]

        # The re-searched program matches training examples
        mock_try.return_value = True
        mock_search.return_value = [_FakeProgram("found")]

        train_challenges = {
            "ref_1": {"train": [{"input": [[1]], "output": [[1]]}]},
        }

        task = {
            "id": "t2",
            "train": [{"input": [[1]], "output": [[1]]}],
            "test": [{"input": [[1]]}],
        }

        result = solve_with_experience(task, vault, train_challenges, max_depth=2, budget=1000)

        assert "t2" in result
        assert len(result["t2"]) == 1
        mock_search.assert_called()
        mock_try.assert_called_once()


class TestPortfolioManager:
    """Tests for portfolio_manager decision helpers."""

    def test_expected_value_happy(self):
        """expected_value scales prize by aligned probability and effort."""
        comp = {
            "prize_usd": 100_000,
            "alignment_with_skills": 1.0,
            "match_with_stack": 1.0,
            "teams": 10,
            "effort_weeks": 2,
        }
        ev = expected_value(comp)
        assert ev > 0
        assert isinstance(ev, float)

    def test_alignment_gate_pass(self):
        """alignment_gate returns True when alignment is above threshold."""
        assert alignment_gate({"alignment_with_skills": 0.75}, threshold=0.5) is True

    def test_alignment_gate_fail(self):
        """alignment_gate returns False when alignment is below threshold."""
        assert alignment_gate({"alignment_with_skills": 0.2}, threshold=0.5) is False


class TestKaggleSubmissionArc:
    """Tests for kaggle_submission_arc solve pipeline."""

    @patch("kaggle_submission_arc.arc_solver")
    def test_solve_task_returns_grid(self, mock_arc: MagicMock):
        """solve_task calls the DSL solver and returns the predicted grid."""
        mock_arc.search_program.return_value = [_FakeProgram("dsl")]
        mock_arc.apply_program.return_value = [[0, 1], [1, 0]]
        mock_arc.grids_equal.return_value = True
        mock_arc.get_all_ops.return_value = []

        train = [{"input": [[1, 0], [0, 1]], "output": [[0, 1], [1, 0]]}]
        result = solve_task(train, budget=500, max_depth=2)

        mock_arc.search_program.assert_called_once()
        assert result == [[0, 1], [1, 0]]

    @patch("kaggle_submission_arc.arc_solver")
    def test_solve_task_none_on_failure(self, mock_arc: MagicMock):
        """solve_task returns None when solver produces no program."""
        mock_arc.search_program.return_value = None
        mock_arc.get_all_ops.return_value = []

        train = [{"input": [[1]], "output": [[1]]}]
        result = solve_task(train)

        mock_arc.search_program.assert_called_once()
        assert result is None
