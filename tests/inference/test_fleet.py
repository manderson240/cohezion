"""Fleet route() orchestrator tests — HTTP and health probes mocked."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from cohezion.inference import RouteResult, route
from cohezion.inference.fleet import _classify_task, _inject_symmetry_axis
from cohezion.inference.registry import FleetRegistry, Lane, Task


def test_classify_task_honors_explicit_hint():
    assert _classify_task("anything", Task.CODE_GEN) == Task.CODE_GEN
    assert _classify_task("anything", "summarization") == Task.SUMMARIZATION


def test_classify_task_detects_code_gen():
    assert _classify_task("write a function that reverses a list", None) == Task.CODE_GEN
    assert _classify_task("```python\ndef foo():\n  pass", None) == Task.CODE_GEN


def test_classify_task_detects_math():
    assert _classify_task("solve x^2 + 3x - 4 = 0", None) == Task.MATH


def test_classify_task_routing_for_short_prompt():
    assert _classify_task("hi there", None) == Task.ROUTING


def test_inject_symmetry_axis_returns_payload_when_bridge_missing():
    payload = {"model": "x", "messages": []}
    # Coherence None should short-circuit
    result = _inject_symmetry_axis(payload, None)
    assert result is payload


@pytest.mark.asyncio
async def test_route_returns_error_when_all_candidates_down():
    """Every local lane is down and we have no cloud for this task."""
    from cohezion.inference import health as health_mod

    # Force fresh probe
    health_mod._LAST_RESULT = None
    health_mod._LAST_CHECK_AT = 0.0

    # All lanes DOWN
    with patch("httpx.get", side_effect=httpx.ConnectError("refused")):
        # And all HTTP dispatches fail too
        with patch(
            "cohezion.inference.fleet._dispatch_openai_compatible",
            AsyncMock(side_effect=Exception("connect refused")),
        ):
            with patch(
                "cohezion.inference.fleet._dispatch_ollama",
                AsyncMock(side_effect=Exception("connect refused")),
            ):
                result = await route("test prompt", task=Task.ROUTING)

    assert result.error is not None
    assert result.text == ""


@pytest.mark.asyncio
async def test_route_dispatches_to_first_healthy_candidate():
    """Simulate NPU up, iGPU down — route() should pick NPU."""
    from cohezion.inference import health as health_mod
    from cohezion.inference.health import LaneHealth, LaneStatus, FleetHealth
    import time

    # Fake health snapshot: only NPU up.
    health_mod._LAST_RESULT = FleetHealth(
        checked_at=time.time(),
        lanes={
            "npu": LaneHealth("npu", "http://localhost:13306", LaneStatus.UP, 10.0),
            "igpu_rocwmma": LaneHealth("igpu_rocwmma", "http://localhost:13307", LaneStatus.DOWN),
            "igpu_unified": LaneHealth("igpu_unified", "http://localhost:13308", LaneStatus.DOWN),
            "cpu": LaneHealth("cpu", "http://localhost:13309", LaneStatus.DOWN),
            "ollama": LaneHealth("ollama", "http://localhost:11434", LaneStatus.DOWN),
            "claude": LaneHealth("claude", "https://api.anthropic.com", LaneStatus.DOWN),
        },
    )
    health_mod._LAST_CHECK_AT = time.time()

    # Returns (text, cost, ttft_ms, tokens_per_sec) per updated dispatch contract.
    dispatch_mock = AsyncMock(return_value=("routed text", 0.0, None, None))
    with patch("cohezion.inference.fleet._dispatch_openai_compatible", dispatch_mock):
        result = await route("short query", task=Task.ROUTING)

    assert result.error is None
    assert result.text == "routed text"
    assert dispatch_mock.await_count >= 1


@pytest.mark.asyncio
async def test_route_records_attempts_list():
    """When first candidate fails, subsequent attempts are logged."""
    from cohezion.inference import health as health_mod
    from cohezion.inference.health import LaneHealth, LaneStatus, FleetHealth
    import time

    health_mod._LAST_RESULT = FleetHealth(
        checked_at=time.time(),
        lanes={
            "npu": LaneHealth("npu", "http://localhost:13306", LaneStatus.UP, 10.0),
            "igpu_rocwmma": LaneHealth(
                "igpu_rocwmma", "http://localhost:13307", LaneStatus.UP, 10.0
            ),
            "igpu_unified": LaneHealth(
                "igpu_unified", "http://localhost:13308", LaneStatus.UP, 10.0
            ),
            "cpu": LaneHealth("cpu", "http://localhost:13309", LaneStatus.UP, 10.0),
            "ollama": LaneHealth("ollama", "http://localhost:11434", LaneStatus.UP, 10.0),
            "claude": LaneHealth("claude", "https://api.anthropic.com", LaneStatus.UP),
        },
    )
    health_mod._LAST_CHECK_AT = time.time()

    # First attempt fails, second succeeds.
    call_count = {"n": 0}

    async def sometimes(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("first lane flaked")
        return ("second lane response", 0.0, None, None)

    # Claude/Gemini CLIs return only (text, cost) — the dispatch wrapper adds the
    # None/None suffix before returning, so keep this mock at 2-tuple shape.
    async def cli_mock(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise Exception("first lane flaked")
        return ("second lane response", 0.0)

    with patch("cohezion.inference.fleet._dispatch_openai_compatible", side_effect=sometimes):
        with patch("cohezion.inference.fleet._dispatch_ollama", side_effect=sometimes):
            with patch("cohezion.inference.fleet._dispatch_headless_cli", side_effect=cli_mock):
                result = await route("explain reasoning", task=Task.REASONING)

    assert result.error is None
    assert result.text == "second lane response"
    assert len(result.attempts) >= 2


def test_route_result_is_dataclass():
    r = RouteResult(text="x", model="m", lane="npu", latency_ms=1.0)
    assert r.cost_usd == 0.0
    assert r.escalated_to_cloud is False
    assert r.attempts == []
