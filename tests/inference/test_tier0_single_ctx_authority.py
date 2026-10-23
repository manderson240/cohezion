"""Consumption test: the tier-0 ctx has ONE authority (lemonade's saved recipe).

Blocked review 2026-10-23: client-side ctx pins on the tier-0 callers were inert on two
paths and active on CLR, so CLR unloaded/reloaded the model whenever another caller had it
loaded at a different ctx -- reload ping-pong, the thrash this branch removes, moved onto
the iGPU. The fix removes every client-side pin and every client-side /load: the router
auto-loads tier 0 at its saved recipe ctx (BASE_RECIPES, applied by
scripts/apply_lemonade_recipes.py).

This drives the REAL request path of each tier-0 caller against a recording fake lemonade
on 127.0.0.1:<free port> and asserts none of them sends /load or /unload. The fake reports
tier 0 already loaded at the recipe ctx (4096) -- below GAIA's own 32768 floor -- so any
surviving GAIA ensure-loaded / exact-pin logic WOULD fire a reload here.
"""

from __future__ import annotations

import asyncio
import json
import socket
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from cohezion.compound.lemonade_recipes import BASE_RECIPES


TIER0 = "Llama-3.2-1B-Instruct-GGUF"
RECIPE_CTX = BASE_RECIPES[TIER0]["ctx_size"]


class _FakeLemonade(BaseHTTPRequestHandler):
    calls: list[tuple[str, str, dict]] = []

    def log_message(self, *_a) -> None:  # keep pytest output clean
        pass

    def _reply(self, payload: dict) -> None:
        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def _loaded(self) -> dict:
        return {
            "id": TIER0,
            "model_name": TIER0,
            "recipe": "llamacpp",
            "recipe_options": {"ctx_size": RECIPE_CTX},
        }

    def do_GET(self) -> None:
        self.calls.append(("GET", self.path, {}))
        if self.path.endswith("/health"):
            self._reply(
                {"status": "ok", "model_loaded": TIER0, "all_models_loaded": [self._loaded()]}
            )
        elif self.path.endswith("/models"):
            self._reply({"data": [{**self._loaded(), "downloaded": True}]})
        else:
            self._reply({})

    def do_POST(self) -> None:
        length = int(self.headers.get("Content-Length") or 0)
        try:
            body = json.loads(self.rfile.read(length) or b"{}")
        except ValueError:
            body = {}
        self.calls.append(("POST", self.path, body))
        if self.path.endswith("/chat/completions"):
            # First word YES (CLR verdict), a float (Flume coherence), non-trivial text (gate).
            content = "YES 0.8 - the task is tractable, specific and well within reach."
            self._reply(
                {
                    "choices": [{"index": 0, "message": {"role": "assistant", "content": content}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 14},
                }
            )
        else:  # /load, /unload, anything else: succeed, so a surviving load loop is not masked
            self._reply({"status": "success"})


@pytest.fixture
def fake_lemonade(monkeypatch):
    """Recording fake lemonade; every other outbound INET connect is refused AND recorded."""
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    # GAIA's host-broker model lease would connect elsewhere when configured.
    from gaia.daemon import broker_client

    monkeypatch.delenv(broker_client.BROKER_URL_ENV_VAR, raising=False)

    _FakeLemonade.calls = []
    server = ThreadingHTTPServer(("127.0.0.1", 0), _FakeLemonade)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    refused: list[object] = []
    orig_connect = socket.socket.connect

    def _connect(sock, address):
        if sock.family in (socket.AF_INET, socket.AF_INET6) and tuple(address[:2]) != (
            "127.0.0.1",
            port,
        ):
            refused.append(address)
            raise ConnectionRefusedError(f"fake_lemonade guard: refused {address!r}")
        return orig_connect(sock, address)

    def _connect_ex(sock, address):
        try:
            _connect(sock, address)
        except ConnectionRefusedError:
            return 111
        return 0

    monkeypatch.setattr(socket.socket, "connect", _connect)
    monkeypatch.setattr(socket.socket, "connect_ex", _connect_ex)

    # Every caller imports GAIA's LemonadeClient lazily from this module, so wrapping it here
    # reaches all three. The REAL client runs; it is only re-pointed at the fake, and the
    # ctx pin each caller constructs it with is recorded. A pin on a client that never loads
    # is inert today, but it is a second ctx authority the moment any path loads (which is
    # how CLR ping-ponged) -- so a re-added pin fails here even before it causes a reload.
    import gaia.llm.lemonade_client as lc

    base = f"http://127.0.0.1:{port}"
    pins: list[object] = []
    real_client = lc.LemonadeClient

    class _AtFake(real_client):
        def __init__(self, *args, **kwargs):
            kwargs["base_url"] = f"{base}/api/v1"
            super().__init__(*args, **kwargs)
            pins.append(self.ctx_size_override)

    monkeypatch.setattr(lc, "LemonadeClient", _AtFake)
    try:
        yield base, _FakeLemonade.calls
    finally:
        server.shutdown()
        server.server_close()
    assert not refused, f"tier-0 caller reached past the fake lemonade: {refused}"
    assert pins, "no GAIA LemonadeClient was constructed -- the real path was not exercised"
    assert all(p is None for p in pins), f"client-side ctx pin(s) re-added: {pins}"


def _load_calls(calls):
    return [c for c in calls if c[0] == "POST" and c[1].rstrip("/").endswith(("/load", "/unload"))]


def _tier0_chats(calls):
    return [
        c
        for c in calls
        if c[0] == "POST" and c[1].endswith("/chat/completions") and c[2].get("model") == TIER0
    ]


def test_recipe_is_the_bounded_ctx_authority():
    assert RECIPE_CTX == 4096


def test_omni_cascade_tier0_never_loads(fake_lemonade):
    base, calls = fake_lemonade
    from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator

    orch = build_triune_omni_orchestrator(base_url=f"{base}/api/v1")
    result = asyncio.run(orch.run("Classify: is 'reboot the router' a networking task?"))
    assert _tier0_chats(calls), f"tier 0 never reached the fake: {calls}"
    assert result.text, "omni cascade produced no answer"
    assert not _load_calls(calls), f"omni cascade issued load/unload: {_load_calls(calls)}"


def test_flume_world_model_never_loads(fake_lemonade):
    _base, calls = fake_lemonade
    # FlumeWorldModel hardcodes :13305; the fixture's client wrapper re-points it at the fake.
    from cohezion.compound.lemonade_world_model import FlumeWorldModel

    reply = FlumeWorldModel()._chat("Estimate tractability of: sort a list.")
    assert "0.8" in reply
    assert _tier0_chats(calls), f"Flume never reached the fake: {calls}"
    assert not _load_calls(calls), f"FlumeWorldModel issued load/unload: {_load_calls(calls)}"


def test_clr_quality_gate_never_loads(fake_lemonade):
    base, calls = fake_lemonade
    from cohezion.compound.clr_quality_gate import CLRQualityGate

    gate = CLRQualityGate(
        router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1"
    )
    assert gate._gaia_client is not None, "GAIA path not exercised"
    # score() returns None (and passes() fails open) on any error: assert a REAL score.
    score = gate.score("Pattern: retry with exponential backoff fixed the flaky upload.")
    assert score == 1.0
    assert len(_tier0_chats(calls)) == 3
    assert not _load_calls(calls), f"CLRQualityGate issued load/unload: {_load_calls(calls)}"
