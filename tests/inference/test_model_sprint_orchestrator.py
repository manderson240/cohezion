"""Tests for model_sprint_orchestrator.

These are integration-style tests with all external I/O mocked:
* Lemonade HTTP (:13305 catalog, health, load, unload)
* /proc/meminfo (free RAM)
* EventBus (async handlers)
* kanban_bridge (SurrealDB + vault writes)

The goal is to verify that the orchestrator COMPOSes existing modules
instead of duplicating them: it calls hotswap.ensure_resident under a
FleetLock and publishes events, but does not reimplement eviction math.
"""

from __future__ import annotations

import asyncio
from typing import Any

import pytest

import cohezion.inference.model_sprint_orchestrator as mso
from cohezion.core.event_bus import EventBus
from cohezion.inference import hotswap, oom_guard
from cohezion.inference.fleet_roles import FleetRoster
from cohezion.inference.model_sprint_orchestrator import (
    MODEL_LOAD_LOCK,
    ModelSprintOrchestrator,
    SprintResult,
    run_model_sprint,
)
from cohezion.researcher.daily_researcher import FleetLock


@pytest.fixture(autouse=True)
def _offline_catalog(monkeypatch, catalog):
    """Honour the module docstring: Lemonade HTTP AND /proc/meminfo are mocked.

    ``run_sprint`` calls ``roster.catalog(force=True)``, which bypassed the fixture
    catalog and fetched the LIVE :13305 catalog. Expectations were then taken from
    whatever the fleet happened to serve: green with the router up, red on the CI
    runner where nothing listens (the gating-inference failure on main, 2026-09).
    The pre-load gate's RAM read (``oom_guard.check_ram``) was likewise unmocked:
    the runner had 15.2 GiB free, under the 16 GiB floor.
    """
    monkeypatch.setattr(FleetRoster, "catalog", lambda self, force=False, **_: self._cache)
    monkeypatch.setattr(oom_guard, "check_ram", lambda min_free_gb=20.0: (True, 100.0))
    # pre_load_gate's size heuristic fetches the router catalog itself (oom_guard._get_catalog);
    # with the router up that call succeeded slowly (10-30 s per test) and made the gate's
    # verdict depend on the live fleet instead of the fixture.
    monkeypatch.setattr(oom_guard, "_get_catalog", lambda base_url=None, **_: catalog)
    # Refusal paths persist a kanban item (SurrealDB :8001 + vault) — real I/O the docstring
    # says is mocked; with the services up each refusal cost ~10 s of wall clock.
    monkeypatch.setattr(mso, "persist_item", lambda item: {"surreal": True, "obsidian": True})
    # hotswap's own router reads (health / models, 10 s timeouts each — and the router's
    # health endpoint is known to block) and the gate's per-model recipe fetch. Tests that
    # care override resident_models / _catalog_sizes; these are the hermetic defaults.
    monkeypatch.setattr(hotswap, "resident_models", lambda: [])
    monkeypatch.setattr(
        hotswap, "_catalog_sizes", lambda: {m["id"]: m["size"] for m in catalog if m.get("size")}
    )
    monkeypatch.setattr(oom_guard, "_get_recipe_options", lambda base_url, model_name, **_: {})


@pytest.fixture
def base_url():
    return "http://localhost:13305"


@pytest.fixture
def catalog():
    return [
        {
            "id": "Qwen3.6-35B-A3B-MTP-GGUF",
            "labels": ["mtp", "tool-calling"],
            "size": 22.1,
            "recipe": "llamacpp",
        },
        {"id": "Bonsai-1.7B-gguf", "labels": ["tool-calling"], "size": 0.231, "recipe": "llamacpp"},
        # Exactly ONE npu_route candidate: a second FLM 1B entry ties on the role's name
        # hints and the winner becomes a stable-sort accident (see MS1).
        {"id": "llama3.2-1b-FLM", "labels": [], "size": None, "recipe": "flm"},
    ]


@pytest.fixture
def roster(catalog):
    r = FleetRoster()
    r._cache = catalog
    r._cache_at = 1e12
    r._perf = {}
    return r


@pytest.fixture
def bus():
    return EventBus()


@pytest.fixture
def orchestrator(base_url, roster, bus):
    return ModelSprintOrchestrator(
        base_url=base_url,
        roster=roster,
        bus=bus,
        lock=FleetLock(),
        min_free_gb=16.0,
    )


class TestModelSprintOrchestrator:
    def test_already_resident_short_circuits(self, monkeypatch, orchestrator):
        """MS1: if the selected model is already resident, no load/unload happens.

        The expectation is a literal, not ``roster.select(...)`` (that would be
        circular). Determinism comes from the fixture catalog carrying exactly one
        npu_route candidate — asserted first so a future tying entry fails HERE
        with the cause named, not downstream as a wrong model_id.

        RAM is pinned BELOW the floor: a resident model needs no load, so the RAM
        gate must not run for it. Re-ordering the gate ahead of the residency
        check (the shape that failed on the CI runner) turns this test red.
        """
        expected = "llama3.2-1b-FLM"
        assert orchestrator.roster.select("npu_route") == expected, (
            "fixture catalog must have exactly one npu_route candidate (no name-hint ties)"
        )
        monkeypatch.setattr(oom_guard, "check_ram", lambda min_free_gb=20.0: (False, 5.0))
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [{"model_name": expected, "last_use": 1, "is_busy": False, "loaded": True}],
        )
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {expected: 1.0})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 100.0)

        seen_load: list[tuple[Any, ...]] = []

        def _post(*a, **k):
            seen_load.append(a)
            return 200, "ok"

        monkeypatch.setattr(hotswap, "_post", _post)

        result = asyncio.run(orchestrator.run_sprint(["route"]))
        assert len(result) == 1
        r = result[0]
        assert r.role == "route"
        assert r.model_id == expected
        assert r.ok is True
        assert r.already_resident is True
        assert seen_load == []

    def test_unknown_model_is_refused_not_loaded(self, monkeypatch, orchestrator):
        """MS2: when catalog has no size for a model, pre_load_gate refuses before load."""
        # deepseek-r1-8b-FLM has size None in the fixture catalog -> effective_size unknown
        monkeypatch.setattr(hotswap, "resident_models", lambda: [])
        monkeypatch.setattr(hotswap, "free_gb", lambda: 100.0)

        def _boom(*a, **k):
            raise AssertionError("load should not be called")

        monkeypatch.setattr(hotswap, "_post", _boom)

        # Replace roster with one containing an FLM model with no size
        r = FleetRoster()
        r._cache = [{"id": "deepseek-r1-8b-FLM", "labels": [], "size": None, "recipe": "flm"}]
        r._cache_at = 1e12
        r._perf = {}
        orchestrator.roster = r

        result = asyncio.run(orchestrator.run_sprint(["npu_reason"]))
        assert result[0].ok is False
        assert "unknown" in result[0].reason.lower() or "weight" in result[0].reason.lower()

    def test_eviction_and_load_publishes_events(self, monkeypatch, orchestrator):
        """MS3: a load that evicts models publishes MODEL_LOADING and MODEL_LOADED."""
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"Bonsai-1.7B-gguf": 0.231})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 20.0)
        monkeypatch.setattr(hotswap, "unload", lambda mid, timeout=30.0: True)

        calls: list[tuple[str, dict]] = []

        def _post(path, payload, timeout):
            calls.append((path, payload))
            return 200, "ok"

        monkeypatch.setattr(hotswap, "_post", _post)

        # After load, resident_models returns the new model too
        loaded: list[bool] = []

        def _resident():
            if loaded:
                return [
                    {
                        "model_name": "Bonsai-1.7B-gguf",
                        "last_use": 2,
                        "is_busy": False,
                        "loaded": True,
                    }
                ]
            loaded.append(True)
            return [{"model_name": "old-model", "last_use": 1, "is_busy": False, "loaded": True}]

        monkeypatch.setattr(hotswap, "resident_models", _resident)

        events: list[Any] = []

        class _FakeBus:
            _running = True

            async def publish(self, event):
                events.append((event.type.name, event.payload.get("model_id")))

            def publish_sync(self, event):
                events.append((event.type.name, event.payload.get("model_id")))

        orchestrator.bus = _FakeBus()

        result = asyncio.run(orchestrator.run_sprint(["fast"]))

        assert result[0].ok is True
        assert result[0].model_id == "Bonsai-1.7B-gguf"
        assert any(t == "MODEL_LOADING" for t, _ in events)
        assert any(t == "MODEL_LOADED" for t, _ in events)

    def test_unsafe_load_is_refused_and_publishes_event(self, monkeypatch, orchestrator):
        """MS4: a load that fails the safety gate publishes MODEL_LOAD_REFUSED."""
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"Qwen3.6-35B-A3B-MTP-GGUF": 22.1})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 20.0)  # 20 - 16 = 4 GB budget, need ~39 GB

        def _boom(*a, **k):
            raise AssertionError("load should not be called")

        monkeypatch.setattr(hotswap, "_post", _boom)

        events: list[Any] = []

        class _FakeBus:
            _running = True

            async def publish(self, event):
                events.append(event.payload)

            def publish_sync(self, event):
                events.append(event.payload)

        orchestrator.bus = _FakeBus()

        result = asyncio.run(orchestrator.run_sprint(["interactive"]))

        assert result[0].ok is False
        assert any(p.get("model_id") == "Qwen3.6-35B-A3B-MTP-GGUF" for p in events)

    def test_fleet_lock_acquired_for_load(self, monkeypatch, orchestrator):
        """MS5: the orchestrator acquires the fleet lock before calling load.

        The target must NOT already be resident — a resident model is a no-op that
        (correctly) takes no lock. The model becomes resident after the mocked load.
        """
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"Bonsai-1.7B-gguf": 0.231})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 20.0)
        monkeypatch.setattr(hotswap, "unload", lambda mid, timeout=30.0: True)
        loaded: list[bool] = []

        def _resident():
            if loaded:
                return [
                    {
                        "model_name": "Bonsai-1.7B-gguf",
                        "last_use": 2,
                        "is_busy": False,
                        "loaded": True,
                    }
                ]
            loaded.append(True)
            return [{"model_name": "old-model", "last_use": 1, "is_busy": False, "loaded": True}]

        monkeypatch.setattr(hotswap, "resident_models", _resident)

        lock_key_seen: list[str | None] = [None]
        original_acquire = orchestrator.lock.acquire

        class _WrappedLock:
            def acquire(self, key, timeout=30.0):
                lock_key_seen[0] = key
                return original_acquire(key, timeout)

        orchestrator.lock = _WrappedLock()

        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))

        result = asyncio.run(orchestrator.run_sprint(["fast"]))
        assert result[0].ok is True
        assert lock_key_seen[0] == MODEL_LOAD_LOCK

    def test_roster_change_triggers_sprint(self, monkeypatch, orchestrator):
        """MS6: a new model in the catalog triggers a focused sprint and events."""
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"Bonsai-1.7B-gguf": 0.231})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 20.0)
        monkeypatch.setattr(hotswap, "unload", lambda mid, timeout=30.0: True)
        monkeypatch.setattr(hotswap, "_post", lambda *a, **k: (200, "ok"))
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [
                {"model_name": "Bonsai-1.7B-gguf", "last_use": 1, "is_busy": False, "loaded": True}
            ],
        )

        events: list[Any] = []

        class _FakeBus:
            _running = True

            async def publish(self, event):
                events.append((event.type.name, event.payload.get("new_models")))

            def publish_sync(self, event):
                events.append((event.type.name, event.payload.get("new_models")))

        orchestrator.bus = _FakeBus()

        asyncio.run(
            orchestrator.update_on_roster_change(
                new_models=["Bonsai-1.7B-gguf"],
                removed_models=[],
                current_models=["Bonsai-1.7B-gguf"],
            )
        )

        assert any(
            t == "MODEL_ROSTER_CHANGED" and "Bonsai-1.7B-gguf" in (new or []) for t, new in events
        )

    def test_run_model_sprint_one_shot(self, monkeypatch, base_url):
        """MS7: the convenience one-shot runs without crashing."""
        monkeypatch.setattr(
            hotswap,
            "resident_models",
            lambda: [
                {"model_name": "llama3.2-1b-FLM", "last_use": 1, "is_busy": False, "loaded": True}
            ],
        )
        monkeypatch.setattr(hotswap, "_catalog_sizes", lambda: {"llama3.2-1b-FLM": 1.0})
        monkeypatch.setattr(hotswap, "free_gb", lambda: 100.0)

        result = asyncio.run(run_model_sprint(["route"], base_url=base_url))
        assert isinstance(result, list)
        assert all(isinstance(r, SprintResult) for r in result)
