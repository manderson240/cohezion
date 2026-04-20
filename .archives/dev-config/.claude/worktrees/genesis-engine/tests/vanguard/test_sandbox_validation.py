"""Tests for Substrate Sandbox & Behavioral Validation (Story 4.2)."""

from __future__ import annotations

from cohezion.vanguard.sandbox_validation import (
    SandboxScript,
    SubstrateSandbox,
    ValidationVerdict,
)


class TestSubstrateSandbox:
    def _safe_script(self, script_id: str = "s1") -> SandboxScript:
        return SandboxScript(
            script_id=script_id,
            source_url="https://arxiv.org/paper",
            code="result = coherence * 0.5",  # Safe code
            requested_bytes=1024 * 1024,
        )

    def test_safe_script_passes_validation(self):
        sandbox = SubstrateSandbox()
        result = sandbox.validate(self._safe_script())
        assert result.verdict == ValidationVerdict.PASSED
        assert result.substrate_impact == "none"

    def test_over_quota_script_quarantined(self):
        sandbox = SubstrateSandbox(gtt_quota_bytes=1024)
        script = SandboxScript(
            script_id="big",
            source_url="https://example.com",
            code="print('hello')",
            requested_bytes=2048,  # Over quota
        )
        result = sandbox.validate(script)
        assert result.verdict == ValidationVerdict.QUARANTINED
        assert "quota" in result.reason.lower()

    def test_unsafe_pattern_quarantined(self):
        sandbox = SubstrateSandbox()
        script = SandboxScript(
            script_id="bad",
            source_url="https://example.com",
            code="shell_invoke('rm -rf /')",  # Unsafe pattern
            requested_bytes=1024,
        )
        result = sandbox.validate(script)
        assert result.verdict == ValidationVerdict.QUARANTINED
        assert "shell_invoke" in result.reason

    def test_quarantine_count_tracked(self):
        sandbox = SubstrateSandbox()
        sandbox.validate(SandboxScript("s1", "", "shell_invoke('x')", 100))
        sandbox.validate(SandboxScript("s2", "", "dynamic_import('y')", 100))
        assert sandbox.quarantine_count == 2

    def test_results_serializable(self):
        sandbox = SubstrateSandbox()
        sandbox.validate(self._safe_script())
        results = sandbox.results()
        assert len(results) == 1
        assert "verdict" in results[0]
