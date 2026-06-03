"""Tests for scripts/experiment_e70_tdd_adversarial.py.

Covers TDD test case creation, suite runner, persona reviews, parallel reviews,
capability stacks save/load, and adversarial pipeline runner.
"""

from __future__ import annotations

import shutil
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.scripts.experiment_e70_tdd_adversarial import (
    CapabilityStack,
    TDDAdversarialExperiment,
    TDDTestCase,
    TDDTestSuite,
    TestStatus,
    experiment_e70_tdd_adversarial,
)

TestStatus.__test__ = False


def test_tdd_test_case_pending():
    """Should create pending TDDTestCase."""
    tc = TDDTestCase(
        test_id="T1",
        description="test",
        requirement="REQ-1",
        target_function="target",
        test_function=lambda: None,
    )
    assert tc.status == TestStatus.PENDING


@pytest.mark.asyncio
async def test_tdd_test_case_success():
    """Should run TDDTestCase to GREEN."""
    tc = TDDTestCase(
        test_id="T1",
        description="test",
        requirement="REQ-1",
        target_function="target",
        test_function=lambda: None,
    )
    success, error = await tc.run()
    assert success is True
    assert error is None
    assert tc.status == TestStatus.GREEN


@pytest.mark.asyncio
async def test_tdd_test_case_failure():
    """Should run TDDTestCase to RED on AssertionError."""

    def fail_fn():
        assert False, "expected failure"

    tc = TDDTestCase(
        test_id="T1",
        description="test",
        requirement="REQ-1",
        target_function="target",
        test_function=fail_fn,
    )
    success, error = await tc.run()
    assert success is False
    assert "expected failure" in error
    assert tc.status == TestStatus.RED


@pytest.mark.asyncio
async def test_tdd_test_case_async():
    """Should run async TDDTestCase function."""

    async def async_fn():
        pass

    tc = TDDTestCase(
        test_id="T1",
        description="test",
        requirement="REQ-1",
        target_function="target",
        test_function=async_fn,
    )
    success, error = await tc.run()
    assert success is True
    assert tc.status == TestStatus.GREEN


@pytest.mark.asyncio
async def test_tdd_suite():
    """Should run suite phases."""
    suite = TDDTestSuite()
    tc1 = TDDTestCase(
        test_id="T1",
        description="test",
        requirement="REQ-1",
        target_function="target",
        test_function=lambda: None,
    )
    suite.add_test(tc1)
    result = await suite.run_phase("RED")
    assert result["total"] == 1
    assert result["passed"] == 1


def test_capability_stack_persistence():
    """Should save and load capability stack."""
    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)
        stack = CapabilityStack(run_id=42, coherence=0.8)

        saved_path = stack.save(tmp_path)
        assert saved_path.exists()

        loaded = CapabilityStack.load_latest(tmp_path)
        assert loaded is not None
        assert loaded.run_id == 42
        assert loaded.coherence == 0.8


@pytest.mark.asyncio
async def test_adversarial_experiment_blocked():
    """Should run adversarial experiment and block merge on critical issues."""
    experiment = TDDAdversarialExperiment(target_cycles=1)

    # Force Critical issue by mocking personas
    with patch.object(
        experiment.adversarial.personas[3], "review", new_callable=AsyncMock
    ) as mock_review:
        mock_review.return_value = {
            "persona": "Security Predator",
            "security_score": 50,
            "critical_count": 1,
            "warning_count": 0,
            "findings": [
                {"issue": "exploit found", "severity": "CRITICAL", "suggestion": "fix it"}
            ],
        }

        _load_count = 0

        def mock_load_latest(cls, cap_dir):
            nonlocal _load_count
            _load_count += 1
            if _load_count % 2 == 1:
                return CapabilityStack(run_id=999)
            else:
                return CapabilityStack(run_id=0)

        import shutil

        with patch.object(CapabilityStack, "load_latest", classmethod(mock_load_latest)):
            try:
                report = await experiment.run()

                assert report["critical_issues"] > 0
                assert report["review_status"] == "REJECT_PENDING_RESOLUTION"
                assert report["metric"] == 0.0
            finally:
                shutil.rmtree("./test_caps", ignore_errors=True)


@pytest.mark.asyncio
async def test_adversarial_experiment_approved():
    """Should run adversarial experiment and succeed with compound lift when approved."""
    import sys

    mock_module = MagicMock()
    mock_module.VModelCompoundExperiment.return_value.run = AsyncMock(
        return_value={"metric": 0.1234, "capabilities_inherited": True}
    )
    sys.modules["cohezion.scripts.experiment_e70_vmodel_engineering"] = mock_module
    _load_count = 0

    def mock_load_latest(cls, cap_dir):
        nonlocal _load_count
        _load_count += 1
        if _load_count % 2 == 1:
            return CapabilityStack(run_id=999)
        else:
            return CapabilityStack(run_id=0)

    with patch.object(CapabilityStack, "load_latest", classmethod(mock_load_latest)):
        try:
            # Run entry point
            report = await experiment_e70_tdd_adversarial(target_cycles=1)

            assert report["tdd_status"] == "PASS"
            assert report["critical_issues"] == 0
            assert report["review_status"] == "APPROVE"
            assert report["metric"] == 0.1234
            assert report["capabilities_inherited"] == 1
        finally:
            sys.modules.pop("cohezion.scripts.experiment_e70_vmodel_engineering", None)
            shutil.rmtree("./test_caps", ignore_errors=True)
