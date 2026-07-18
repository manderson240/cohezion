"""Tests for lemonade_health (lemonade OmniRouter recipe-aware probe).

Pure logic + mocked tests run unconditionally. Live tests skip cleanly if
:13305 is down.
"""

from __future__ import annotations

import json
import socket

import pytest

from cohezion.inference.lemonade_health import (
    CtxHazard,
    LemonadeHealth,
    OrphanProcess,
    RecipeProbe,
    TypeHeadroom,
    _check_ctx_hazards,
    _check_orphans,
    detect_unready_backends,
    is_lemonade_alive,
    probe_lemonade,
)


# ----- Wedge detection (2026-07-18 FLM-wedge fix) --------------------------


def test_detect_unready_backends_does_not_flag_busy():
    # DISCRIMINATING (false-positive guard): "busy" is a NORMAL in-flight state —
    # verified live 2026-07-18 (a loaded FLM read "busy" then cleared). Flagging it
    # would route around every actively-serving backend. Must return [].
    loaded = [
        {"model_name": "Gemma-4-26B-A4B-it-GGUF", "loaded": True, "backend_health": "ready"},
        {"model_name": "deepseek-r1-0528-8b-FLM", "loaded": True, "backend_health": "busy"},
        {"model_name": "kokoro-v1", "loaded": True, "backend_health": "ready"},
    ]
    assert detect_unready_backends(loaded) == []


def test_detect_unready_backends_flags_dead_and_error():
    # DISCRIMINATING: a DEFINITIVELY bad backend must be flagged — backend_alive
    # False (dead process) or a non-transient bad health state (e.g. "error").
    loaded = [
        {"model_name": "ok", "loaded": True, "backend_health": "ready", "backend_alive": True},
        {"model_name": "dead", "loaded": True, "backend_health": "ready", "backend_alive": False},
        {"model_name": "errored", "loaded": True, "backend_health": "error"},
    ]
    assert detect_unready_backends(loaded) == ["dead", "errored"]


def test_detect_unready_backends_ignores_unknown_and_unloaded():
    # no backend_health + no backend_alive -> unknown, NOT flagged
    assert detect_unready_backends([{"model_name": "C", "loaded": True}]) == []
    # not loaded -> not flagged even if health looks bad
    assert (
        detect_unready_backends([{"model_name": "D", "loaded": False, "backend_health": "error"}])
        == []
    )


def test_detect_unready_backends_fails_safe_on_unknown_states():
    # DISCRIMINATING (Finding-1 guard): a denylist must NOT flag states it hasn't
    # enumerated — an allowlist impl (flag anything != {ready,busy,...}) would WRONGLY
    # flag "idle"/"" and route around a healthy lane. These must all be [].
    for unknown in ("idle", "initializing", "", "paused", "queued"):
        assert (
            detect_unready_backends(
                [{"model_name": "m", "loaded": True, "backend_health": unknown}]
            )
            == []
        ), f"unknown state {unknown!r} must fail safe (not flagged)"


def test_lemonade_health_ok_false_when_backend_unready():
    # DISCRIMINATING: a wedged backend must make the snapshot NOT ok — the whole
    # point (last night .ok stayed true while the FLM lane was dead).
    h_wedged = LemonadeHealth(
        checked_at=0.0,
        port=13305,
        version="11.0.0",
        status="ok",
        loaded_count=1,
        unready_backends=["deepseek-r1-0528-8b-FLM"],
    )
    assert h_wedged.ok is False
    assert "unready=deepseek-r1-0528-8b-FLM" in h_wedged.summary
    h_healthy = LemonadeHealth(
        checked_at=0.0,
        port=13305,
        version="11.0.0",
        status="ok",
        loaded_count=1,
    )
    assert h_healthy.ok is True
    assert "unready=none" in h_healthy.summary


def lemonade_reachable(host: str = "localhost", port: int = 13305) -> bool:
    try:
        with socket.create_connection((host, port), timeout=1.0):
            return True
    except OSError:
        return False


# ----- Pure logic (no network) ---------------------------------------------


def test_ctx_hazard_str():
    h = CtxHazard(model="Q", recipe="llamacpp", ctx_size=0, backend_url="http://x", pid=42)
    s = str(h)
    assert "Q" in s and "ctx_size=0" in s and "pid=42" in s


def test_orphan_str():
    o = OrphanProcess(model="X", pid=0, backend_url="http://x")
    s = str(o)
    assert "X" in s and "pid=0" in s


def test_type_headroom_free_saturated():
    h = TypeHeadroom(type="llm", loaded=6, max_=6)
    assert h.free == 0
    assert h.saturated
    s = str(h)
    assert "SATURATED" in s

    h2 = TypeHeadroom(type="llm", loaded=3, max_=6)
    assert h2.free == 3
    assert not h2.saturated
    assert "ok" in str(h2)


def test_recipe_probe_ok_short_circuit():
    p = RecipeProbe(recipe="kokoro", ok=True, latency_ms=10.0, detail="HTTP 200")
    assert str(p).startswith("kokoro=ok")
    p2 = RecipeProbe(recipe="kokoro", ok=False, latency_ms=999.0, detail="HTTP 503")
    assert "DOWN" in str(p2)


def test_check_ctx_hazards_finds_zero():
    loaded = [
        {
            "model_name": "X",
            "recipe": "llamacpp",
            "recipe_options": {"ctx_size": 0},
            "backend_url": "u",
            "pid": 1,
        },
        {
            "model_name": "Y",
            "recipe": "llamacpp",
            "recipe_options": {"ctx_size": 16384},
            "backend_url": "u",
            "pid": 2,
        },
    ]
    import asyncio

    hazards = asyncio.run(_check_ctx_hazards(loaded))
    assert len(hazards) == 1
    assert hazards[0].model == "X"
    assert hazards[0].ctx_size == 0


def test_check_ctx_hazards_ignores_non_llm_recipes():
    loaded = [
        {
            "model_name": "k",
            "recipe": "kokoro",
            "recipe_options": {"ctx_size": 0},
            "backend_url": "u",
            "pid": 1,
        },
        {
            "model_name": "s",
            "recipe": "sd-cpp",
            "recipe_options": {"ctx_size": 0},
            "backend_url": "u",
            "pid": 2,
        },
        {
            "model_name": "w",
            "recipe": "whispercpp",
            "recipe_options": {"ctx_size": 0},
            "backend_url": "u",
            "pid": 3,
        },
    ]
    import asyncio

    hazards = asyncio.run(_check_ctx_hazards(loaded))
    assert hazards == []


def test_check_ctx_hazards_handles_missing_ctx():
    loaded = [
        {
            "model_name": "X",
            "recipe": "llamacpp",
            "recipe_options": {},
            "backend_url": "u",
            "pid": 1,
        },
    ]
    import asyncio

    hazards = asyncio.run(_check_ctx_hazards(loaded))
    # missing ctx_size is not a hazard (not zero, just absent)
    assert hazards == []


def test_check_orphans_finds_zeros_and_dups():
    loaded = [
        {"model_name": "A", "pid": 100, "backend_url": "u1"},
        {"model_name": "B", "pid": 0, "backend_url": "u2"},  # zombie
        {"model_name": "C", "pid": -1, "backend_url": "u3"},  # also zombie
        {"model_name": "D", "pid": 100, "backend_url": "u4"},  # dup of A
    ]
    import asyncio

    orphans = asyncio.run(_check_orphans(loaded))
    names = [o.model for o in orphans]
    assert any("B" in n for n in names)
    assert any("C" in n for n in names)
    assert any("D" in n and "dup" in n for n in names)


def test_health_summary_includes_counts():
    h = LemonadeHealth(
        checked_at=0.0,
        port=13305,
        version="10.6.0",
        status="ok",
        loaded_count=3,
        recipe_probes=[
            RecipeProbe(recipe="kokoro", ok=True, latency_ms=10.0),
            RecipeProbe(recipe="sd-cpp", ok=False, latency_ms=999.0),
        ],
        headroom=[TypeHeadroom(type="llm", loaded=2, max_=6)],
        ctx_hazards=[CtxHazard("M", "llamacpp", 0, "u", 1)],
        warnings=["ctx_size<=0 on M"],
    )
    s = h.summary
    assert "v10.6.0" in s
    assert "loaded=3" in s
    assert "recipes_up=kokoro" in s
    assert "recipes_down=sd-cpp" in s
    assert "ctx_hazards=1" in s


def test_health_ok_requires_no_hazards():
    h_ok = LemonadeHealth(
        checked_at=0.0,
        port=13305,
        version="10.6.0",
        status="ok",
        loaded_count=1,
        recipe_probes=[],
        headroom=[],
    )
    assert h_ok.ok

    h_bad = LemonadeHealth(
        checked_at=0.0,
        port=13305,
        version="10.6.0",
        status="ok",
        loaded_count=1,
        recipe_probes=[],
        headroom=[],
        ctx_hazards=[CtxHazard("M", "llamacpp", 0, "u", 1)],
    )
    assert not h_bad.ok
    assert h_bad.has_ctx_hazards


def test_health_recipes_up_down():
    h = LemonadeHealth(
        checked_at=0.0,
        port=13305,
        version="10.6.0",
        status="degraded",
        loaded_count=0,
        recipe_probes=[
            RecipeProbe(recipe="kokoro", ok=True, latency_ms=10.0),
            RecipeProbe(recipe="llamacpp", ok=False, latency_ms=999.0),
        ],
        headroom=[],
    )
    assert h.recipes_up == ["kokoro"]
    assert h.recipes_down == ["llamacpp"]


# ----- Mocked test (always runs) -------------------------------------------


@pytest.mark.asyncio
async def test_probe_lemonade_mocked_all_ok(monkeypatch):
    import httpx

    health_payload = {
        "version": "10.6.0",
        "status": "ok",
        "all_models_loaded": [
            {
                "model_name": "M1",
                "recipe": "llamacpp",
                "type": "llm",
                "recipe_options": {"ctx_size": 16384},
                "backend_url": "http://x",
                "pid": 100,
            },
            {
                "model_name": "M2",
                "recipe": "kokoro",
                "type": "tts",
                "recipe_options": {},
                "backend_url": "http://y",
                "pid": 200,
            },
        ],
        "max_models": {"llm": 6, "tts": 6},
    }
    voices_payload = {"voices": ["a", "b"]}

    class _Resp:
        def __init__(self, status, payload):
            self.status_code = status
            self._payload = payload

        def json(self):
            return self._payload

        @property
        def text(self):
            return json.dumps(self._payload)

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def get(self, url, **kw):
            if url.endswith("/api/v1/health"):
                return _Resp(200, health_payload)
            if url.endswith("/v1/audio/voices"):
                return _Resp(200, voices_payload)
            if url.endswith("/v1/models"):
                return _Resp(200, {"data": []})
            if url.endswith("/v1/images/generations"):
                return _Resp(405, {"error": "POST required"})
            if url.endswith("/v1/audio/transcriptions"):
                return _Resp(400, {"error": "multipart required"})
            return _Resp(404, {})

        async def request(self, method, url, **kw):
            return await self.get(url, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    h = await probe_lemonade(port=13305)
    assert h.ok
    assert h.version == "10.6.0"
    assert h.loaded_count == 2
    assert h.recipes_up == ["llamacpp", "kokoro", "sd-cpp", "whispercpp"]
    assert h.headroom[0].type in ("llm", "tts")


@pytest.mark.asyncio
async def test_probe_lemonade_mocked_ctx_hazard(monkeypatch):
    import httpx

    health_payload = {
        "version": "10.6.0",
        "status": "ok",
        "all_models_loaded": [
            {
                "model_name": "Q-HAZARD",
                "recipe": "llamacpp",
                "type": "llm",
                "recipe_options": {"ctx_size": 0},
                "backend_url": "http://x",
                "pid": 1,
            },
        ],
        "max_models": {"llm": 6},
    }

    class _Resp:
        def __init__(self, status, payload):
            self.status_code = status
            self._payload = payload

        def json(self):
            return self._payload

        @property
        def text(self):
            return json.dumps(self._payload)

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def get(self, url, **kw):
            if url.endswith("/api/v1/health"):
                return _Resp(200, health_payload)
            return _Resp(400, {})  # recipes alive

        async def request(self, method, url, **kw):
            return await self.get(url, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    h = await probe_lemonade(port=13305)
    assert not h.ok
    assert h.has_ctx_hazards
    assert h.ctx_hazards[0].model == "Q-HAZARD"
    assert any("ctx_size" in w for w in h.warnings)


@pytest.mark.asyncio
async def test_probe_lemonade_mocked_omni_down(monkeypatch):
    import httpx

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def get(self, url, **kw):
            raise httpx.ConnectError("connection refused", request=httpx.Request("GET", url))

        async def request(self, method, url, **kw):
            return await self.get(url, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    h = await probe_lemonade(port=13305)
    assert h.status == "down"
    assert not h.ok
    assert any("unreachable" in e for e in h.errors)


@pytest.mark.asyncio
async def test_probe_lemonade_mocked_5xx_means_dead(monkeypatch):
    """A recipe returning HTTP 500 must be marked dead (not alive)."""
    import httpx

    class _Resp:
        def __init__(self, status, payload):
            self.status_code = status
            self._payload = payload

        def json(self):
            return self._payload

        @property
        def text(self):
            return json.dumps(self._payload)

    class _Client:
        def __init__(self, *a, **k):
            pass

        async def __aenter__(self):
            return self

        async def __aexit__(self, *e):
            return False

        async def get(self, url, **kw):
            if url.endswith("/api/v1/health"):
                return _Resp(
                    200,
                    {
                        "version": "10.6.0",
                        "status": "ok",
                        "all_models_loaded": [],
                        "max_models": {},
                    },
                )
            if url.endswith("/v1/audio/voices"):
                return _Resp(503, {"error": "down"})
            return _Resp(400, {})

        async def request(self, method, url, **kw):
            return await self.get(url, **kw)

    monkeypatch.setattr(httpx, "AsyncClient", _Client)
    h = await probe_lemonade(port=13305, probe_recipes=["kokoro", "llamacpp"])
    assert h.recipes_down == ["kokoro"]
    assert h.recipes_up == ["llamacpp"]


# ----- Live tests (skipped if :13305 down) ---------------------------------


LIVE = pytest.mark.skipif(
    not lemonade_reachable(),
    reason="lemonade OmniRouter not reachable on :13305",
)


@LIVE
@pytest.mark.asyncio
async def test_probe_lemonade_live():
    h = await probe_lemonade(port=13305)
    assert h.status == "ok", f"omni status not ok: {h.errors}"
    assert h.version != "?"
    assert h.latency_ms < 5000
    # Live: should have at least kokoro (per the live catalog snapshot)
    assert "kokoro" in h.recipes_up or "kokoro" in h.recipes_down  # depends on what's loaded
    # No live ctx_size=0 hazards on a healthy box
    assert h.ctx_hazards == [], f"unexpected live ctx hazards: {[str(x) for x in h.ctx_hazards]}"


@LIVE
@pytest.mark.asyncio
async def test_is_lemonade_alive_live():
    assert await is_lemonade_alive(port=13305)


@LIVE
@pytest.mark.asyncio
async def test_is_lemonade_alive_live_dead_port():
    assert not await is_lemonade_alive(port=19999)
