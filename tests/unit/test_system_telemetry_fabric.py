"""Unit tests for SystemTelemetryFabric (resources, journals, workspaces, EventBus)."""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from cohezion.core.event_bus import EventBus, EventType
from cohezion.cybernetics.system_telemetry_fabric import (
    JournalAlert,
    ResourceSnapshot,
    SystemTelemetryFabric,
    WorktreeEntry,
)


@pytest.mark.asyncio
async def test_system_telemetry_fabric_sample_and_publish():
    bus = EventBus()
    await bus.start()
    received_events = []

    async def mock_handler(event):
        received_events.append(event)

    bus.register_handler(mock_handler, event_type=None)

    fabric = SystemTelemetryFabric()

    with (
        patch.object(
            fabric,
            "sample_resources",
            return_value=ResourceSnapshot(
                cpu_pct=15.2,
                avail_mem_gib=32.0,
                swap_used_gib=5.0,
                gtt_used_gib=1.5,
                psi_pressure=0.0,
                is_safe_local=True,
                safety_reason="Local Silicon Safe",
            ),
        ),
        patch.object(
            fabric,
            "sample_journals",
            return_value=[
                JournalAlert(facility="journalctl", priority="warning", message="amdgpu: test warning")
            ],
        ),
        patch.object(
            fabric,
            "sample_workspaces",
            return_value=[
                WorktreeEntry(path="/tmp/test_wt", branch="main", commit="abc1234", is_clean=True)
            ],
        ),
    ):
        result = await fabric.audit_and_publish(bus, source="test_runner")

        assert result["resources"]["cpu_pct"] == 15.2
        assert result["alert_count"] == 1
        assert result["workspace_count"] == 1

        # Allow EventBus async background processor to drain events to handlers
        await asyncio.sleep(0.05)

        # Check emitted events
        event_types = {e.type for e in received_events}
        assert EventType.RESOURCE_TELEMETRY in event_types
        assert EventType.SYSTEM_JOURNAL_ALERT in event_types
        assert EventType.WORKSPACE_STATE in event_types

    await bus.stop()


def test_system_telemetry_fabric_live_sample():
    fabric = SystemTelemetryFabric()
    res = fabric.sample_resources()
    assert isinstance(res.cpu_pct, float)
    assert res.avail_mem_gib > 0.0
    assert isinstance(res.is_safe_local, bool)

    worktrees = fabric.sample_workspaces()
    assert isinstance(worktrees, list)
    assert len(worktrees) > 0
    assert any("ollama_lemonade_kaggle_push" in wt.path or "cohezion" in wt.path for wt in worktrees)
