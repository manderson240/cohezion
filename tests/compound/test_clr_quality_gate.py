"""TDD RED phase — Task #15: CLR quality gate for Mycelium re-injection.

CLR formula: score = (mean_verdicts)^3
- 3/3 YES → 1.0 (passes threshold 0.7)
- 2/3 YES → (2/3)^3 ≈ 0.296 (fails threshold)
- 1/3 YES → (1/3)^3 ≈ 0.037 (fails threshold)
- 0/3 YES → 0.0 (fails threshold)

Fail-open: None score (inference unavailable) → passes() = True.
All inference routes through OmniRouter :13305 (model: llama3.2-1b-FLM).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_gate(verdicts: list[int | None]):
    """Build a CLRQualityGate with _verify_claim returning verdicts in sequence."""
    from cohezion.compound.clr_quality_gate import CLRQualityGate

    gate = CLRQualityGate()
    verdict_iter = iter(verdicts)

    def fake_verify(claim: str, context: str) -> int | None:
        return next(verdict_iter, None)

    gate._verify_claim = fake_verify
    return gate


# ---------------------------------------------------------------------------
# Class 1: CLR score arithmetic — (mean_verdicts)^3
# ---------------------------------------------------------------------------


class TestCLRScoreArithmetic:
    """score = (mean_verdicts)^3 — verified with injected verdicts."""

    def test_all_yes_returns_1(self):
        gate = _make_gate([1, 1, 1])
        s = gate.score("content")
        assert s == pytest.approx(1.0)

    def test_two_yes_returns_cube_of_two_thirds(self):
        gate = _make_gate([1, 1, 0])
        s = gate.score("content")
        assert s == pytest.approx((2 / 3) ** 3)

    def test_one_yes_returns_cube_of_one_third(self):
        gate = _make_gate([1, 0, 0])
        s = gate.score("content")
        assert s == pytest.approx((1 / 3) ** 3)

    def test_all_no_returns_0(self):
        gate = _make_gate([0, 0, 0])
        s = gate.score("content")
        assert s == pytest.approx(0.0)

    def test_score_is_cube_not_linear_or_square(self):
        """Discriminating: 2/3 YES must give (2/3)^3 ≈ 0.296, not linear 0.667 or square 0.444."""
        gate = _make_gate([1, 1, 0])
        s = gate.score("content")
        assert s is not None
        # Must be the cube, not linear or square
        assert s == pytest.approx((2 / 3) ** 3)
        assert abs(s - (2 / 3)) > 0.1, "Linear (not cubed) would be ~0.667"
        assert abs(s - (2 / 3) ** 2) > 0.1, "Squared (not cubed) would be ~0.444"

    def test_inference_failure_returns_none(self):
        """If any _verify_claim returns None, score() returns None."""
        gate = _make_gate([1, None, 1])
        s = gate.score("content")
        assert s is None


# ---------------------------------------------------------------------------
# Class 2: passes() threshold boundary
# ---------------------------------------------------------------------------


class TestCLRPassFail:
    """passes() = score >= 0.7; unanimous YES required in practice."""

    def test_passes_at_three_thirds(self):
        gate = _make_gate([1, 1, 1])
        assert gate.passes("content") is True

    def test_fails_at_two_thirds(self):
        gate = _make_gate([1, 1, 0])
        assert gate.passes("content") is False

    def test_fails_at_one_third(self):
        gate = _make_gate([1, 0, 0])
        assert gate.passes("content") is False

    def test_fails_at_zero_thirds(self):
        gate = _make_gate([0, 0, 0])
        assert gate.passes("content") is False


# ---------------------------------------------------------------------------
# Class 3: Fail-open — inference unavailable → allow ingestion
# ---------------------------------------------------------------------------


class TestCLRFailOpen:
    """When inference is unavailable (score=None), passes() must return True (fail-open)."""

    def test_inference_failure_allows_ingestion(self):
        gate = _make_gate([None, None, None])
        assert gate.passes("content") is True

    def test_none_score_is_distinct_from_zero_score(self):
        """score=None ≠ score=0.0 — None means inference failed, not 'all NO'."""
        gate_none = _make_gate([None, None, None])
        gate_zero = _make_gate([0, 0, 0])
        assert gate_none.score("x") is None
        assert gate_zero.score("x") == pytest.approx(0.0)

    def test_partial_failure_returns_none(self):
        """One None verdict aborts and returns None for the whole score."""
        gate = _make_gate([1, None, 1])
        assert gate.passes("content") is True


# ---------------------------------------------------------------------------
# Class 4: Verdict parsing — first-word only
# ---------------------------------------------------------------------------


class TestVerdictParsing:
    """_parse_verdict() parses YES/NO from first word only."""

    @pytest.fixture
    def parse(self):
        from cohezion.compound.clr_quality_gate import _parse_verdict

        return _parse_verdict

    def test_parses_YES(self, parse):
        assert parse("YES") == 1

    def test_parses_NO(self, parse):
        assert parse("NO") == 0

    def test_parses_lowercase_yes(self, parse):
        assert parse("yes") == 1

    def test_parses_lowercase_no(self, parse):
        assert parse("no") == 0

    def test_parses_yes_with_period(self, parse):
        assert parse("Yes.") == 1

    def test_parses_no_with_period(self, parse):
        assert parse("No.") == 0

    def test_empty_returns_none(self, parse):
        assert parse("") is None

    def test_whitespace_only_returns_none(self, parse):
        assert parse("   ") is None

    def test_ambiguous_first_word_returns_zero(self, parse):
        """First word 'I' is ambiguous → conservative NO (0)."""
        assert parse("I think yes") == 0

    def test_no_not_substring_matched(self, parse):
        """'unknown' must NOT match as 'no' via substring — first-word parsing protects this."""
        assert parse("unknown") == 0  # ambiguous first word → 0, NOT a substring 'no' match

    def test_yes_but_no_first_word_wins(self, parse):
        """'yes, but actually no' → first word 'yes' wins."""
        assert parse("yes, but actually no") == 1

    def test_whitespace_stripped(self, parse):
        assert parse("  yes  ") == 1


# ---------------------------------------------------------------------------
# Class 5: Mycelium wiring — CLR gate gates ingest_entry
# ---------------------------------------------------------------------------


class TestMyceliumWiring:
    """CLRQualityGate.passes() controls whether ingest_entry is called.

    Patch at the SOURCE module (cohezion.compound.clr_quality_gate.CLRQualityGate)
    because _run_mycelium uses lazy imports — patching post_execution.CLRQualityGate
    would fail since that name never exists at module level.
    """

    def _exercise(self, success: bool, clr_passes: bool):
        """Run _run_mycelium with mocked CLRQualityGate; return the registry mock."""
        from cohezion.compound.post_execution import PostExecutionOrchestrator

        ex = MagicMock()
        mock_registry = MagicMock()
        # Set _mycelium_registry directly so the `hasattr` guard skips get_instance()
        ex._mycelium_registry = mock_registry

        orch = PostExecutionOrchestrator.__new__(PostExecutionOrchestrator)
        orch._ex = ex

        mock_gate = MagicMock()
        mock_gate.passes.return_value = clr_passes

        # Patch at source module — the lazy `from ... import CLRQualityGate` reads
        # from sys.modules['cohezion.compound.clr_quality_gate'].CLRQualityGate
        with patch(
            "cohezion.compound.clr_quality_gate.CLRQualityGate",
            return_value=mock_gate,
        ):
            orch._run_mycelium(success=success, skill_name="test_skill", task_description="desc")

        return mock_registry

    def test_clr_pass_allows_ingest(self):
        """When CLR gate passes, ingest_entry must be called."""
        registry = self._exercise(success=True, clr_passes=True)
        registry.ingest_entry.assert_called_once()

    def test_clr_fail_blocks_ingest(self):
        """When CLR gate fails, ingest_entry must NOT be called."""
        registry = self._exercise(success=True, clr_passes=False)
        registry.ingest_entry.assert_not_called()

    def test_failure_entry_skips_clr_entirely(self):
        """success=False → early return before CLR gate is ever instantiated."""
        from cohezion.compound.post_execution import PostExecutionOrchestrator

        ex = MagicMock()
        orch = PostExecutionOrchestrator.__new__(PostExecutionOrchestrator)
        orch._ex = ex

        mock_gate_cls = MagicMock(return_value=MagicMock())

        with patch("cohezion.compound.clr_quality_gate.CLRQualityGate", mock_gate_cls):
            orch._run_mycelium(success=False, skill_name="sk", task_description="d")

        # The class was never instantiated — early return at `if not success:`
        mock_gate_cls.assert_not_called()
