"""Unit tests for the Phoenix/OTel trace exporter.

Discriminating tests — each one would FAIL for a plausibly-wrong implementation.
"""

import pytest

from cohezion.compound.trace_exporter import execution_trace_to_otel_spans


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

TELEMETRY_TRACE = {
    "request_id": "req-abc123",
    "skill_name": "test_skill",
    "timestamp": "2026-06-22T12:00:00+00:00",
    "success": True,
    "total_latency_ms": 350.0,
    "total_tokens_in": 200,
    "total_tokens_out": 80,
    "steps_count": 3,
    "inflection_detected": False,
    "vault_logged": True,
    "steps": [
        {
            "step_name": "alignment_gate",
            "latency_ms": 50.0,
            "tokens_in": 80,
            "tokens_out": 0,
            "coherence": 0.70,
            "cache_hit": False,
            "error": None,
        },
        {
            "step_name": "execution",
            "latency_ms": 250.0,
            "tokens_in": 100,
            "tokens_out": 70,
            "coherence": 0.85,
            "cache_hit": False,
            "error": None,
        },
        {
            "step_name": "vault_log",
            "latency_ms": 50.0,
            "tokens_in": 20,
            "tokens_out": 10,
            "coherence": 0.90,
            "cache_hit": False,
            "error": None,
        },
    ],
}

RETROSPECTION_TRACE = {
    "cycle_id": "cycle-xyz789",
    "skill_name": "skill_refinement",
    "timestamp": 1750000000.0,  # Unix epoch float
    "success": False,
    "coherence_delta": -0.12,
    "tokens_used": 500,
    "insights": ["slow vault query"],
    "anomalies": ["timeout"],
}


# ---------------------------------------------------------------------------
# Test 1: trace_id mapping
# ---------------------------------------------------------------------------


class TestTraceIdMapping:
    """cycle_id takes priority over request_id; both map to trace_id."""

    def test_request_id_becomes_trace_id_when_no_cycle_id(self):
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        root = spans[0]
        # Must be the request_id, NOT some generated hash
        assert root.trace_id == "req-abc123"

    def test_cycle_id_takes_priority_over_request_id(self):
        """cycle_id wins when both keys are present."""
        trace = {**TELEMETRY_TRACE, "cycle_id": "cycle-override"}
        spans = execution_trace_to_otel_spans(trace)
        assert spans[0].trace_id == "cycle-override"

    def test_retrospection_cycle_id_maps_to_trace_id(self):
        spans = execution_trace_to_otel_spans(RETROSPECTION_TRACE)
        assert spans[0].trace_id == "cycle-xyz789"


# ---------------------------------------------------------------------------
# Test 2: status mapping
# ---------------------------------------------------------------------------


class TestStatusMapping:
    def test_success_true_maps_to_ok(self):
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        assert spans[0].status == "OK"

    def test_success_false_maps_to_error(self):
        spans = execution_trace_to_otel_spans(RETROSPECTION_TRACE)
        assert spans[0].status == "ERROR"

    def test_step_with_error_field_maps_to_error_status(self):
        trace = {
            **TELEMETRY_TRACE,
            "steps": [
                {
                    "step_name": "bad_step",
                    "latency_ms": 10.0,
                    "tokens_in": 0,
                    "tokens_out": 0,
                    "coherence": 0.5,
                    "cache_hit": False,
                    "error": "timeout",
                }
            ],
        }
        spans = execution_trace_to_otel_spans(trace)
        child = spans[1]
        assert child.status == "ERROR"
        assert child.attributes.get("cohezion.error") == "timeout"

    def test_step_without_error_maps_to_ok_status(self):
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        for child in spans[1:]:
            assert child.status == "OK"


# ---------------------------------------------------------------------------
# Test 3: child span creation
# ---------------------------------------------------------------------------


class TestChildSpanCreation:
    def test_one_child_span_per_step(self):
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        # 1 root + 3 children
        assert len(spans) == 4

    def test_root_is_first_span_with_no_parent(self):
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        root = spans[0]
        assert root.parent_span_id is None

    def test_child_spans_have_root_as_parent(self):
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        root_id = spans[0].span_id
        for child in spans[1:]:
            assert child.parent_span_id == root_id, (
                f"Child {child.name!r} parent is {child.parent_span_id!r}, expected {root_id!r}"
            )

    def test_child_span_names_match_step_names(self):
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        child_names = [s.name for s in spans[1:]]
        assert child_names == ["alignment_gate", "execution", "vault_log"]

    def test_no_steps_produces_root_only(self):
        trace = {
            "request_id": "r1",
            "skill_name": "bare",
            "success": True,
            "total_latency_ms": 100.0,
        }
        spans = execution_trace_to_otel_spans(trace)
        assert len(spans) == 1
        assert spans[0].parent_span_id is None


# ---------------------------------------------------------------------------
# Test 4: coherence_delta in attributes
# ---------------------------------------------------------------------------


class TestCoherenceDelta:
    def test_root_span_has_coherence_delta_attribute(self):
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        assert "cohezion.coherence_delta" in spans[0].attributes

    def test_retrospection_coherence_delta_preserved(self):
        spans = execution_trace_to_otel_spans(RETROSPECTION_TRACE)
        assert spans[0].attributes["cohezion.coherence_delta"] == pytest.approx(-0.12)

    def test_telemetry_coherence_delta_inferred_from_first_last_step(self):
        """Root coherence_delta = last_step.coherence − first_step.coherence."""
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        # first step coherence=0.70, last step coherence=0.90 → delta=+0.20
        assert spans[0].attributes["cohezion.coherence_delta"] == pytest.approx(0.20)

    def test_child_spans_have_incremental_coherence_delta(self):
        """Each child span carries the coherence change from its predecessor."""
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        # step[0]: coherence=0.70, prev=None → delta=0.00 (first step baseline)
        # step[1]: coherence=0.85, prev=0.70 → delta=+0.15
        # step[2]: coherence=0.90, prev=0.85 → delta=+0.05
        child_deltas = [s.attributes["cohezion.coherence_delta"] for s in spans[1:]]
        assert child_deltas[0] == pytest.approx(0.00)
        assert child_deltas[1] == pytest.approx(0.15)
        assert child_deltas[2] == pytest.approx(0.05)


# ---------------------------------------------------------------------------
# Test 5: timing reconstruction
# ---------------------------------------------------------------------------


class TestTimingReconstruction:
    def test_root_span_end_time_equals_start_plus_total_latency(self):
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        root = spans[0]
        assert root.end_time_ms == pytest.approx(root.start_time_ms + 350.0)

    def test_child_spans_are_sequential_from_root_start(self):
        """Child span start times are cumulative offsets from root start."""
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        root_start = spans[0].start_time_ms
        # step 0: starts at root_start, ends at +50ms
        assert spans[1].start_time_ms == pytest.approx(root_start)
        assert spans[1].end_time_ms == pytest.approx(root_start + 50.0)
        # step 1: starts at root_start+50, ends at +300ms
        assert spans[2].start_time_ms == pytest.approx(root_start + 50.0)
        assert spans[2].end_time_ms == pytest.approx(root_start + 300.0)

    def test_iso_timestamp_parsed_to_milliseconds(self):
        """ISO timestamp is converted to epoch-ms, not left as a string."""
        spans = execution_trace_to_otel_spans(TELEMETRY_TRACE)
        root = spans[0]
        # 2026-06-22T12:00:00+00:00 → epoch_ms > 1e12
        assert root.start_time_ms > 1e12, "start_time_ms must be epoch milliseconds"

    def test_unix_float_timestamp_parsed_to_milliseconds(self):
        spans = execution_trace_to_otel_spans(RETROSPECTION_TRACE)
        root = spans[0]
        # 1750000000.0 seconds → 1750000000000.0 ms
        assert root.start_time_ms == pytest.approx(1750000000.0 * 1000.0)
