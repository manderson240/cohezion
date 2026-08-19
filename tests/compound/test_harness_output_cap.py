"""HarnessSynthesizer.verify() must cap captured subprocess output.

Why: `verify()` returned `result.stdout + result.stderr` unbounded. A single pytest run
can emit 50k+ characters, which lands directly in an agent's context (~12.5k tokens at
4 chars/token). Backlog item raised 2026-06-24, implemented 2026-08-19.

The cap keeps BOTH ends. For test-runner output the actionable content — the failure
summary — is at the TAIL, so a head-only truncation would discard precisely the part
worth reading.
"""

from __future__ import annotations

import subprocess
from unittest.mock import patch

from cohezion.compound.harness import MAX_TOOL_OUTPUT_CHARS, HarnessSynthesizer, _cap_output


class TestCapOutput:
    def test_short_output_passes_through_unchanged(self) -> None:
        """Discriminating: an impl that always truncates would fail this."""
        assert _cap_output("hello") == "hello"

    def test_exactly_at_limit_is_untouched(self) -> None:
        text = "x" * MAX_TOOL_OUTPUT_CHARS
        assert _cap_output(text) == text

    def test_over_limit_is_capped(self) -> None:
        text = "x" * (MAX_TOOL_OUTPUT_CHARS * 3)
        out = _cap_output(text)
        assert len(out) < len(text), "output was not capped"
        assert len(out) <= MAX_TOOL_OUTPUT_CHARS + 200, "cap overshot its own budget"

    def test_truncation_is_visible_not_silent(self) -> None:
        """Silent truncation is indistinguishable from short output — the marker is the point."""
        out = _cap_output("x" * (MAX_TOOL_OUTPUT_CHARS * 2))
        assert "truncated" in out.lower()
        assert str(MAX_TOOL_OUTPUT_CHARS) in out or "chars" in out.lower()

    def test_tail_is_preserved(self) -> None:
        """The failure summary lives at the END of test-runner output."""
        body = "A" * (MAX_TOOL_OUTPUT_CHARS * 2)
        text = body + "FAILED tests/test_x.py::test_y - AssertionError"
        out = _cap_output(text)
        assert "FAILED tests/test_x.py::test_y" in out, "tail dropped — the useful half"

    def test_head_is_preserved(self) -> None:
        text = "TRACEBACK-START" + ("B" * (MAX_TOOL_OUTPUT_CHARS * 2))
        assert "TRACEBACK-START" in _cap_output(text)


class TestVerifyIsCapped:
    """The constant must be CONSUMED by verify(), not merely defined (wiring discipline)."""

    def test_verify_caps_a_huge_subprocess_output(self) -> None:
        huge = "z" * (MAX_TOOL_OUTPUT_CHARS * 4)
        fake = subprocess.CompletedProcess(args=[], returncode=0, stdout=huge, stderr="")
        synth = HarnessSynthesizer()
        with patch("cohezion.compound.harness.subprocess.run", return_value=fake):
            ok, output = synth.verify("x = 1", "mod")
        assert ok is True
        assert len(output) < len(huge), "verify() returned uncapped output — constant is dormant"
        assert "truncated" in output.lower()

    def test_verify_leaves_small_output_alone(self) -> None:
        """Discriminating: proves the cap is conditional, not applied unconditionally."""
        fake = subprocess.CompletedProcess(
            args=[], returncode=0, stdout="HARNESS_INFO: ok\n", stderr=""
        )
        synth = HarnessSynthesizer()
        with patch("cohezion.compound.harness.subprocess.run", return_value=fake):
            _, output = synth.verify("x = 1", "mod")
        assert output == "HARNESS_INFO: ok\n"
        assert "truncated" not in output.lower()
