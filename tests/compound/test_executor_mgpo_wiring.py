"""TDD tests for MGPO batch refinement wiring in CompoundExecutor (Task #19).

V-Model level: AD1 (Architecture Design) — Integration between executor state
accumulation, MGPO prioritization, and the skill refiner call path.

These tests MUST fail before implementation:
  - test_executor_has_recent_skill_names    → AttributeError
  - test_accumulator_fills_on_execution     → AttributeError
  - test_batch_trigger_fires_at_n           → method not called
  - test_batch_refines_top_k_mgpo_order     → wrong order / method missing
  - test_accumulator_drains_after_batch     → accumulator not cleared
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch


from cohezion.compound.executor import CompoundExecutor


# ── structural invariants (MD level) ────────────────────────────────────────


def test_executor_has_recent_skill_names():
    """CompoundExecutor must expose _recent_skill_names list after init."""
    ex = CompoundExecutor(mcp_client=None, enable_skill_refinement=False)
    assert hasattr(ex, "_recent_skill_names"), (
        "_recent_skill_names accumulator missing from CompoundExecutor"
    )
    assert isinstance(ex._recent_skill_names, list)


def test_executor_has_mgpo_batch_size():
    """CompoundExecutor must expose MGPO_BATCH_SIZE class constant."""
    assert hasattr(CompoundExecutor, "MGPO_BATCH_SIZE"), (
        "MGPO_BATCH_SIZE class constant missing from CompoundExecutor"
    )
    assert CompoundExecutor.MGPO_BATCH_SIZE >= 1


def test_executor_has_batch_mgpo_refine():
    """CompoundExecutor must expose _batch_mgpo_refine() method."""
    ex = CompoundExecutor(mcp_client=None, enable_skill_refinement=False)
    assert hasattr(ex, "_batch_mgpo_refine"), (
        "_batch_mgpo_refine() method missing from CompoundExecutor"
    )


# ── accumulator behaviour (MD level) ────────────────────────────────────────


def _make_minimal_executor(mock_refiner=None):
    """Return an executor with mocked inference provider and skill refiner."""
    ex = CompoundExecutor(
        mcp_client=None,
        enable_skill_refinement=True,
        skill_refiner=mock_refiner or MagicMock(),
    )
    return ex


def test_batch_mgpo_refine_calls_prioritized_skills():
    """_batch_mgpo_refine must call skill_refiner.prioritized_skills() with candidates."""
    mock_refiner = MagicMock()
    mock_refiner.prioritized_skills.return_value = ["a", "b", "c"]
    mock_refiner.refine.return_value = None

    ex = _make_minimal_executor(mock_refiner)
    ex._recent_skill_names = ["a", "b", "c", "a", "b"]

    ex._batch_mgpo_refine()

    mock_refiner.prioritized_skills.assert_called_once()
    called_with = mock_refiner.prioritized_skills.call_args[0][0]
    # unique candidates passed in (set of accumulated names)
    assert set(called_with) == {"a", "b", "c"}


def test_batch_mgpo_refine_calls_refine_top_k():
    """_batch_mgpo_refine must call refine() for the top-K MGPO-ordered skills."""
    mock_refiner = MagicMock()
    # MGPO order: boundary skill first
    mock_refiner.prioritized_skills.return_value = ["boundary", "mastered", "stuck"]
    mock_refiner.refine.return_value = None

    ex = _make_minimal_executor(mock_refiner)
    ex._recent_skill_names = ["mastered", "stuck", "boundary"] * 3

    ex._batch_mgpo_refine(top_k=2)

    refine_calls = [c[1]["skill_name"] for c in mock_refiner.refine.call_args_list]
    assert refine_calls[:2] == ["boundary", "mastered"], (
        f"Top-2 refine calls must follow MGPO order; got {refine_calls}"
    )
    assert len(refine_calls) == 2, "Must refine exactly top_k=2 skills"


def test_accumulator_drains_after_batch():
    """_batch_mgpo_refine must clear _recent_skill_names after processing."""
    mock_refiner = MagicMock()
    mock_refiner.prioritized_skills.return_value = ["x"]
    mock_refiner.refine.return_value = None

    ex = _make_minimal_executor(mock_refiner)
    ex._recent_skill_names = ["x", "y", "z"]

    ex._batch_mgpo_refine()

    assert ex._recent_skill_names == [], (
        "_recent_skill_names must be empty after batch refinement"
    )


def test_batch_mgpo_refine_empty_accumulator_is_noop():
    """_batch_mgpo_refine with empty accumulator must not call refiner."""
    mock_refiner = MagicMock()
    ex = _make_minimal_executor(mock_refiner)
    ex._recent_skill_names = []

    ex._batch_mgpo_refine()

    mock_refiner.prioritized_skills.assert_not_called()
    mock_refiner.refine.assert_not_called()


def test_batch_mgpo_refine_no_refiner_is_noop():
    """_batch_mgpo_refine with no skill_refiner must not raise."""
    ex = CompoundExecutor(mcp_client=None, enable_skill_refinement=False)
    ex._recent_skill_names = ["some_skill"]
    # should not raise, even with no refiner configured
    ex._batch_mgpo_refine()


# ── batch trigger (AD level) ─────────────────────────────────────────────────


def test_accumulator_appends_and_check_fires():
    """Direct accumulation: appending to _recent_skill_names + _check_mgpo_batch work together."""
    mock_refiner = MagicMock()
    ex = _make_minimal_executor(mock_refiner)
    ex._recent_skill_names = []

    # Simulate what execute_task does: accumulate skill name, then check
    ex._recent_skill_names.append("ROUTING")
    ex._check_mgpo_batch()  # below batch size — must not fire
    assert "ROUTING" in ex._recent_skill_names

    # Fill to batch size - 1, then push over
    ex._recent_skill_names = [f"s{i}" for i in range(CompoundExecutor.MGPO_BATCH_SIZE - 1)]
    ex._recent_skill_names.append("ROUTING")

    mock_refiner.prioritized_skills.return_value = ["ROUTING"]
    mock_refiner.refine.return_value = None
    ex._check_mgpo_batch()

    # After firing, accumulator must be drained
    assert ex._recent_skill_names == [], "Accumulator must drain after batch trigger"


def test_batch_trigger_fires_at_batch_size(monkeypatch):
    """_batch_mgpo_refine must be called when len(_recent_skill_names) reaches MGPO_BATCH_SIZE."""
    mock_refiner = MagicMock()
    mock_refiner.prioritized_skills.return_value = ["skill_0"]
    mock_refiner.refine.return_value = None

    ex = _make_minimal_executor(mock_refiner)

    batch_calls = []
    original_batch = ex._batch_mgpo_refine

    def tracking_batch(*args, **kwargs):
        batch_calls.append(1)
        return original_batch(*args, **kwargs)

    ex._batch_mgpo_refine = tracking_batch

    # Simulate accumulation to just below threshold, then at threshold
    batch_size = CompoundExecutor.MGPO_BATCH_SIZE
    ex._recent_skill_names = [f"skill_{i}" for i in range(batch_size - 1)]

    # The executor's _check_mgpo_batch() must fire when we push over the threshold
    ex._recent_skill_names.append("skill_trigger")
    ex._check_mgpo_batch()

    assert len(batch_calls) == 1, (
        f"_batch_mgpo_refine must fire once at MGPO_BATCH_SIZE={batch_size}; "
        f"fired {len(batch_calls)} times"
    )


def test_check_mgpo_batch_below_threshold_does_not_fire():
    """_check_mgpo_batch must NOT call _batch_mgpo_refine below MGPO_BATCH_SIZE."""
    mock_refiner = MagicMock()
    ex = _make_minimal_executor(mock_refiner)
    ex._recent_skill_names = ["a", "b"]  # below MGPO_BATCH_SIZE

    with patch.object(ex, "_batch_mgpo_refine") as mock_batch:
        ex._check_mgpo_batch()

    mock_batch.assert_not_called()
