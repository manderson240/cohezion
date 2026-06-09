"""Item 962: get_all_windowed_tool_telemetry_full(window_ms, *, store=None, now_ms=None) -> dict[str, dict]
-- full 6-key windowed profile for every active tool.

PRIMARY DISC.: 2 tools each with recent calls -> dict with exactly 2 keys, each
value having exactly 6 keys. Kills impl returning all tools regardless of window
(including tools with only old calls). Kills impl returning 4-key windowed stats.
empty / no-recent-calls -> {}; returns dict[str, dict].
"""
from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    clear_telemetry_stores,
    get_all_windowed_tool_telemetry_full,
)

_EXPECTED_KEYS = frozenset({
    "call_count", "error_count", "error_rate", "success_rate", "p50_ms", "p95_ms",
})
_NOW = 1_000_000.0
_WIN = 500.0


def _make_store(entries: dict[str, list[tuple[float, float, bool]]]) -> dict:
    return {tool: list(recs) for tool, recs in entries.items()}


def _reset():
    clear_telemetry_stores()


def test_two_active_tools_two_keys_six_each_primary_discriminator() -> None:
    """FALSIFIABLE: 2 tools with recent calls -> dict with exactly 2 keys, each 6 keys.
    Kills impl returning 4-key stats; kills impl including tools with no recent calls."""
    _reset()
    store = _make_store({
        "awttf_a": [(_NOW - 10, 10.0, True)] * 2,
        "awttf_b": [(_NOW - 10, 50.0, False)],
    })
    result = get_all_windowed_tool_telemetry_full(_WIN, store=store, now_ms=_NOW)
    assert isinstance(result, dict)
    assert set(result.keys()) == {"awttf_a", "awttf_b"}
    for tool_name, profile in result.items():
        assert set(profile.keys()) == _EXPECTED_KEYS, (
            f"Tool {tool_name!r} has wrong keys: {set(profile.keys())}"
        )


def test_empty_store_returns_empty_dict() -> None:
    """No calls -> {}."""
    _reset()
    assert get_all_windowed_tool_telemetry_full(_WIN, store={}, now_ms=_NOW) == {}


def test_returns_dict_type() -> None:
    """Return type is dict."""
    store = _make_store({"rtype_awttf": [(_NOW - 10, 5.0, True)]})
    assert isinstance(get_all_windowed_tool_telemetry_full(_WIN, store=store, now_ms=_NOW), dict)


def test_tool_with_only_old_calls_excluded() -> None:
    """Tool with calls only outside window is excluded (empty recent = not active)."""
    store = _make_store({
        "awttf_recent": [(_NOW - 10, 5.0, True)],
        "awttf_old": [(_NOW - _WIN - 100, 5.0, True)],   # outside window
    })
    result = get_all_windowed_tool_telemetry_full(_WIN, store=store, now_ms=_NOW)
    assert "awttf_recent" in result
    assert "awttf_old" not in result   # excluded: no recent calls


def test_all_calls_outside_window_returns_empty_dict() -> None:
    """All calls outside window -> {}."""
    store = _make_store({
        "awttf_all_old": [(_NOW - _WIN - 100, 5.0, True)],
    })
    assert get_all_windowed_tool_telemetry_full(_WIN, store=store, now_ms=_NOW) == {}


def test_consistent_with_windowed_tool_telemetry_full() -> None:
    """Values consistent with get_windowed_tool_telemetry_full per tool."""
    from cohezion.mcp.compound_mcp_telemetry import get_windowed_tool_telemetry_full
    _reset()
    store = _make_store({
        "consist_awttf_a": [(_NOW - 10, lat, True) for lat in [5.0, 15.0, 25.0]],
        "consist_awttf_b": [(_NOW - 10, 100.0, False)],
    })
    all_full = get_all_windowed_tool_telemetry_full(_WIN, store=store, now_ms=_NOW)
    for tool in ("consist_awttf_a", "consist_awttf_b"):
        individual = get_windowed_tool_telemetry_full(tool, _WIN, store=store, now_ms=_NOW)
        for key in _EXPECTED_KEYS:
            assert abs(all_full[tool][key] - individual[key]) < 0.001, (
                f"Mismatch for {tool!r} key {key!r}"
            )


def test_single_tool_one_key() -> None:
    """One tool with recent calls -> dict with exactly 1 key."""
    store = _make_store({"single_awttf": [(_NOW - 10, 7.0, True)]})
    result = get_all_windowed_tool_telemetry_full(_WIN, store=store, now_ms=_NOW)
    assert len(result) == 1
    assert "single_awttf" in result
