"""TDD test for _apply_rule fn_map desync bug.

Bug: submission.py::SubmissionBuilder._apply_rule has a hardcoded fn_map that
is missing ops produced by PatternExtractor._build_strategy:
  - color_map  (needs train data, stateful closure)
  - upsample2, upsample3, downsample2, downsample3 (pure scaling ops)

When PatternExtractor extracts a rule with these ops (e.g. 'color_map' or
'upsample2'), _apply_rule returns None (op not found) and falls through to
the default_zero fallback, losing the correct prediction.

V-Model Traceability
--------------------
Requirement  : _apply_rule must execute all ops that PatternExtractor can emit.
Architecture  : Pass train data to _apply_rule; build op map from _build_strategy.
Implementation: See submission.py _apply_rule + _predict_with_rules.
Verification  : This test file.

Tasks blocked by bug (measured on ARC-AGI-2 training set):
  color_map: 0d3d703e, d511f180
  upsample2/3/downsample2: 60c09cac, 68b67ca3, 9172f3a0, c59eb873
  Total: 6/1000 tasks = +0.6% solve rate improvement when fixed.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from cohezion.arc.codec import grids_equal
from cohezion.arc.pattern_extractor import CompoundRule, PatternExtractor
from cohezion.arc.submission import SubmissionBuilder


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


# Resolve data directory by walking up from the test file until we find
# a "data/arc-agi-2" subdirectory. This handles both worktrees and the
# main checkout without hardcoding absolute paths.
def _find_arc_data() -> Path:
    """Walk up from this file to find the data/arc-agi-2 directory
    that contains the training challenges JSON.
    """
    candidate = Path(__file__).resolve()
    for _ in range(8):
        candidate = candidate.parent
        data_dir = candidate / "data" / "arc-agi-2"
        if (data_dir / "arc-agi_training_challenges.json").is_file():
            return data_dir
    return Path("/nonexistent/data/arc-agi-2")


_DATA = _find_arc_data()
_CHALLENGES = _DATA / "arc-agi_training_challenges.json"
_SOLUTIONS = _DATA / "arc-agi_training_solutions.json"


def _load_task_and_solution(task_id: str):
    """Return (task_dict, solution_grid) for a training task."""
    challenges = json.loads(_CHALLENGES.read_text())
    solutions = json.loads(_SOLUTIONS.read_text())
    return challenges[task_id], solutions[task_id][0]


def _builder(tmp_path: Path) -> SubmissionBuilder:
    return SubmissionBuilder(
        data_dir=Path("/nonexistent"),
        output_path=tmp_path / "submission.json",
    )


# ---------------------------------------------------------------------------
# Tests: color_map op missing from _apply_rule fn_map
# ---------------------------------------------------------------------------


def test_apply_rule_colormap_blocked_d511f180(tmp_path: Path):
    """d511f180: PatternExtractor extracts 'color_map' but _apply_rule cannot execute it.

    Before fix: _apply_rule returns None (falls to default_zero).
    After fix: correct prediction matches solution.
    """
    if not _CHALLENGES.exists():
        pytest.skip("ARC training data not available")

    task, sol = _load_task_and_solution("d511f180")
    extractor = PatternExtractor(max_depth=1, budget_per_strategy=200)
    rules = extractor.extract(task)

    # Verify PatternExtractor DOES find color_map as a rule
    assert any("color_map" in r.ops for r in rules), (
        "PatternExtractor should extract a color_map rule for d511f180"
    )

    builder = _builder(tmp_path)

    # After fix: _apply_rule should accept train data and execute color_map
    best_rule = next(r for r in rules if "color_map" in r.ops)
    test_input = task["test"][0]["input"]

    # The fixed _apply_rule must accept train as an argument
    pred = builder._apply_rule(test_input, best_rule, train=task["train"])

    assert pred is not None, "_apply_rule must not return None for color_map op"
    assert grids_equal(pred, sol), (
        f"Prediction does not match solution.\nPred: {pred[:2]}...\nSol:  {sol[:2]}..."
    )


def test_apply_rule_colormap_blocked_0d3d703e(tmp_path: Path):
    """0d3d703e: second task blocked by missing color_map in _apply_rule."""
    if not _CHALLENGES.exists():
        pytest.skip("ARC training data not available")

    task, sol = _load_task_and_solution("0d3d703e")
    extractor = PatternExtractor(max_depth=1, budget_per_strategy=200)
    rules = extractor.extract(task)

    cm_rules = [r for r in rules if "color_map" in r.ops]
    if not cm_rules:
        pytest.skip("PatternExtractor did not extract color_map for 0d3d703e")

    builder = _builder(tmp_path)
    best_rule = cm_rules[0]
    test_input = task["test"][0]["input"]
    pred = builder._apply_rule(test_input, best_rule, train=task["train"])

    assert pred is not None
    assert grids_equal(pred, sol)


# ---------------------------------------------------------------------------
# Tests: upsample/downsample ops missing from _apply_rule fn_map
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "task_id,expected_op",
    [
        ("60c09cac", "upsample2"),
        ("c59eb873", "upsample2"),
        ("9172f3a0", "upsample3"),
        ("68b67ca3", "downsample2"),
    ],
)
def test_apply_rule_scale_op_not_blocked(task_id: str, expected_op: str, tmp_path: Path):
    """Scale ops (upsample2/3, downsample2) must be executable by _apply_rule.

    Before fix: rule with upsample2 has op not found in fn_map - None returned.
    After fix: correct scaled prediction returned.
    """
    if not _CHALLENGES.exists():
        pytest.skip("ARC training data not available")

    task, sol = _load_task_and_solution(task_id)
    extractor = PatternExtractor(max_depth=1, budget_per_strategy=200)
    rules = extractor.extract(task)

    scale_rules = [r for r in rules if expected_op in r.ops]
    if not scale_rules:
        pytest.skip(f"PatternExtractor did not extract {expected_op} for {task_id}")

    builder = _builder(tmp_path)
    best_rule = scale_rules[0]
    test_input = task["test"][0]["input"]
    pred = builder._apply_rule(test_input, best_rule, train=task["train"])

    assert pred is not None, f"_apply_rule must not return None for {expected_op}"
    assert grids_equal(pred, sol), f"[{task_id}] prediction mismatch for {expected_op}"


# ---------------------------------------------------------------------------
# Regression: existing ops still work after signature change
# ---------------------------------------------------------------------------


def test_apply_rule_existing_ops_still_work(tmp_path: Path):
    """Smoke test: existing ops (flip_h, rot180) must still work
    after _apply_rule signature update to accept optional train kwarg.
    """
    builder = _builder(tmp_path)

    # Test flip_h
    grid = [[1, 2, 3], [4, 5, 6]]
    rule = CompoundRule(
        name="flip_h",
        ops=("flip_h",),
        confidence=1.0,
        train_coverage=1.0,
        strategy_votes=1,
        hiho_score=0.5,
        latent_delta=tuple([0.0] * 12),
        signature=hashlib.sha256(b"flip_h").hexdigest()[:16],
    )
    pred = builder._apply_rule(grid, rule, train=None)
    assert pred == [[4, 5, 6], [1, 2, 3]], f"flip_h failed: {pred}"

    # Test rot180
    rule2 = CompoundRule(
        name="rot180",
        ops=("rot180",),
        confidence=1.0,
        train_coverage=1.0,
        strategy_votes=1,
        hiho_score=0.5,
        latent_delta=tuple([0.0] * 12),
        signature=hashlib.sha256(b"rot180").hexdigest()[:16],
    )
    pred2 = builder._apply_rule([[1, 2], [3, 4]], rule2, train=None)
    assert pred2 == [[4, 3], [2, 1]], f"rot180 failed: {pred2}"
