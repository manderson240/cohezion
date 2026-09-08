"""Tests for ShadowScripter Autonomous Test Generation (Story 5.2, FR7)."""

from __future__ import annotations

from cohezion.learning.shadow_scripter import (
    ShadowScripter,
    TestGenStatus,
)


class TestShadowScripter:
    def test_valid_test_is_validated(self):
        """Syntactically valid test code is marked validated."""
        scripter = ShadowScripter()
        test = scripter.generate(
            test_name="test_coherence",
            test_code="def test_coherence():\n    assert 1 + 1 == 2\n",
            source_skill="COHERENCE_PRIME",
        )
        assert test.status == TestGenStatus.VALIDATED
        assert test.error is None

    def test_invalid_syntax_is_quarantined(self):
        """Test with syntax errors is quarantined, not committed."""
        scripter = ShadowScripter()
        test = scripter.generate(
            test_name="test_broken",
            test_code="def test_broken(\n    assert True  # Missing closing paren",
            source_skill="BROKEN_SKILL",
        )
        assert test.status == TestGenStatus.QUARANTINED
        assert test.error is not None

    def test_quarantined_tests_not_committable(self):
        """Quarantined tests are excluded from committable list."""
        scripter = ShadowScripter()
        scripter.generate("test_ok", "assert True\n", "skill_a")
        scripter.generate("test_bad", "def (:\n", "skill_b")
        committable = scripter.get_committable_tests()
        assert len(committable) == 1
        assert committable[0].test_name == "test_ok"

    def test_quarantine_report(self):
        """Quarantine report contains failed tests for Ouroboros."""
        scripter = ShadowScripter()
        scripter.generate("test_bad", "def (:\n", "skill_x")
        report = scripter.get_quarantine_report()
        assert len(report) == 1
        assert report[0]["status"] == "quarantined"

    def test_multiple_generations(self):
        """Multiple tests can be generated in sequence."""
        scripter = ShadowScripter()
        for i in range(5):
            scripter.generate(f"test_{i}", f"assert {i} >= 0\n", f"skill_{i}")
        assert len(scripter.generated_tests) == 5

    def test_source_skill_tracked(self):
        """Each test tracks which skill triggered its generation."""
        scripter = ShadowScripter()
        test = scripter.generate("test_x", "assert True\n", "FLUME_PRIME")
        assert test.source_skill == "FLUME_PRIME"
