"""EventBus lifecycle wiring in the unified perpetual orchestrator (AGENTS.md mandate 5).

Covers:
- Master-cycle AGENT_COMPLETE publishes reach a RUNNING bus (no "bus not running" drops).
- start_event_bus() is idempotent (bus not double-started, bridge not double-subscribed).
- stop_event_bus() drains queued events before the processor task dies.
- The pre-existing OOMGuard park gate in execute_master_cycle is unchanged.
- run_forever() starts the bus (bus first, bridge second) and stops it on exit.

All SurrealDB I/O is mocked at the CrossSessionEventBridge.surreal_client level —
no real SurrealDB is contacted. The global bus singleton is reset per repo
convention (cohezion.core.event_bus._event_bus = None).
"""

from __future__ import annotations

import asyncio
import logging
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.autopoiesis.tri_silicon_engine import TriSiliconCycleResult
from cohezion.core.cross_session_event_bridge import CrossSessionEventBridge
from cohezion.core.event_bus import Event, EventBus, EventType
from cohezion.ops.unified_perpetual_orchestrator import (
    MasterCycleOutcome,
    PhaseResult,
    UnifiedPerpetualLoopDaemon,
)
from cohezion.reliability.oom_guard import MemoryState


_DROP_MSG = "Event dropped (bus not running)"


@pytest.fixture
def mock_daemon():
    daemon = UnifiedPerpetualLoopDaemon(interval_seconds=1.0, cpu_threads=2)
    # Replace the default SurrealClient with a mock so no real DB is touched.
    daemon.event_bridge = CrossSessionEventBridge(
        event_bus=daemon.event_bus,
        session_id="test_session",
        surreal_client=AsyncMock(),
    )
    return daemon


@pytest.fixture(autouse=True)
def reset_event_bus_singleton():
    """Repo convention: reset module singletons between tests."""
    import cohezion.core.event_bus as eb

    eb._event_bus = None
    yield
    eb._event_bus = None


def _tri_result() -> TriSiliconCycleResult:
    return TriSiliconCycleResult(
        cycle=1,
        npu_guidance="High-leverage focus",
        npu_model="llama3.2-1b-FLM",
        npu_latency_ms=120.0,
        cpu_arc_programs_found=1,
        cpu_kaggriculture_win_rate=0.85,
        cpu_sheaf_converged=True,
        cpu_latency_ms=80.0,
        igpu_synthesis_triggered=False,
        delta_entropy=-0.5848,
        autoharness_verified=True,
        total_latency_ms=200.0,
        details={"reward": 1.0},
    )


async def _drain(bus: EventBus, timeout: float = 2.0) -> None:
    """Deterministically wait until the bus processor has drained its queue."""
    await asyncio.wait_for(bus._queue.join(), timeout=timeout)


@pytest.mark.asyncio
async def test_master_cycle_publishes_agent_complete_to_running_bus(mock_daemon, caplog):
    """(a) With the bus started, the cycle's AGENT_COMPLETE is delivered, not dropped."""
    with caplog.at_level(logging.WARNING):
        await mock_daemon.start_event_bus()

    seen: list[Event] = []
    mock_daemon.event_bus.register_handler(
        lambda e: _collect(seen, e),
        None,  # type: ignore[arg-type]
    )
    mock_daemon.event_bridge.surreal_client.query.return_value = [{"result": []}]

    with (
        patch.object(mock_daemon.tri_silicon_engine, "execute_cycle", return_value=_tri_result()),
        patch.object(
            mock_daemon.control_plane.projects,
            "get_kanban_summary",
            return_value={"approved": 0, "completed": 5},
        ),
        patch.object(
            mock_daemon.control_plane.projects,
            "get_kaggle_tracks",
            return_value=[],
        ),
        patch.object(
            mock_daemon.evaluator, "evaluate_model_on_task", side_effect=RuntimeError("skip")
        ),
        # Phases 5 and 6 persist to live SurrealDB when unpatched; this test is about
        # the bus, so keep them hermetic.
        patch.object(
            mock_daemon,
            "run_trace_refactor_phase",
            return_value=PhaseResult("trace_goal_refactor", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_sentry_phase",
            return_value=PhaseResult("control_sentry", True, 10.0, "OK"),
        ),
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        outcome = await mock_daemon.execute_master_cycle(cycle_num=1)

    await _drain(mock_daemon.event_bus)

    assert isinstance(outcome, MasterCycleOutcome)
    agent_events = [e for e in seen if e.type is EventType.AGENT_COMPLETE]
    assert len(agent_events) == 1, "AGENT_COMPLETE must reach a running bus exactly once"
    assert agent_events[0].source == "autopoiesis_engine"
    # Bridge consumer side ran: handler persisted to (mock) SurrealDB event_log.
    assert mock_daemon.event_bridge.surreal_client.query.await_count >= 1
    # No drop warnings, no queue drops.
    assert _DROP_MSG not in caplog.text
    assert mock_daemon.event_bus.get_metrics()["dropped"] == 0

    await mock_daemon.stop_event_bus()


async def _collect(seen: list[Event], event: Event) -> None:
    seen.append(event)


@pytest.mark.asyncio
async def test_publish_before_start_still_warns_and_fails(mock_daemon, caplog):
    """Negative control: WITHOUT the lifecycle wiring, publish drops (regression canary)."""
    with caplog.at_level(logging.WARNING):
        accepted = await mock_daemon.event_bus.publish(
            Event.agent_complete("autopoiesis_engine", result={}, duration_ms=1.0)
        )
    assert accepted is False
    assert _DROP_MSG in caplog.text


@pytest.mark.asyncio
async def test_start_event_bus_idempotent(mock_daemon):
    """(b) Double start must not double-start the bus or double-subscribe the bridge."""
    await mock_daemon.start_event_bus()
    task_first = mock_daemon.event_bus._processor_task
    assert task_first is not None
    assert mock_daemon.event_bus._running is True

    await mock_daemon.start_event_bus()  # second call — must no-op

    assert mock_daemon.event_bus._processor_task is task_first
    assert len(mock_daemon.event_bus._wildcard_handlers) == 1, "bridge subscribed twice"
    assert mock_daemon.event_bridge._subscribed is True

    await mock_daemon.stop_event_bus()


@pytest.mark.asyncio
async def test_stop_event_bus_drains_queued_events(mock_daemon):
    """(c) stop() flushes queued events cleanly and leaves the bus stopped."""
    await mock_daemon.start_event_bus()
    seen: list[int] = []
    mock_daemon.event_bus.register_handler(lambda e: _collect_n(seen, e), EventType.CUSTOM)

    for n in range(8):
        await mock_daemon.event_bus.publish(
            Event(type=EventType.CUSTOM, source="drain-test", payload={"n": n})
        )
    await mock_daemon.stop_event_bus(drain_timeout=5.0)

    assert sorted(seen) == list(range(8)), "stop() must drain queued events"
    assert mock_daemon.event_bus._running is False
    assert mock_daemon.event_bus._queue.qsize() == 0


async def _collect_n(seen: list[int], event: Event) -> None:
    await asyncio.sleep(0.01)  # force real drain work under stop()
    seen.append(event.payload["n"])


@pytest.mark.asyncio
async def test_stop_event_bus_without_start_is_safe(mock_daemon):
    """stop() on a never-started bus must not raise (clean no-op)."""
    await mock_daemon.stop_event_bus()
    assert mock_daemon.event_bus._running is False


@pytest.mark.asyncio
async def test_preexisting_park_gate_unchanged(mock_daemon, caplog):
    """(d) The OOMGuard park in execute_master_cycle behaves exactly as before."""
    constrained = MemoryState(
        available_gb=10.0,
        total_gb=128.0,
        swap_used_gb=0.0,
        is_safe=False,
        dynamic_floor_gb=20.0,
        gtt_used_gb=60.0,
        gtt_total_gb=96.0,
        psi_some_10=25.0,
    )
    safe = MemoryState(
        available_gb=40.0,
        total_gb=128.0,
        swap_used_gb=0.0,
        is_safe=True,
        dynamic_floor_gb=20.0,
        gtt_used_gb=20.0,
        gtt_total_gb=96.0,
        psi_some_10=0.0,
    )
    with (
        patch(
            "cohezion.reliability.oom_guard.OOMGuard.get_memory_state",
            side_effect=[constrained, safe, safe],  # pre-flight, park recheck, memory_after
        ),
        patch.object(
            mock_daemon,
            "run_autopoiesis_phase",
            return_value=PhaseResult("autopoiesis", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_kaggle_compute_phase",
            return_value=PhaseResult("kaggle_compute", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_actioner_phase",
            return_value=PhaseResult("actioner_queue", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_model_eval_phase",
            return_value=PhaseResult("model_eval", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_trace_refactor_phase",
            return_value=PhaseResult("trace_goal_refactor", True, 10.0, "OK"),
        ),
        patch.object(
            mock_daemon,
            "run_sentry_phase",
            return_value=PhaseResult("control_sentry", True, 10.0, "OK"),
        ),
        patch("asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
        caplog.at_level(logging.WARNING),
    ):
        outcome = await mock_daemon.execute_master_cycle(cycle_num=7)

    assert outcome.success is True
    # Mirrors tests/unit/test_unified_perpetual_orchestrator.py on main: six phases
    # since trace_goal_refactor joined the cycle (#294).
    assert len(outcome.phases) == 6
    mock_sleep.assert_any_await(30)  # the park pause is intact
    assert "Memory constrained before Cycle 7" in caplog.text


@pytest.mark.asyncio
async def test_run_forever_starts_and_stops_bus(mock_daemon):
    """run_forever: bus first, bridge second at startup; clean bounded stop at exit."""
    assert mock_daemon.event_bus._running is False

    with (
        patch.object(
            mock_daemon,
            "execute_master_cycle",
            new=AsyncMock(return_value=MagicMock(success=True)),
        ) as mock_exec,
        patch("asyncio.sleep", new_callable=AsyncMock),
    ):
        await mock_daemon.run_forever(max_cycles=1)

    assert mock_exec.call_count == 1
    # Bridge got subscribed during startup...
    assert mock_daemon.event_bridge._subscribed is True
    # ...and the bus was cleanly stopped by the finally block.
    assert mock_daemon.event_bus._running is False
    assert (
        mock_daemon.event_bus._processor_task is None
        or mock_daemon.event_bus._processor_task.done()
    )


@pytest.mark.asyncio
async def test_bus_first_bridge_second_startup_order(mock_daemon):
    """Explicit startup order: after start_event_bus() both are live, bus draining first."""
    order: list[str] = []
    real_bus_start = mock_daemon.event_bus.start
    real_bridge_init = mock_daemon.event_bridge.initialize

    async def spy_bus_start() -> None:
        await real_bus_start()
        order.append("bus")

    async def spy_bridge_init() -> None:
        await real_bridge_init()
        order.append("bridge")

    with (
        patch.object(mock_daemon.event_bus, "start", side_effect=spy_bus_start),
        patch.object(mock_daemon.event_bridge, "initialize", side_effect=spy_bridge_init),
    ):
        await mock_daemon.start_event_bus()

    assert order == ["bus", "bridge"]
    await mock_daemon.stop_event_bus()
