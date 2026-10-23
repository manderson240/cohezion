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
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from cohezion.compound.lemonade_recipes import BASE_RECIPES
from cohezion.config.defaults import DEFAULT_TIER0_MODEL


TIER0 = DEFAULT_TIER0_MODEL
RECIPE_CTX = BASE_RECIPES[TIER0]["ctx_size"]

# Thinking-model reply (Gemma-4-E2B, the default tier 0): content is EMPTY and the answer sits
# at the end of reasoning_content. ZEBRA-7731 is a token no caller fallback can invent; the
# last line carries the CLR verdict (first word) and the only 0..1 float (Flume coherence).
THINKING_REASONING = (
    "The user asks for a short judgement. The context is specific and the step is small.\n"
    "Marker ZEBRA-7731 recorded.\n"
    "YES 0.83"
)
# Smallest max_tokens a tier-0 call may send: below this a thinking model never reaches the
# answer (thinking-model-token-budget-gate-trap; the old CLR/Flume budget was 8).
THINKING_SAFE_MAX_TOKENS = 1024


class _FakeLemonade(BaseHTTPRequestHandler):
    calls: list[tuple[str, str, dict]] = []
    thinking: bool = False  # reply as a thinking model: content="" + reasoning_content
    # Full override of the chat reply: {"message": ..., "finish_reason": ..., "usage": ...}.
    override: dict | None = None

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
            if self.override is not None:
                self._reply(
                    {
                        "choices": [
                            {
                                "index": 0,
                                "message": self.override["message"],
                                "finish_reason": self.override["finish_reason"],
                            }
                        ],
                        "usage": self.override["usage"],
                    }
                )
                return
            if self.thinking:
                message = {
                    "role": "assistant",
                    "content": "",
                    "reasoning_content": THINKING_REASONING,
                }
            else:
                # First word YES (CLR verdict), a float (Flume coherence), non-trivial text.
                content = "YES 0.8 - the task is tractable, specific and well within reach."
                message = {"role": "assistant", "content": content}
            self._reply(
                {
                    "choices": [{"index": 0, "message": message, "finish_reason": "stop"}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 14},
                }
            )
        else:  # /load, /unload, anything else: succeed, so a surviving load loop is not masked
            self._reply({"status": "success"})


@pytest.fixture
def fake_lemonade(monkeypatch):
    """Recording fake lemonade; every other outbound INET connect is refused AND recorded."""
    with _fake_lemonade(monkeypatch, expect_gaia_client=True) as handle:
        yield handle


@pytest.fixture
def fake_lemonade_raw(monkeypatch):
    """Same fake, for raw-HTTP callers that never construct a GAIA client."""
    with _fake_lemonade(monkeypatch, expect_gaia_client=False) as handle:
        yield handle


@contextmanager
def _fake_lemonade(monkeypatch, *, expect_gaia_client: bool):
    for var in ("HTTP_PROXY", "HTTPS_PROXY", "ALL_PROXY", "http_proxy", "https_proxy", "all_proxy"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("NO_PROXY", "127.0.0.1,localhost")
    monkeypatch.setenv("no_proxy", "127.0.0.1,localhost")
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    # GAIA's host-broker model lease would connect elsewhere when configured.
    from gaia.daemon import broker_client

    monkeypatch.delenv(broker_client.BROKER_URL_ENV_VAR, raising=False)

    _FakeLemonade.calls = []
    _FakeLemonade.thinking = False
    _FakeLemonade.override = None
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
    if expect_gaia_client:
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


# ── Thinking-model consumption: content="" + reasoning_content must still yield the answer ──
# Default tier 0 is Gemma-4-E2B-it-GGUF, a thinking model. Each tier-0 path must (a) send a
# budget that fits CoT + answer and (b) take the answer from reasoning_content when content is
# empty. A fallback/prior value would not contain ZEBRA-7731 / 0.83 / a 1.0 CLR score.


def _assert_thinking_safe_budget(calls) -> None:
    chats = _tier0_chats(calls)
    assert chats, f"tier 0 never reached the fake: {calls}"
    # GAIA's LemonadeClient sends max_completion_tokens; raw callers send max_tokens.
    budgets = [c[2].get("max_completion_tokens", c[2].get("max_tokens")) for c in chats]
    assert all(b is not None and b >= THINKING_SAFE_MAX_TOKENS for b in budgets), budgets


def test_omni_cascade_tier0_reads_reasoning_content(fake_lemonade):
    base, calls = fake_lemonade
    _FakeLemonade.thinking = True
    from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator

    orch = build_triune_omni_orchestrator(base_url=f"{base}/api/v1")
    tier0, _gate = orch.tiers[0]
    result = asyncio.run(tier0.run("Classify: is 'reboot the router' a networking task?"))
    assert result.error is None, result.error
    assert "ZEBRA-7731" in result.text
    _assert_thinking_safe_budget(calls)
    assert not _load_calls(calls)


def test_flume_world_model_ignores_unclosed_reasoning(fake_lemonade):
    """content="" + bare reasoning_content is the model's THOUGHT, not its answer: Flume must
    keep its baseline rather than parse a number out of an unfinished chain of thought."""
    _base, calls = fake_lemonade
    _FakeLemonade.thinking = True
    import numpy as np

    from cohezion.compound.lemonade_world_model import FlumeWorldModel

    wm = FlumeWorldModel()
    wm.set_task("sort a short list of integers")
    nxt = wm.predict_next_state(np.zeros(12, dtype=np.float32), None)
    assert float(np.mean(nxt)) == pytest.approx(wm._BASELINE, abs=1e-6)
    _assert_thinking_safe_budget(calls)
    assert not _load_calls(calls)


def test_flume_world_model_reads_finished_answer(fake_lemonade):
    """Finished thinking reply: CoT (with a misleading draft number) in reasoning_content, the
    answer in content. The coherence comes from content only."""
    _base, calls = fake_lemonade
    _FakeLemonade.override = _finished_reply("ZEBRA-7731 0.83")
    import numpy as np

    from cohezion.compound.lemonade_world_model import FlumeWorldModel

    wm = FlumeWorldModel()
    wm.set_task("sort a short list of integers")
    nxt = wm.predict_next_state(np.zeros(12, dtype=np.float32), None)
    expected = (2.0 * wm._BASELINE + 0.83) / 3.0
    assert float(np.mean(nxt)) == pytest.approx(expected, abs=1e-6)
    _assert_thinking_safe_budget(calls)
    assert not _load_calls(calls)


def test_clr_quality_gate_unclosed_reasoning_fails_open(fake_lemonade):
    base, calls = fake_lemonade
    _FakeLemonade.thinking = True
    from cohezion.compound.clr_quality_gate import CLRQualityGate

    gate = CLRQualityGate(
        router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1"
    )
    assert gate._gaia_client is not None, "GAIA path not exercised"
    # The verdict-looking last line of bare reasoning is NOT an answer: fail open.
    assert gate.score("Pattern: retry with exponential backoff fixed the flaky upload.") is None
    _assert_thinking_safe_budget(calls)
    assert not _load_calls(calls)


def test_clr_quality_gate_reads_finished_answer(fake_lemonade):
    base, calls = fake_lemonade
    _FakeLemonade.override = _finished_reply("YES")
    from cohezion.compound.clr_quality_gate import CLRQualityGate

    gate = CLRQualityGate(
        router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1"
    )
    assert gate._gaia_client is not None, "GAIA path not exercised"
    # The reasoning drafts NO; the closed answer in content says YES.
    assert gate.score("Pattern: retry with exponential backoff fixed the flaky upload.") == 1.0
    assert len(_tier0_chats(calls)) == 3
    _assert_thinking_safe_budget(calls)
    assert not _load_calls(calls)


def test_clr_quality_gate_httpx_path_reads_finished_answer(fake_lemonade, monkeypatch):
    base, calls = fake_lemonade
    _FakeLemonade.override = _finished_reply("YES")
    from cohezion.compound import clr_quality_gate as clr

    # Build one real GAIA client so the fixture's real-path check holds, then take the httpx
    # fallback (gaia unavailable) for the gate under test.
    clr.CLRQualityGate(router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1")
    monkeypatch.setattr(clr.CLRQualityGate, "_init_gaia_client", lambda self: None)
    gate = clr.CLRQualityGate(
        router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1"
    )
    assert gate.score("Pattern: retry with exponential backoff fixed the flaky upload.") == 1.0
    _assert_thinking_safe_budget(calls)


# ── Truncation: an unfinished chain of thought must never be read as the answer ────────
# Realistic truncated E2B replies: the CoT reaches a tentative "Yes" (and, for Flume, echoes a
# few-shot anchor) and then the budget runs out mid-reconsideration. lemonade sometimes reports
# finish_reason="stop" while truncating, so completion_tokens >= budget must count too.

_TRUNCATED_COT = (
    "The user wants a YES/NO judgement on the pattern.\n"
    "Let me check the context. It mentions exponential backoff.\n"
    "Yes, it mentions X.\n"
    "But wait"
)
_TRUNCATED_FLUME_COT = (
    "Sorting a short list is like the examples.\n"
    "Task: add two small numbers -> 0.97 is the closest anchor.\n"
    "But wait, the list could"
)


def _finished_reply(answer: str) -> dict:
    return {
        "message": {
            "role": "assistant",
            "content": answer,
            "reasoning_content": "Draft: NO 0.05? Re-checking the context... it is fine.",
        },
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 90, "completion_tokens": 120},
    }


def _truncated_reply(reasoning: str, *, finish: str, completion_tokens: int) -> dict:
    return {
        "message": {"role": "assistant", "content": "", "reasoning_content": reasoning},
        "finish_reason": finish,
        "usage": {"prompt_tokens": 90, "completion_tokens": completion_tokens},
    }


def _truncated_inline_reply(reasoning: str, *, finish: str, completion_tokens: int) -> dict:
    # reasoning_format="none": the whole unclosed Gemma channel lands in content.
    return {
        "message": {"role": "assistant", "content": f"<|channel>thought\n{reasoning}"},
        "finish_reason": finish,
        "usage": {"prompt_tokens": 90, "completion_tokens": completion_tokens},
    }


_CLR_TRUNCATIONS = {
    "length": _truncated_reply(_TRUNCATED_COT, finish="length", completion_tokens=1024),
    "stop_at_budget": _truncated_reply(_TRUNCATED_COT, finish="stop", completion_tokens=1024),
    "inline_length": _truncated_inline_reply(
        _TRUNCATED_COT, finish="length", completion_tokens=1024
    ),
}


@pytest.mark.parametrize("shape", sorted(_CLR_TRUNCATIONS))
def test_clr_truncated_reasoning_fails_open(fake_lemonade, shape):
    base, calls = fake_lemonade
    _FakeLemonade.override = _CLR_TRUNCATIONS[shape]
    from cohezion.compound.clr_quality_gate import CLRQualityGate

    gate = CLRQualityGate(
        router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1"
    )
    assert gate._gaia_client is not None, "GAIA path not exercised"
    content = "Pattern: retry with exponential backoff fixed the flaky upload."
    assert gate.score(content) is None, "a truncated CoT was read as a verdict"
    assert gate.passes(content) is True  # fail-open, as before
    assert _tier0_chats(calls)


def test_clr_httpx_path_truncated_reasoning_fails_open(fake_lemonade, monkeypatch):
    base, _calls = fake_lemonade
    _FakeLemonade.override = _CLR_TRUNCATIONS["length"]
    from cohezion.compound import clr_quality_gate as clr

    clr.CLRQualityGate(router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1")
    monkeypatch.setattr(clr.CLRQualityGate, "_init_gaia_client", lambda self: None)
    gate = clr.CLRQualityGate(
        router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1"
    )
    assert gate.score("Pattern: retry with exponential backoff fixed the flaky upload.") is None


_FLUME_TRUNCATIONS = {
    "length": _truncated_reply(_TRUNCATED_FLUME_COT, finish="length", completion_tokens=1024),
    "stop_at_budget": _truncated_reply(
        _TRUNCATED_FLUME_COT, finish="stop", completion_tokens=1024
    ),
    "inline_length": _truncated_inline_reply(
        _TRUNCATED_FLUME_COT, finish="length", completion_tokens=1024
    ),
    "inline_stop_at_budget": _truncated_inline_reply(
        _TRUNCATED_FLUME_COT, finish="stop", completion_tokens=1024
    ),
}


@pytest.mark.parametrize("shape", sorted(_FLUME_TRUNCATIONS))
def test_flume_truncated_reasoning_keeps_baseline(fake_lemonade, shape):
    _base, calls = fake_lemonade
    _FakeLemonade.override = _FLUME_TRUNCATIONS[shape]
    import numpy as np

    from cohezion.compound.lemonade_world_model import FlumeWorldModel

    wm = FlumeWorldModel()
    wm.set_task("sort a short list of integers")
    nxt = wm.predict_next_state(np.zeros(12, dtype=np.float32), None)
    # Not (2*0.7 + 0.97)/3: the echoed few-shot anchor in an unfinished CoT is not an estimate.
    assert float(np.mean(nxt)) == pytest.approx(wm._BASELINE, abs=1e-6)
    assert _tier0_chats(calls)


def test_flume_closed_inline_channel_answer_is_read(fake_lemonade):
    _base, _calls = fake_lemonade
    _FakeLemonade.override = {
        "message": {
            "role": "assistant",
            "content": "<|channel>thought\nLike the 0.97 anchor, maybe lower.<channel|>0.9",
        },
        "finish_reason": "stop",
        "usage": {"prompt_tokens": 90, "completion_tokens": 40},
    }
    import numpy as np

    from cohezion.compound.lemonade_world_model import FlumeWorldModel

    wm = FlumeWorldModel()
    wm.set_task("sort a short list of integers")
    nxt = wm.predict_next_state(np.zeros(12, dtype=np.float32), None)
    assert float(np.mean(nxt)) == pytest.approx((2.0 * wm._BASELINE + 0.9) / 3.0, abs=1e-6)


def test_tri_silicon_tier0_phase_reads_reasoning_content(fake_lemonade_raw, monkeypatch):
    base, calls = fake_lemonade_raw
    _FakeLemonade.thinking = True
    from cohezion.autopoiesis import tri_silicon_engine as tse

    monkeypatch.setattr(tse, "LEMONADE_URL", f"{base}/v1/chat/completions")
    engine = tse.TriSiliconAutopoiesisEngine(cpu_threads=1)
    guidance, _latency = engine.execute_npu_phase(cycle=1)
    # Not either hard-coded fallback sentence: the model's own answer.
    assert "ZEBRA-7731" in guidance
    _assert_thinking_safe_budget(calls)
