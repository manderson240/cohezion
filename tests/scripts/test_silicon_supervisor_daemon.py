"""Composition tests for the silicon supervisor daemon.

`stall_events(n)` is unit-tested in tests/inference/test_silicon_supervisor.py.
That proves the RULE. It does not prove the daemon ever passes n > 1 -- and
every defect found in this subsystem lived in composition, not in a function:
a correct diff handed a baseline its caller had already destroyed, a correct
state machine whose caller overwrote the memory it depended on. So the seam
gets its own test.

The daemon is a script, not a package module, so it is loaded by path.
"""

from __future__ import annotations

import asyncio
import importlib.util
from pathlib import Path
from typing import Any

import pytest


REPO = Path(__file__).resolve().parents[2]
DAEMON_PATH = REPO / "scripts" / "ops" / "silicon_supervisor_daemon.py"


def _load_daemon():
    spec = importlib.util.spec_from_file_location("_silicon_daemon", DAEMON_PATH)
    if spec is None or spec.loader is None:  # pragma: no cover - import plumbing
        pytest.skip(f"cannot load {DAEMON_PATH}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


HEALTHY_STORAGE = {
    "model_storage": {
        "path": "/store",
        "total_bytes": 800 * 1024**3,
        "used_bytes": 400 * 1024**3,
        "free_bytes": 400 * 1024**3,
    }
}


def _run_cycles(monkeypatch, n: int, get_fn) -> tuple[Any, list[str]]:
    daemon = _load_daemon()
    emitted: list[str] = []

    async def capture(bus, events):
        emitted.extend(e.kind for e in events)
        return len(events)

    monkeypatch.setattr(daemon, "_get", get_fn)
    monkeypatch.setattr(daemon, "publish_events", capture)

    async def drive():
        state = daemon.CycleState()
        for _ in range(n):
            state = await daemon.cycle(state, bus=None, apply_changes=False, quiet=True)
        return state

    return asyncio.run(drive()), emitted


@pytest.mark.skipif(not DAEMON_PATH.exists(), reason="daemon script not present")
def test_t2_permanent_census_death_escalates_exactly_once(monkeypatch) -> None:
    """The blind spot: cheap endpoint alive, expensive endpoints permanently dead.

    Making `router_unreachable` require the CHEAP endpoint to fail closed one
    false-alarm hole and opened another: nothing could escalate. A stall that
    never clears must page, and must page ONCE.
    """

    async def cheap_alive_expensive_dead(path):
        if path == "/api/v1/system-info":
            return HEALTHY_STORAGE
        raise TimeoutError("simulated permanent census death")

    state, emitted = _run_cycles(monkeypatch, 12, cheap_alive_expensive_dead)

    assert emitted.count("census_stalled") == 1, emitted
    assert emitted.count("census_stalled_persistent") == 1, emitted
    assert state.stall_polls == 12
    assert state.census_stalled is True
    # The router IS up -- calling this an outage is the false alarm we removed.
    assert state.router_down is False


@pytest.mark.skipif(not DAEMON_PATH.exists(), reason="daemon script not present")
def test_t2_transient_stall_never_escalates(monkeypatch) -> None:
    """Discriminating against the above: a stall that clears must NOT page.

    This is the measured case -- /health blocked on 2 of 3 probe rounds and
    answered on the third. If this test ever emits census_stalled_persistent,
    the escalation threshold has been set below real-world contention.
    """
    calls = {"n": 0}

    async def stall_twice_then_recover(path):
        if path == "/api/v1/system-info":
            return HEALTHY_STORAGE
        calls["n"] += 1
        if calls["n"] <= 2:
            raise TimeoutError("transient contention")
        return {"all_models_loaded": []} if path == "/api/v1/health" else {"data": []}

    state, emitted = _run_cycles(monkeypatch, 6, stall_twice_then_recover)

    assert "census_stalled" in emitted
    assert "census_stalled_persistent" not in emitted, emitted
    assert "census_resumed" in emitted
    assert state.stall_polls == 0, "a successful census must reset the escalation clock"
    assert state.census_stalled is False
