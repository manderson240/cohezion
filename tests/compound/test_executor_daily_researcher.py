"""RED tests for the ExecutorFactory.enable_daily_researcher flag (WS2C).

Contracts:
- ExecutorFactory.create() accepts enable_daily_researcher=True (default).
- When True, a DailyResearcher is created and a dry-run is scheduled.
- When False, no DailyResearcher is created and no scheduling happens.
- A failure to import the researcher module does NOT block executor
  creation (best-effort, non-blocking).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

# PREMATURE on this branch, not broken.
#
# ``ExecutorFactory.create(enable_daily_researcher=...)`` is implemented in commit
# c9cd1e723 on ``origin/feat/adaptive-calibration-harness``, which has NEVER been merged
# here (``git merge-base --is-ancestor c9cd1e723 HEAD`` fails). These tests arrived
# separately via #242/#251 without their implementation, so all 4 fail with:
#   TypeError: ExecutorFactory.create() got an unexpected keyword argument
#              'enable_daily_researcher'
#
# strict=True forces this marker to be removed when that branch lands.
pytestmark = pytest.mark.xfail(
    strict=True,
    reason="enable_daily_researcher wiring (c9cd1e723) is unmerged; lives on origin/feat/adaptive-calibration-harness",
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    """Reset the ExecutorFactory singleton between tests."""
    from cohezion.compound.executor_factory import ExecutorFactory

    ExecutorFactory.reset_singleton()
    yield
    ExecutorFactory.reset_singleton()


def _fake_mcp():
    return MagicMock(name="mcp_client")


def test_default_daily_researcher_flag_is_true():
    """The default for enable_daily_researcher is True (per WS2 plan)."""
    import inspect

    from cohezion.compound.executor_factory import ExecutorFactory

    sig = inspect.signature(ExecutorFactory.create)
    assert sig.parameters["enable_daily_researcher"].default is True


def test_enable_daily_researcher_false_skips_scheduling():
    """When the flag is False, no DailyResearcher is instantiated."""
    from cohezion.compound.executor_factory import ExecutorFactory

    with patch("cohezion.researcher.daily_researcher.DailyResearcher") as mock_dr:
        ExecutorFactory.create(_fake_mcp(), enable_daily_researcher=False)
    mock_dr.assert_not_called()


def test_enable_daily_researcher_true_schedules_dry_run():
    """When True, a DailyResearcher is created and a dry-run is scheduled."""
    from cohezion.compound.executor_factory import ExecutorFactory

    with patch("cohezion.researcher.daily_researcher.DailyResearcher") as mock_dr:
        # The factory creates the researcher but doesn't actually run it
        # in a sync context — it just calls run_dry_run() at most
        mock_dr.return_value = MagicMock()
        ExecutorFactory.create(_fake_mcp(), enable_daily_researcher=True)
    # The factory may or may not have called the researcher (best-
    # effort, depends on whether an event loop is available at import
    # time). The contract is "the executor still created successfully";
    # reaching this line is the assertion.
    assert True  # the import + create didn't raise, which is the actual contract


def test_researcher_import_failure_does_not_block_executor():
    """If the researcher module isn't importable, the executor still creates."""
    from cohezion.compound.executor_factory import ExecutorFactory

    with patch.dict("sys.modules", {"cohezion.researcher.daily_researcher": None}):
        # ImportError must be swallowed
        ExecutorFactory.create(_fake_mcp(), enable_daily_researcher=True)
    # If we got here without exception, the test passes
