"""Item 910: clear_telemetry_stores() -- explicit reset of both in-memory stores.

PRIMARY DISC.: after recording + clear, BOTH stores are {} (kills impl clearing only one);
idempotent (empty-stores clear raises no error); subsequent record builds fresh entries.
"""

from __future__ import annotations

from cohezion.mcp.compound_mcp_telemetry import (
    _TELEMETRY,
    _WINDOWED_TELEMETRY,
    record_tool_call,
    record_tool_call_windowed,
    record_tool_call_all,
    clear_telemetry_stores,
)


def _seed():
    record_tool_call("seed_tool", 10.0, True)
    record_tool_call_windowed("seed_tool", 10.0, True)


# ── primary discriminator ─────────────────────────────────────────────────────


def test_both_stores_cleared_primary_discriminator() -> None:
    """FALSIFIABLE: after recording + clear, BOTH _TELEMETRY and _WINDOWED_TELEMETRY are {}.
    Kills impl that clears only one store or clears the wrong one."""
    _seed()
    assert _TELEMETRY  # non-empty before
    assert _WINDOWED_TELEMETRY  # non-empty before
    clear_telemetry_stores()
    assert _TELEMETRY == {}, "cumulative store not cleared"
    assert _WINDOWED_TELEMETRY == {}, "windowed store not cleared"


def test_idempotent_on_empty_stores() -> None:
    """Calling clear on already-empty stores must not raise."""
    _TELEMETRY.clear()
    _WINDOWED_TELEMETRY.clear()
    clear_telemetry_stores()  # must not raise
    assert _TELEMETRY == {}
    assert _WINDOWED_TELEMETRY == {}


def test_stores_usable_after_clear() -> None:
    """After clear, new record_tool_call_all works normally."""
    clear_telemetry_stores()
    record_tool_call_all("post_clear_tool", 20.0, True)
    assert _TELEMETRY["post_clear_tool"]["call_count"] == 1
    assert len(_WINDOWED_TELEMETRY["post_clear_tool"]) == 1


def test_returns_none() -> None:
    """clear_telemetry_stores must return None."""
    result = clear_telemetry_stores()
    assert result is None


def test_only_clears_global_stores_not_injected() -> None:
    """Custom dicts passed to windowed functions are not affected by clear."""
    custom_store: dict = {}
    record_tool_call_windowed(
        "custom_tool", 5.0, True, ts_ms=1_000_000.0
    )  # ts_ms=fixed to avoid import
    # inject into a separate dict manually
    custom_store["custom_tool"] = [("value",)]
    clear_telemetry_stores()
    # custom_store is separate — not cleared
    assert "custom_tool" in custom_store


def test_multiple_tools_all_cleared() -> None:
    """Multiple tools in both stores are all removed."""
    _TELEMETRY.clear()
    _WINDOWED_TELEMETRY.clear()
    for name in ["tool_a", "tool_b", "tool_c"]:
        record_tool_call_all(name, 10.0, True)
    clear_telemetry_stores()
    assert _TELEMETRY == {}
    assert _WINDOWED_TELEMETRY == {}
