"""Discriminating tests for agent.unified_harness (V-model audit, 2026-06-05).

Consolidated 2026-07-13 into tests/agents/ (the canonical agent-test directory)
from the singular-dir anomaly tests/agent/, REPLACING a stale duplicate that tested
a removed UnifiedAgent(use_gaia=, use_autocontext=, use_autoharness=, use_metaharness=)
harness-integration API. The current UnifiedAgent(executor, tools, *, guidance, ...) is
covered by test_unified_harness_guidance.py; this file covers ToolRegistry — the pure
registration/dispatch core — plus autocontext_monitor.

Each test fails a plausible wrong impl:
  - __init__ that forgets to register the default tools,
  - execute that doesn't pass args as kwargs (**args) or doesn't raise on an unknown tool,
  - register that doesn't overwrite an existing name.

FINDING (pin-actual, minor): autocontext_monitor ignores `history` and always returns
warn=False/critical=False -- a context monitor that can never fire. Pinned below.
"""

from __future__ import annotations

import asyncio

from cohezion.agent.unified_harness import ToolRegistry, autocontext_monitor


DEFAULTS = {"bash", "python", "file_read", "file_write", "browser", "think"}


def test_default_tools_registered() -> None:
    assert set(ToolRegistry()._tools) >= DEFAULTS


def test_register_and_execute_passes_args_as_kwargs() -> None:
    reg = ToolRegistry()

    async def add(a, b):
        return a + b

    reg.register("add", add)
    assert asyncio.run(reg.execute("add", {"a": 2, "b": 3})) == 5


def test_execute_unknown_tool_raises() -> None:
    reg = ToolRegistry()
    try:
        asyncio.run(reg.execute("does_not_exist", {}))
        raise AssertionError("expected ValueError for unknown tool")
    except ValueError as e:
        assert "does_not_exist" in str(e)


def test_register_overwrites_existing_name() -> None:
    reg = ToolRegistry()

    async def replacement():
        return "new"

    reg.register("think", replacement)  # 'think' is a default
    assert asyncio.run(reg.execute("think", {})) == "new"


def test_autocontext_monitor_is_input_independent_stub() -> None:
    # pin-actual: warn/critical are always False regardless of history length/content.
    empty = autocontext_monitor([])
    huge = autocontext_monitor([{"role": "user", "content": "x" * 100_000}] * 500)
    assert empty == huge == {"pct": 0.0, "warn": False, "critical": False}
