"""Item 888: CompoundHealthResponse.mcp_telemetry field -- health route telemetry field.

PRIMARY DISC.: response has mcp_telemetry key with dict value (kills impl that
omits the field or returns None); key present even when telemetry store is empty
(returns {}); non-empty telemetry reflects recorded data (kills impl that always
returns {}).
"""
from __future__ import annotations

from cohezion.api.routes.compound import CompoundHealthResponse
from cohezion.mcp.compound_mcp_telemetry import (
    _TELEMETRY,
    record_tool_call,
    get_tool_telemetry_summary,
)


def _reset_telemetry():
    _TELEMETRY.clear()


# ── model-level field checks ─────────────────────────────────────────────────

def test_mcp_telemetry_field_exists_on_model() -> None:
    """CompoundHealthResponse must have mcp_telemetry field (not just dynamically added)."""
    resp = CompoundHealthResponse()
    assert hasattr(resp, "mcp_telemetry"), "mcp_telemetry field missing from CompoundHealthResponse"


def test_mcp_telemetry_defaults_to_empty_dict() -> None:
    """When no value provided, mcp_telemetry defaults to {} not None."""
    resp = CompoundHealthResponse()
    assert resp.mcp_telemetry == {}
    assert resp.mcp_telemetry is not None


def test_mcp_telemetry_accepts_populated_dict() -> None:
    """CompoundHealthResponse accepts a non-empty mcp_telemetry dict."""
    payload = {"my_tool": {"call_count": 5, "error_rate": 0.2, "p50_ms": 10.0, "p95_ms": 50.0}}
    resp = CompoundHealthResponse(mcp_telemetry=payload)
    assert resp.mcp_telemetry == payload


def test_mcp_telemetry_type_is_dict() -> None:
    """mcp_telemetry field must be a dict, not a list or string."""
    resp = CompoundHealthResponse()
    assert isinstance(resp.mcp_telemetry, dict)


# ── primary discriminator: telemetry content is live, not hardcoded ──────────

def test_mcp_telemetry_empty_when_no_calls_primary_discriminator() -> None:
    """FALSIFIABLE: empty telemetry store -> mcp_telemetry = {} (not None or missing key).

    An impl that always returns {} passes this but fails the non-empty test below.
    An impl that returns None fails this test.
    """
    _reset_telemetry()
    summary = get_tool_telemetry_summary()
    resp = CompoundHealthResponse(mcp_telemetry=summary)
    assert "mcp_telemetry" in CompoundHealthResponse.model_fields
    assert resp.mcp_telemetry == {}


def test_mcp_telemetry_non_empty_when_calls_recorded() -> None:
    """FALSIFIABLE: when tool calls recorded, mcp_telemetry reflects them (kills always-{} impl)."""
    _reset_telemetry()
    record_tool_call("search_files", 15.0, True)
    record_tool_call("search_files", 25.0, True)
    record_tool_call("search_files", 20.0, False)
    summary = get_tool_telemetry_summary()
    resp = CompoundHealthResponse(mcp_telemetry=summary)
    assert "search_files" in resp.mcp_telemetry
    assert resp.mcp_telemetry["search_files"]["call_count"] == 3
    assert abs(resp.mcp_telemetry["search_files"]["error_rate"] - 1 / 3) < 1e-9


def test_mcp_telemetry_structure_matches_directory_format() -> None:
    """Each tool entry has call_count, error_rate, p50_ms, p95_ms keys."""
    _reset_telemetry()
    record_tool_call("read_file", 10.0, True)
    summary = get_tool_telemetry_summary()
    resp = CompoundHealthResponse(mcp_telemetry=summary)
    assert "read_file" in resp.mcp_telemetry
    entry = resp.mcp_telemetry["read_file"]
    assert set(entry.keys()) >= {"call_count", "error_rate", "p50_ms", "p95_ms"}


def test_mcp_telemetry_does_not_break_existing_fields() -> None:
    """Adding mcp_telemetry must not shadow or remove existing CompoundHealthResponse fields."""
    _reset_telemetry()
    resp = CompoundHealthResponse(
        total_executions=5,
        total_refinements=2,
        mcp_telemetry={"t": {"call_count": 1, "error_rate": 0.0, "p50_ms": 5.0, "p95_ms": 5.0}},
    )
    assert resp.total_executions == 5
    assert resp.total_refinements == 2
    assert "t" in resp.mcp_telemetry


def test_mcp_telemetry_multiple_tools() -> None:
    """Multiple tools all appear in the mcp_telemetry dict."""
    _reset_telemetry()
    record_tool_call("tool_a", 5.0, True)
    record_tool_call("tool_b", 10.0, False)
    summary = get_tool_telemetry_summary()
    resp = CompoundHealthResponse(mcp_telemetry=summary)
    assert "tool_a" in resp.mcp_telemetry
    assert "tool_b" in resp.mcp_telemetry
    assert resp.mcp_telemetry["tool_b"]["error_rate"] == 1.0
