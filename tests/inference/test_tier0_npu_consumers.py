"""Tier-0-class NPU consumers request the SHARED tier-0 model with ``"think": false``.

The XDNA2 NPU holds ONE LLM; requesting any other FLM id swaps the slot under lemond's lock
(measured: 32 llama3.2-1b-FLM swaps in 90 min thrashed tier 0 and a Kaggle worker). These
production default paths do tier-0-class work (classify/route/short answers/short lists) and
used to hard-code a different FLM id:

- direct_tier "routine" lane (compound_daemon multi_node_batch / _quarter_execute)
- SystemResourceAgent recommendation (compound_daemon, every iteration)
- telegram bot SIMPLE hints (_handle_chat / _classify_delegation_intent)
- R-Zero challenger (scripts/run_agentic_loop.py --rzero)

Each test drives the REAL payload builder; only the HTTP transport is faked (the recording
fake lemonade for urllib callers, an httpx.AsyncClient stand-in for the telegram bot). Each
path is checked three ways: the default sends tier0_model() with think=false, a
COHEZION_TIER0_MODEL FLM override is honoured (and still gets think=false), and a GGUF
override sends no think key. A non-tier-0 lane on the same builder stays unchanged.
"""

from __future__ import annotations

import asyncio
import json

import pytest

from cohezion.config.defaults import DEFAULT_TIER0_MODEL
from tests.inference.test_tier0_single_ctx_authority import _fake_lemonade, _FakeLemonade


_GGUF = "Gemma-4-E2B-it-GGUF"
_OTHER_FLM = "qwen3.5-4b-FLM"


@pytest.fixture
def fake_raw(monkeypatch):
    with _fake_lemonade(monkeypatch, expect_gaia_client=False) as handle:
        yield handle


def _chat_bodies(calls) -> list[dict]:
    return [c[2] for c in calls if c[0] == "POST" and c[1].endswith("/chat/completions")]


def _assert_tier0_request(calls, model: str) -> None:
    bodies = [b for b in _chat_bodies(calls) if b.get("model") == model]
    assert bodies, f"no {model} chat reached the fake: {calls}"
    for body in bodies:
        if model.endswith("-FLM"):
            assert body.get("think") is False, f"tier-0 FLM request without think=false: {body}"
        else:
            assert "think" not in body, f"GGUF tier-0 request carries a think key: {body}"
    stray = [b["model"] for b in _chat_bodies(calls) if b.get("model", "").endswith("-FLM")]
    assert set(stray) <= {model}, f"a different FLM id was requested (swaps the NPU slot): {stray}"


_OVERRIDES = [None, _OTHER_FLM, _GGUF]


def _expected(override: str | None) -> str:
    return override or DEFAULT_TIER0_MODEL


# ── direct_tier: quarter-on-a-string "routine" lane ──────────────────────────


def _routine(base: str, complexity: str = "routine") -> dict:
    from cohezion.inference.direct_tier import quarter_on_a_string_tier

    tier = quarter_on_a_string_tier(complexity, port=int(base.rsplit(":", 1)[1]))
    tier._base_url = f"{base}/v1/chat/completions"  # 127.0.0.1, the only host the guard allows
    return tier.call("Classify: is 'reboot the router' a networking task?")


@pytest.mark.parametrize("override", _OVERRIDES)
def test_quarter_routine_lane_requests_tier0(fake_raw, monkeypatch, override):
    base, calls = fake_raw
    if override:
        monkeypatch.setenv("COHEZION_TIER0_MODEL", override)
    out = _routine(base)
    assert out["error"] is None, out["error"]
    assert out["model"] == _expected(override)
    _assert_tier0_request(calls, _expected(override))


def test_quarter_unknown_complexity_falls_back_to_tier0(fake_raw):
    base, calls = fake_raw
    _routine(base, complexity="no-such-complexity")
    _assert_tier0_request(calls, DEFAULT_TIER0_MODEL)


def test_quarter_synthesis_lane_unchanged(fake_raw):
    base, calls = fake_raw
    _routine(base, complexity="synthesis")
    bodies = _chat_bodies(calls)
    assert [b["model"] for b in bodies] == ["Gemma-4-E4B-it-GGUF"]
    assert "think" not in bodies[0]


# ── SystemResourceAgent: per-iteration routing recommendation ────────────────


_METRICS = {
    "temp_c": 50.0,
    "memory_percent": 40.0,
    "available_gb": 80.0,
    "psi_avg10": 0.0,
    "pressure_lock": False,
}


@pytest.mark.parametrize("override", _OVERRIDES)
def test_resource_agent_requests_tier0(fake_raw, monkeypatch, override):
    base, calls = fake_raw
    if override:
        monkeypatch.setenv("COHEZION_TIER0_MODEL", override)
    _FakeLemonade.override = {
        "message": {
            "role": "assistant",
            "content": json.dumps(
                {"tier": "npu", "action": "proceed", "reason": "healthy", "pressure_score": 0.05}
            ),
        },
        "finish_reason": "stop",
        "usage": {"completion_tokens": 20},
    }
    from cohezion.inference.system_resource_agent import SystemResourceAgent

    agent = SystemResourceAgent(lemonade_url=f"{base}/v1/chat/completions")
    rec = agent._lemonade_recommendation(_METRICS)
    assert rec is not None and rec.source == "lemonade", "reply not consumed -- vacuous"
    _assert_tier0_request(calls, _expected(override))


# ── R-Zero challenger: short numbered task proposals ─────────────────────────


@pytest.mark.parametrize("override", _OVERRIDES)
def test_rzero_challenger_requests_tier0(fake_raw, monkeypatch, override):
    base, calls = fake_raw
    if override:
        monkeypatch.setenv("COHEZION_TIER0_MODEL", override)
    from cohezion.compound.autonomous_loop.rzero_challenger import ChallengerAgent

    tasks = ChallengerAgent(base_url=base).generate_tasks(2)
    assert len(tasks) == 2
    _assert_tier0_request(calls, _expected(override))


def test_rzero_solver_lane_unchanged(fake_raw):
    base, calls = fake_raw
    from cohezion.compound.autonomous_loop.rzero_challenger import SolverAgent

    SolverAgent(base_url=base).attempt_task("Add a docstring to executor.py", "t1")
    bodies = _chat_bodies(calls)
    assert [b["model"] for b in bodies] == ["Gemma-4-E4B-it-GGUF"]
    assert "think" not in bodies[0]


# ── telegram bot: SIMPLE hint list (short answers + intent classification) ───


class _Resp:
    def __init__(self, status: int, payload: dict) -> None:
        self.status_code = status
        self._payload = payload
        self.text = ""

    def json(self) -> dict:
        return self._payload


class _RouterRefusesFirstHint:
    """httpx.AsyncClient stand-in: the user.cohezion-router alias fails, real ids answer."""

    bodies: list[dict] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc):
        return False

    async def post(self, url, *args, json=None, **kwargs):
        type(self).bodies.append(json or {})
        if (json or {}).get("model") == "user.cohezion-router":
            return _Resp(503, {})
        return _Resp(
            200,
            {
                "model": json["model"],
                "choices": [{"message": {"role": "assistant", "content": "STATUS"}}],
            },
        )


def _telegram_simple(monkeypatch, complexity_name: str = "SIMPLE") -> list[dict]:
    from cohezion.integrations import telegram_bot as tb

    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "8344971611")
    _RouterRefusesFirstHint.bodies = []
    monkeypatch.setattr(tb.httpx, "AsyncClient", lambda *a, **k: _RouterRefusesFirstHint())
    hub = tb.TelegramCommunicationHub()
    text, _telem = asyncio.run(
        hub._chat_omnirouter(
            getattr(tb.QueryComplexity, complexity_name), [{"role": "user", "content": "hi"}]
        )
    )
    assert text == "STATUS", "fell through every hint -- vacuous"
    return _RouterRefusesFirstHint.bodies


@pytest.mark.parametrize("override", _OVERRIDES)
def test_telegram_simple_falls_back_to_tier0(monkeypatch, override):
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    if override:
        monkeypatch.setenv("COHEZION_TIER0_MODEL", override)
    bodies = _telegram_simple(monkeypatch)
    assert [b["model"] for b in bodies] == ["user.cohezion-router", _expected(override)]
    tier0_body = bodies[1]
    if _expected(override).endswith("-FLM"):
        assert tier0_body.get("think") is False, tier0_body
    else:
        assert "think" not in tier0_body, tier0_body


def test_telegram_simple_hints_hold_one_flm_id_and_dedupe(monkeypatch):
    from cohezion.integrations import telegram_bot as tb

    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    simple = tb._resolve_hints(tb.QueryComplexity.SIMPLE)
    assert [h for h in simple if h.endswith("-FLM")] == [DEFAULT_TIER0_MODEL]
    monkeypatch.setenv("COHEZION_TIER0_MODEL", _GGUF)  # already later in the list
    simple = tb._resolve_hints(tb.QueryComplexity.SIMPLE)
    assert simple.count(_GGUF) == 1 and simple[1] == _GGUF


def test_telegram_medium_lane_unchanged(monkeypatch):
    monkeypatch.delenv("COHEZION_TIER0_MODEL", raising=False)
    bodies = _telegram_simple(monkeypatch, "MEDIUM")
    assert [b["model"] for b in bodies] == ["user.cohezion-router", "qwen3-4b-FLM"]
    assert "think" not in bodies[1]
