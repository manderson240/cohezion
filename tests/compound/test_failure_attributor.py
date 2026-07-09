"""Tests for FailureAttributor — discriminating tests for all four FAPO categories.

Each test is designed to fail against the most-plausible *wrong* implementation:
  - A classifier that always returns "reasoning" fails the format/cascading/retrieval tests.
  - A classifier that uses output length for everything fails the format boundary.
  - A classifier that confuses retrieval/reasoning based on quality score alone fails
    the discriminating retrieval vs reasoning boundary test.

V-Model: T3 (unit tests) on D1 (deterministic 4-category classifier).
"""

import pytest

from cohezion.compound.failure_attributor import (
    _CASCADING_THRESHOLD,
    _REASONING_QUALITY_THRESHOLD,
    FailureAttributor,
)


@pytest.fixture
def fa() -> FailureAttributor:
    return FailureAttributor()


# ---------------------------------------------------------------------------
# Null path — healthy execution
# ---------------------------------------------------------------------------


class TestNoAttribution:
    def test_high_quality_no_validation_error_returns_none(self, fa):
        """Successful execution must not be attributed."""
        metrics = {"anomaly_score": 0.1}  # quality_score = 0.9 > threshold
        result = fa.classify("some output", metrics, decision_paths=["vault/path"])
        assert result is None

    def test_threshold_boundary_just_above_returns_none(self, fa):
        """quality_score exactly above threshold → no attribution."""
        threshold_anomaly = 1.0 - _REASONING_QUALITY_THRESHOLD - 0.001
        metrics = {"anomaly_score": threshold_anomaly}
        result = fa.classify("x" * 50, metrics, decision_paths=["something"])
        assert result is None


# ---------------------------------------------------------------------------
# Category 1: FORMAT
# ---------------------------------------------------------------------------


class TestFormatAttribution:
    def test_explicit_validation_failed_flag_gives_format(self, fa):
        """output_validation_failed=True → format, regardless of output content."""
        metrics = {
            "anomaly_score": 0.8,
            "output_validation_failed": True,
            "output_validation_error": "JSON parse error at position 5: Expecting value",
        }
        result = fa.classify('{"broken": ', metrics)
        assert result is not None
        assert result.category == "format"
        assert result.escalation_level == "L1"

    def test_format_evidence_contains_validator_message(self, fa):
        """Format attribution must surface the exact validator error (for prompt injection)."""
        metrics = {
            "anomaly_score": 0.8,
            "output_validation_failed": True,
            "output_validation_error": "JSON parse error at position 5: Expecting value",
        }
        result = fa.classify('{"broken": ', metrics)
        assert result is not None
        assert "JSON parse error" in result.evidence

    def test_invalid_json_output_gives_format_not_reasoning(self, fa):
        """Format-INVALID output with guidance present must classify format, not reasoning.

        Discriminating: a wrong implementation that ignores output_validator and always
        falls through to reasoning would fail this test.
        """
        metrics = {"anomaly_score": 0.8}  # low quality
        result = fa.classify('{"key": missing_value}', metrics, decision_paths=["vault/x"])
        assert result is not None
        assert result.category == "format"

    def test_valid_json_does_not_classify_as_format(self, fa):
        """Valid JSON output must not be classified as format, even on low quality."""
        metrics = {"anomaly_score": 0.8}  # low quality score
        result = fa.classify('{"answer": "wrong but valid JSON"}', metrics, decision_paths=["v"])
        # Should NOT be format — it's valid JSON
        assert result is None or result.category != "format"


# ---------------------------------------------------------------------------
# Category 2: CASCADING
# ---------------------------------------------------------------------------


class TestCascadingAttribution:
    def test_empty_output_gives_cascading(self, fa):
        """Empty output → cascading (upstream produced nothing)."""
        metrics = {"anomaly_score": 0.9}
        result = fa.classify("", metrics, decision_paths=["vault/x"])
        assert result is not None
        assert result.category == "cascading"
        assert result.escalation_level == "L3"

    def test_near_empty_output_gives_cascading_not_retrieval(self, fa):
        """Near-empty output with empty decision_paths → cascading (not retrieval).

        Discriminating: a wrong implementation that checks retrieval before cascading
        would classify this as retrieval. Cascading must win because empty output
        means the upstream component failed regardless of what vault returned.
        """
        metrics = {"anomaly_score": 0.9}
        short_output = "x" * (_CASCADING_THRESHOLD - 1)
        result = fa.classify(short_output, metrics, decision_paths=[])
        assert result is not None
        assert result.category == "cascading"  # NOT retrieval

    def test_output_at_threshold_not_cascading(self, fa):
        """Output exactly at (not below) threshold → not cascading."""
        metrics = {"anomaly_score": 0.8}
        output_at_threshold = "x" * _CASCADING_THRESHOLD
        result = fa.classify(output_at_threshold, metrics, decision_paths=[])
        # At threshold it should proceed to retrieval (empty paths) or reasoning
        assert result is None or result.category != "cascading"


# ---------------------------------------------------------------------------
# Category 3: RETRIEVAL
# ---------------------------------------------------------------------------


class TestRetrievalAttribution:
    def test_no_decision_paths_gives_retrieval(self, fa):
        """Non-empty output with empty decision_paths → retrieval (not reasoning).

        Discriminating: a wrong implementation that only looks at quality_score would
        classify this as reasoning. Empty decision_paths must override quality signal.
        """
        metrics = {"anomaly_score": 0.8}  # low quality
        output = "x" * (_CASCADING_THRESHOLD + 10)  # non-empty, non-cascading
        result = fa.classify(output, metrics, decision_paths=[])
        assert result is not None
        assert result.category == "retrieval"
        assert result.escalation_level == "L2"

    def test_none_decision_paths_gives_retrieval(self, fa):
        """decision_paths=None treated same as empty list → retrieval."""
        metrics = {"anomaly_score": 0.8}
        output = "a substantial response that is definitely long enough"
        result = fa.classify(output, metrics, decision_paths=None)
        assert result is not None
        assert result.category == "retrieval"

    def test_with_decision_paths_does_not_give_retrieval(self, fa):
        """Non-empty decision_paths → must not classify as retrieval.

        If decision_paths has content, the retrieval step was not empty — the issue
        is downstream (reasoning), not upstream (retrieval).
        """
        metrics = {"anomaly_score": 0.8}  # low quality, but had guidance
        output = "a substantial response that is definitely long enough"
        result = fa.classify(output, metrics, decision_paths=["vault/pattern/foo"])
        assert result is not None
        assert result.category != "retrieval"


# ---------------------------------------------------------------------------
# Category 4: REASONING
# ---------------------------------------------------------------------------


class TestReasoningAttribution:
    def test_format_valid_non_empty_with_guidance_gives_reasoning(self, fa):
        """Format-valid, non-empty output WITH guidance → reasoning (not retrieval).

        Discriminating: a wrong implementation that checks decision_paths before
        quality score would mis-classify this. Reasoning is the fallthrough after
        all other categories are eliminated.
        """
        metrics = {"anomaly_score": 0.8}  # low quality = poor reasoning
        output = "The answer to everything is 42 but this is incorrect"
        result = fa.classify(output, metrics, decision_paths=["vault/context/guidance"])
        assert result is not None
        assert result.category == "reasoning"
        assert result.escalation_level == "L1"

    def test_reasoning_evidence_includes_quality_score(self, fa):
        """Reasoning attribution evidence must include the quality_score (for PRIME injection)."""
        metrics = {"anomaly_score": 0.5}  # quality_score = 0.5
        output = "a substantial response that is long enough to be non-cascading clearly"
        result = fa.classify(output, metrics, decision_paths=["vault/x"])
        assert result is not None
        assert result.category == "reasoning"
        assert "quality_score" in result.evidence

    def test_reasoning_is_not_format_for_valid_json(self, fa):
        """Valid JSON wrong answer → reasoning, not format.

        Discriminating: checks that format detection doesn't fire on valid JSON
        even when the answer is semantically wrong (low quality).
        """
        metrics = {"anomaly_score": 0.8}
        valid_but_wrong_json = '{"result": "wrong_answer", "confidence": 0.1}'
        result = fa.classify(valid_but_wrong_json, metrics, decision_paths=["vault/x"])
        # Valid JSON should not be categorized as format failure
        assert result is None or result.category == "reasoning"


# ---------------------------------------------------------------------------
# Structural guard (harness invariant T1)
# ---------------------------------------------------------------------------


class TestStructural:
    def test_classify_signature_has_required_params(self):
        """T1 structural: classify() must accept output, metrics, decision_paths."""
        import inspect

        params = inspect.signature(FailureAttributor.classify).parameters
        assert "output" in params
        assert "metrics" in params
        assert "decision_paths" in params

    def test_attribution_category_is_one_of_four(self, fa):
        """All returned categories must be one of the four FAPO categories."""
        valid_categories = {"format", "cascading", "retrieval", "reasoning"}
        test_cases = [
            # format
            (
                '{"bad": ',
                {
                    "anomaly_score": 0.9,
                    "output_validation_failed": True,
                    "output_validation_error": "bad",
                },
                [],
            ),
            # cascading
            ("", {"anomaly_score": 0.9}, ["vault/x"]),
            # retrieval
            ("x" * 30, {"anomaly_score": 0.9}, []),
            # reasoning
            ("x" * 30, {"anomaly_score": 0.9}, ["vault/x"]),
        ]
        for output, metrics, paths in test_cases:
            result = fa.classify(output, metrics, paths)
            if result is not None:
                assert result.category in valid_categories
                assert result.escalation_level in {"L1", "L2", "L3"}
