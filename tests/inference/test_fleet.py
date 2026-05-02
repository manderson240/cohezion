"""Fleet route() orchestrator tests — HTTP and health probes mocked."""

from __future__ import annotations

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


# ---------------------------------------------------------------------------
# Self-reported confidence (L367 / ARC Lesson 7)
# ---------------------------------------------------------------------------


def test_parse_self_reported_confidence_bracketed_canonical_form():
    from cohezion.inference.fleet import _parse_self_reported_confidence

    conf, cleaned = _parse_self_reported_confidence("The answer is 42. [confidence: 0.85]")
    assert conf == 0.85
    assert cleaned == "The answer is 42."


def test_parse_self_reported_confidence_assignment_form():
    from cohezion.inference.fleet import _parse_self_reported_confidence

    conf, cleaned = _parse_self_reported_confidence("Yes. confidence=0.9")
    assert conf == 0.9
    assert cleaned == "Yes."


def test_parse_self_reported_confidence_percent_form():
    from cohezion.inference.fleet import _parse_self_reported_confidence

    conf, cleaned = _parse_self_reported_confidence("Probably correct. Confidence: 75%")
    assert conf == 0.75
    assert cleaned == "Probably correct."


def test_parse_self_reported_confidence_colon_form():
    from cohezion.inference.fleet import _parse_self_reported_confidence

    conf, cleaned = _parse_self_reported_confidence("Maybe. Confidence: 0.5")
    assert conf == 0.5
    assert cleaned == "Maybe."


def test_parse_self_reported_confidence_returns_none_when_absent():
    from cohezion.inference.fleet import _parse_self_reported_confidence

    conf, cleaned = _parse_self_reported_confidence("No marker here.")
    assert conf is None
    assert cleaned == "No marker here."  # unchanged


def test_parse_self_reported_confidence_ignores_marker_in_body():
    """A mention of 'confidence' mid-body must not trigger extraction —
    only end-of-text markers count."""
    from cohezion.inference.fleet import _parse_self_reported_confidence

    conf, cleaned = _parse_self_reported_confidence(
        "We have high confidence in this result. The answer is 42."
    )
    assert conf is None
    assert cleaned == "We have high confidence in this result. The answer is 42."


def test_parse_self_reported_confidence_clamps_overflow():
    """Miscalibrated models might emit values outside [0,1]; clamp rather
    than reject — a bad calibration is still SOME signal."""
    from cohezion.inference.fleet import _parse_self_reported_confidence

    conf, _ = _parse_self_reported_confidence("x [confidence: 1.5]")
    assert conf == 1.0
    conf, _ = _parse_self_reported_confidence("x confidence=-0.3")
    assert conf == 0.0


def test_parse_self_reported_confidence_handles_empty_text():
    from cohezion.inference.fleet import _parse_self_reported_confidence

    conf, cleaned = _parse_self_reported_confidence("")
    assert conf is None
    assert cleaned == ""


def test_route_result_carries_confidence_default_none():
    r = RouteResult(text="x", model="m", lane="npu", latency_ms=1.0)
    assert r.self_reported_confidence is None


@pytest.mark.asyncio
async def test_extend_claude_escalates_when_confidence_below_threshold():
    """Even if the local text is long enough to pass the length heuristic,
    a self-reported confidence below the threshold must force escalation."""
    from cohezion.inference import extend_claude
    from cohezion.inference.fleet import RouteResult

    # First local attempt: long text + low confidence — should NOT pass
    # Second attempt: same (both fail → falls through to Claude)
    low_conf_result = RouteResult(
        text="This is a long-enough answer but I'm not sure about it at all.",
        model="local-model",
        lane="igpu_rocwmma",
        latency_ms=50.0,
        self_reported_confidence=0.3,  # below default 0.8 threshold
        error=None,
    )
    # Cloud escalation result
    cloud_result = RouteResult(
        text="Confident cloud answer.",
        model="claude-sonnet-4-6",
        lane="cloud_claude",
        latency_ms=400.0,
        self_reported_confidence=None,
        error=None,
    )

    call_results = [low_conf_result, low_conf_result, cloud_result]

    async def sequential_route(*_args, **_kwargs):
        return call_results.pop(0)

    with patch("cohezion.inference.fleet.route", side_effect=sequential_route):
        result = await extend_claude("ambiguous question", claude_model="claude-sonnet-4-6")

    # Both local attempts rejected due to low confidence → escalated to cloud
    assert result.text == "Confident cloud answer."
    assert result.escalated_to_cloud is True


@pytest.mark.asyncio
async def test_extend_claude_accepts_high_confidence_local():
    """High confidence + long text → no escalation."""
    from cohezion.inference import extend_claude
    from cohezion.inference.fleet import RouteResult

    high_conf = RouteResult(
        text="Git is a distributed version control system for tracking code changes.",
        model="local-model",
        lane="igpu_rocwmma",
        latency_ms=50.0,
        self_reported_confidence=0.95,
        error=None,
    )

    with patch("cohezion.inference.fleet.route", return_value=high_conf) as mock_route:
        result = await extend_claude("what is git?", claude_model="claude-sonnet-4-6")

    # Only ONE route() call — the local one. No escalation.
    assert mock_route.await_count == 1
    assert result.self_reported_confidence == 0.95
    assert not result.escalated_to_cloud
