"""Consumption test: EVERY tier-0 request to an FLM model carries top-level ``"think": false``.

FastFlowLM's think flag is STICKY on the loaded NPU model: a request that omits it inherits
whatever the last caller set. The calibrated gauntlet measured gemma4-it-e2b-FLM at 1.000 with
think=false and 0.949 with think=true, so one caller that omits the flag silently degrades
every other tier-0 caller. One chokepoint (config.defaults.tier0_request_extras) feeds every
production tier-0 payload builder; this file drives each builder's REAL request path against
the recording fake lemonade (only the HTTP transport is faked) and asserts on the wire body.

Negative halves: a non-FLM tier-0 override sends NO think key, and non-tier-0 lanes (the
reasoning orchestrator's FLM tier, the E4B judge) are unchanged.
"""

from __future__ import annotations

import asyncio
import sys

import pytest

from cohezion.config.defaults import DEFAULT_TIER0_MODEL, tier0_request_extras
from tests.inference.test_tier0_single_ctx_authority import _fake_lemonade


_GGUF = "Gemma-4-E2B-it-GGUF"


@pytest.fixture
def fake_gaia(monkeypatch):
    with _fake_lemonade(monkeypatch, expect_gaia_client=True) as handle:
        yield handle


@pytest.fixture
def fake_raw(monkeypatch):
    with _fake_lemonade(monkeypatch, expect_gaia_client=False) as handle:
        yield handle


def _chats(calls, model: str) -> list[dict]:
    return [
        c[2]
        for c in calls
        if c[0] == "POST" and c[1].endswith("/chat/completions") and c[2].get("model") == model
    ]


def _assert_think_false(calls, model: str = DEFAULT_TIER0_MODEL) -> None:
    bodies = _chats(calls, model)
    assert bodies, f"no {model} chat reached the fake -- test is vacuous: {calls}"
    for body in bodies:
        assert body.get("think") is False, f"tier-0 FLM request without think=false: {body}"


def _assert_no_think(calls, model: str) -> None:
    bodies = _chats(calls, model)
    assert bodies, f"no {model} chat reached the fake -- test is vacuous: {calls}"
    for body in bodies:
        assert "think" not in body, f"{model} request carries a think key: {body}"


# ── the chokepoint ────────────────────────────────────────────────────────────


def test_default_tier0_is_an_flm_id():
    assert DEFAULT_TIER0_MODEL == "gemma4-it-e2b-FLM"
    assert tier0_request_extras(DEFAULT_TIER0_MODEL) == {"think": False}


def test_non_flm_id_gets_no_extras():
    assert tier0_request_extras(_GGUF) == {}


# ── each production tier-0 path, real payload builder, fake transport ────────


def _omni_tier0(base: str):
    from cohezion.inference.triune_orchestrator import build_triune_omni_orchestrator

    orch = build_triune_omni_orchestrator(base_url=f"{base}/api/v1")
    tier0, _gate = orch.tiers[0]
    result = asyncio.run(tier0.run("Classify: is 'reboot the router' a networking task?"))
    assert result.error is None, result.error


def _flume(_base: str):
    from cohezion.compound.lemonade_world_model import FlumeWorldModel

    FlumeWorldModel()._chat("Estimate tractability of: sort a list.")


def _clr_gaia(base: str):
    from cohezion.compound.clr_quality_gate import CLRQualityGate

    gate = CLRQualityGate(
        router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1"
    )
    assert gate._gaia_client is not None, "GAIA path not exercised"
    assert gate.score("Pattern: retry with backoff fixed the flaky upload.") == 1.0


_GAIA_PATHS = {
    "omni_cascade_tier0": _omni_tier0,
    "flume_world_model": _flume,
    "clr_gaia": _clr_gaia,
}


@pytest.mark.parametrize("path", sorted(_GAIA_PATHS))
def test_gaia_paths_send_think_false(path, fake_gaia):
    base, calls = fake_gaia
    _GAIA_PATHS[path](base)
    _assert_think_false(calls)


@pytest.mark.parametrize("path", sorted(_GAIA_PATHS))
def test_gaia_paths_send_no_think_for_gguf_override(path, fake_gaia, monkeypatch):
    base, calls = fake_gaia
    monkeypatch.setenv("COHEZION_TIER0_MODEL", _GGUF)
    _GAIA_PATHS[path](base)
    _assert_no_think(calls, _GGUF)


def test_cascade_tier0_without_gaia_sdk_sends_think_false(fake_raw, monkeypatch):
    """amd-gaia absent -> build_gaia_llm_tier's stdlib _LocalRouterClient builds the payload."""
    base, calls = fake_raw
    monkeypatch.setitem(sys.modules, "gaia.llm.lemonade_client", None)
    _omni_tier0(base)
    _assert_think_false(calls)


def test_clr_httpx_path_sends_think_false(fake_gaia, monkeypatch):
    base, calls = fake_gaia
    from cohezion.compound import clr_quality_gate as clr

    # One real GAIA client keeps the fixture's real-path check honest; then take httpx.
    clr.CLRQualityGate(router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1")
    monkeypatch.setattr(clr.CLRQualityGate, "_init_gaia_client", lambda self: None)
    gate = clr.CLRQualityGate(
        router_url=f"{base}/v1/chat/completions", gaia_router_url=f"{base}/api/v1"
    )
    calls.clear()
    assert gate.score("Pattern: retry with backoff fixed the flaky upload.") == 1.0
    _assert_think_false(calls)


def test_tri_silicon_npu_phase_sends_think_false(fake_raw, monkeypatch):
    base, calls = fake_raw
    from cohezion.autopoiesis import tri_silicon_engine as tse

    monkeypatch.setattr(tse, "LEMONADE_URL", f"{base}/v1/chat/completions")
    text, _ms = tse.TriSiliconAutopoiesisEngine(cpu_threads=1).execute_npu_phase(1)
    assert "YES" in text, "fell back instead of reading the fake's reply"
    _assert_think_false(calls)


def test_tri_silicon_gguf_override_sends_no_think(fake_raw, monkeypatch):
    base, calls = fake_raw
    monkeypatch.setenv("COHEZION_TIER0_MODEL", _GGUF)
    from cohezion.autopoiesis import tri_silicon_engine as tse

    monkeypatch.setattr(tse, "LEMONADE_URL", f"{base}/v1/chat/completions")
    tse.TriSiliconAutopoiesisEngine(cpu_threads=1).execute_npu_phase(1)
    _assert_no_think(calls, _GGUF)


class _Task:
    id = "t1"
    description = "Classify this log line"
    category = "general"
    verification = "one word"


def test_autonomous_loop_npu_node_sends_think_false_and_judge_unchanged(fake_raw, monkeypatch):
    base, calls = fake_raw
    from cohezion.compound.autonomous_loop import local_executor as le

    monkeypatch.setattr(le, "_classify_node", lambda _d: "npu")
    result = le.LocalImprovementExecutor(base_url=base).execute_task(_Task(), "/tmp")
    assert result["model"] == DEFAULT_TIER0_MODEL
    _assert_think_false(calls)
    _assert_no_think(calls, le._JUDGE_MODEL)  # the E4B QA lane is not tier 0


def test_telegram_ask_local_tier0_sends_think_false(fake_raw):
    base, calls = fake_raw
    from cohezion.compound.telegram_hub import TelegramHub

    hub = TelegramHub()
    hub._lemonade_url = base
    reply = asyncio.run(hub.ask_local("ping", model=DEFAULT_TIER0_MODEL))
    assert reply, "ask_local returned nothing -- request never succeeded"
    _assert_think_false(calls)


def test_telegram_non_tier0_flm_sends_no_think(fake_raw):
    base, calls = fake_raw
    from cohezion.compound.telegram_hub import TelegramHub

    hub = TelegramHub()
    hub._lemonade_url = base
    asyncio.run(hub.ask_local("ping", model="llama3.2-1b-FLM"))
    _assert_no_think(calls, "llama3.2-1b-FLM")


def test_reasoning_orchestrator_flm_lane_sends_no_think(fake_gaia):
    """A non-tier-0 FLM lane keeps its own behaviour: the gate is the tier-0 id, not -FLM."""
    base, calls = fake_gaia
    from cohezion.inference.triune_orchestrator import build_reasoning_orchestrator

    orch = build_reasoning_orchestrator(omni_port=int(base.rsplit(":", 1)[1]))
    tier, _gate = orch.tiers[0]
    asyncio.run(tier.run("Reason: 2 + 2?"))
    _assert_no_think(calls, "qwen3.6-moe-35b-a3b-FLM")
