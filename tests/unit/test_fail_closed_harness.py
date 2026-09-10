"""Unit tests for FailClosedHarness (ExecCritic & CapScope guarantees)."""

from __future__ import annotations

import pytest

from cohezion.reliability.fail_closed_harness import (
    Capability,
    CapabilityCeiling,
    FailClosedHarness,
    FrozenTestSuite,
)


def test_frozen_test_suite_integrity():
    code = "assert 1 + 1 == 2"
    suite = FrozenTestSuite.create_and_freeze(code)
    assert suite.verify_integrity(code) is True
    assert suite.verify_integrity("assert 1 + 1 == 3") is False


def test_capability_ceiling_enforcement():
    ceiling = CapabilityCeiling(allowed_capabilities={Capability.FS_READ})
    assert ceiling.check_permission(Capability.FS_READ) is True
    assert ceiling.check_permission(Capability.CODE_EXEC) is False

    ceiling.grant(Capability.CODE_EXEC)
    assert ceiling.check_permission(Capability.CODE_EXEC) is True

    ceiling.revoke(Capability.CODE_EXEC)
    assert ceiling.check_permission(Capability.CODE_EXEC) is False


def test_harness_blocks_execution_without_capability():
    ceiling = CapabilityCeiling(allowed_capabilities={Capability.FS_READ})
    harness = FailClosedHarness(capability_ceiling=ceiling)
    harness.freeze_test_suite("assert True")

    res = harness.run_under_frozen_suite("x = 1")
    assert res.passed is False
    assert res.capabilities_respected is False
    assert "denied" in (res.error or "")


def test_harness_blocks_malformed_test_suite():
    harness = FailClosedHarness()
    with pytest.raises(ValueError, match="Cannot freeze malformed"):
        harness.freeze_test_suite("def broken(:")


def test_harness_catches_candidate_syntax_error():
    harness = FailClosedHarness()
    harness.freeze_test_suite("assert True")

    res = harness.run_under_frozen_suite("def bad_syntax(:")
    assert res.passed is False
    assert "syntax error" in (res.error or "")


def test_harness_fails_failing_patch():
    harness = FailClosedHarness()
    # Test agent creates test that requires double(5) == 10
    harness.freeze_test_suite("assert double(5) == 10")

    # Flawed candidate patch
    candidate = "def double(n): return n + 2"
    res = harness.run_under_frozen_suite(candidate)
    assert res.passed is False
    assert "AssertionError" in (res.error or "")


def test_harness_passes_correct_patch():
    harness = FailClosedHarness()
    # Test agent creates test
    harness.freeze_test_suite("assert double(5) == 10")

    # Correct patch
    candidate = "def double(n): return n * 2"
    res = harness.run_under_frozen_suite(candidate)
    assert res.passed is True
    assert res.error is None
