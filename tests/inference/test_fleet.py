"""Fleet route() orchestrator tests — HTTP and health probes mocked."""

from __future__ import annotations

import subprocess
from unittest.mock import AsyncMock, patch

import httpx
import pytest

from cohezion.inference import RouteResult, route
from cohezion.inference.fleet import _classify_task, _inject_symmetry_axis
from cohezion.inference.registry import Task


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

    # All lanes DOWN. Use httpx.ConnectError (caught by the narrowed
    # except clause in fleet.route) rather than bare Exception, which
    # would propagate out of the dispatch and fail the test post-L359.
    # Also patch the headless CLI dispatch so the gemini/claude fallback
    # tier doesn't shell out to real subprocesses.
    cli_err = subprocess.CalledProcessError(1, ["gemini"], stderr="down")
    with (
        patch("httpx.get", side_effect=httpx.ConnectError("refused")),
        patch(
            "cohezion.inference.fleet._dispatch_openai_compatible",
            AsyncMock(side_effect=httpx.ConnectError("connect refused")),
        ),
        patch(
            "cohezion.inference.fleet._dispatch_ollama",
            AsyncMock(side_effect=httpx.ConnectError("connect refused")),
        ),
        patch(
            "cohezion.inference.fleet._dispatch_headless_cli",
            AsyncMock(side_effect=cli_err),
        ),
    ):
        result = await route("test prompt", task=Task.ROUTING)

    assert result.error is not None
    assert result.text == ""


@pytest.mark.asyncio
async def test_route_dispatches_to_first_healthy_candidate():
    """Simulate NPU up, iGPU down — route() should pick NPU."""
    import time

    from cohezion.inference import health as health_mod
    from cohezion.inference.health import FleetHealth, LaneHealth, LaneStatus

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
    import time

    from cohezion.inference import health as health_mod
    from cohezion.inference.health import FleetHealth, LaneHealth, LaneStatus

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

    # First attempt fails, second succeeds. Raise httpx.ConnectError so the
    # narrowed except clause in fleet.route catches it and advances to the
    # next candidate (bare Exception would propagate and fail the test
    # post-L359 narrowing).
    call_count = {"n": 0}

    async def sometimes(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise httpx.ConnectError("first lane flaked")
        return ("second lane response", 0.0, None, None)

    # Claude/Gemini CLIs return only (text, cost) — the dispatch wrapper adds the
    # None/None suffix before returning, so keep this mock at 2-tuple shape.
    async def cli_mock(*args, **kwargs):
        call_count["n"] += 1
        if call_count["n"] == 1:
            raise httpx.ConnectError("first lane flaked")
        return ("second lane response", 0.0)

    with (
        patch("cohezion.inference.fleet._dispatch_openai_compatible", side_effect=sometimes),
        patch("cohezion.inference.fleet._dispatch_ollama", side_effect=sometimes),
        patch("cohezion.inference.fleet._dispatch_headless_cli", side_effect=cli_mock),
    ):
        result = await route("explain reasoning", task=Task.REASONING)

    assert result.error is None
    assert result.text == "second lane response"
    assert len(result.attempts) >= 2


def test_route_result_is_dataclass():
    r = RouteResult(text="x", model="m", lane="npu", latency_ms=1.0)
    assert r.cost_usd == 0.0
    assert r.escalated_to_cloud is False
    assert r.attempts == []


@pytest.mark.asyncio
async def test_extend_claude_rejects_unknown_model_before_local_loop():
    """Regression: an invalid claude_model must short-circuit BEFORE dispatching
    any local route() calls — otherwise a typo wastes `max_local_attempts`
    worth of NPU cycles. See adversarial review Edge-case #2 (ROADMAP P1)."""
    from cohezion.inference import extend_claude

    route_mock = AsyncMock()
    with patch("cohezion.inference.fleet.route", route_mock):
        result = await extend_claude("test", claude_model="this-model-does-not-exist")

    assert route_mock.await_count == 0, (
        "route() must not be called when claude_model is invalid; "
        f"was called {route_mock.await_count} times"
    )
    assert result.error is not None
    assert "this-model-does-not-exist" in result.error


@pytest.mark.asyncio
async def test_route_warns_on_small_max_tokens_for_reasoning_mode(caplog):
    """route() must warn when dispatching to a reasoning-mode model with
    max_tokens < 128. Gemma-4 FLM on NPU eats the entire budget on its
    <thinking> block, returning empty visible text. Silent empties make
    debugging painful — a pre-dispatch warning surfaces the cause.

    See docs/dogfood/drift-report-2026-04-18.md P2 #1.
    """
    import logging
    import time

    from cohezion.inference import health as health_mod
    from cohezion.inference.health import FleetHealth, LaneHealth, LaneStatus

    # Only NPU up; route should pick the Gemma-4-E2B (reasoning_mode=True).
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

    dispatch_mock = AsyncMock(return_value=("pong", 0.0, None, None))

    caplog.set_level(logging.WARNING, logger="cohezion.inference.fleet")
    with patch("cohezion.inference.fleet._dispatch_openai_compatible", dispatch_mock):
        result = await route("ping", task=Task.ROUTING, max_tokens=16)

    assert result.error is None
    warnings = [r for r in caplog.records if r.levelno == logging.WARNING]
    assert any(
        "reasoning-mode" in r.getMessage() and "max_tokens=16" in r.getMessage() for r in warnings
    ), f"expected reasoning-mode warning; got {[r.getMessage() for r in warnings]}"


@pytest.mark.asyncio
async def test_route_does_not_warn_on_ample_max_tokens(caplog):
    """Inverse of the above: max_tokens >= 128 suppresses the reasoning-mode warning."""
    import logging
    import time

    from cohezion.inference import health as health_mod
    from cohezion.inference.health import FleetHealth, LaneHealth, LaneStatus

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

    dispatch_mock = AsyncMock(return_value=("pong", 0.0, None, None))
    caplog.set_level(logging.WARNING, logger="cohezion.inference.fleet")
    with patch("cohezion.inference.fleet._dispatch_openai_compatible", dispatch_mock):
        await route("ping", task=Task.ROUTING, max_tokens=256)

    assert not any("reasoning-mode" in r.getMessage() for r in caplog.records), (
        "no reasoning-mode warning expected when max_tokens >= 128"
    )
