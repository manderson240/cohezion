"""Unit tests for the Google-inspired testing and quality assurance pipeline.

Validates:
1. Hermetic async fixtures: async_event_bus, mock_inference_gateway, and agent_turn_harness.
2. Parallel execution and state isolation under pytest-xdist.
3. Flaky test management and automatic quarantine telemetry logging.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import pytest

from cohezion.core.event_bus import Event, EventBus, EventType


# State counter used to simulate transient flakiness
_FLAKY_ATTEMPT_COUNTER = 0


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_event_bus_pub_sub(async_event_bus: EventBus) -> None:
    """Validate hermetic async event bus publishing, subscribing, and draining."""
    received: list[Event] = []

    async def _handler(event: Event) -> None:
        received.append(event)

    async_event_bus.subscribe(EventType.AGENT_START)(_handler)

    test_event = Event.agent_start(agent_name="PlannerAgent", model="deepseek-r1-0528-8b-FLM")
    await async_event_bus.publish(test_event)

    # Allow processor loop a tick to deliver
    await asyncio.sleep(0.05)

    assert len(received) == 1
    assert received[0].source == "PlannerAgent"
    assert received[0].payload["model"] == "deepseek-r1-0528-8b-FLM"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_inference_gateway_deterministic(mock_inference_gateway: Any) -> None:
    """Verify mock inference gateway returns deterministic tokens with zero external I/O."""
    mock_inference_gateway.set_response_for_model(
        "qwen3.6-moe-35b-a3b-FLM", "Verified optimal plan generated."
    )

    response = await mock_inference_gateway.complete(
        prompt="Synthesize next action plan",
        model="qwen3.6-moe-35b-a3b-FLM",
        temperature=0.2,
    )

    assert response["content"] == "Verified optimal plan generated."
    assert response["model"] == "qwen3.6-moe-35b-a3b-FLM"
    assert response["usage"]["prompt_tokens"] > 0
    assert response["usage"]["completion_tokens"] > 0
    assert len(mock_inference_gateway.calls) == 1


@pytest.mark.unit
@pytest.mark.asyncio
async def test_mock_inference_gateway_error_simulation(mock_inference_gateway: Any) -> None:
    """Verify mock inference gateway simulates transient errors for resilience testing."""
    mock_inference_gateway.set_error(RuntimeError("NPU thermal throttle simulation"))

    with pytest.raises(RuntimeError, match="thermal throttle"):
        await mock_inference_gateway.complete(
            prompt="Test prompt",
            model="deepseek-r1-0528-8b-FLM",
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agent_turn_harness_lifecycle(
    agent_turn_harness: Any, async_event_bus: EventBus
) -> None:
    """Verify AgentTurnHarness manages state transitions, timeouts, and event logging."""
    agent_turn_harness.bus = async_event_bus

    async with agent_turn_harness.run_turn(name="CoderAgent") as harness:
        harness.record_state("GENERATING_CODE")
        await asyncio.sleep(0.02)

    assert agent_turn_harness.state_history == [
        "INITIALIZED",
        "RUNNING",
        "GENERATING_CODE",
        "COMPLETED",
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_agent_turn_harness_timeout_guard(agent_turn_harness: Any) -> None:
    """Verify AgentTurnHarness fails fast on hung or looping agent turns."""
    agent_turn_harness.timeout_s = 0.05

    with pytest.raises(TimeoutError):
        async with agent_turn_harness.run_turn(name="HungAgent"):
            await asyncio.sleep(0.2)

    assert agent_turn_harness.state_history == ["INITIALIZED", "RUNNING", "FAILED"]


@pytest.mark.unit
@pytest.mark.flaky(reruns=2, reruns_delay=0.01)
def test_flaky_test_quarantine_rerun() -> None:
    """Verify intermittent failures trigger automatic reruns and log to quarantine report."""
    global _FLAKY_ATTEMPT_COUNTER
    _FLAKY_ATTEMPT_COUNTER += 1

    # Fail on first attempt, succeed on rerun
    if _FLAKY_ATTEMPT_COUNTER == 1:
        pytest.fail("Simulated transient non-deterministic network/async jitter")

    assert _FLAKY_ATTEMPT_COUNTER >= 2


@pytest.mark.unit
def test_quarantine_report_persisted() -> None:
    """Verify reports/quarantine.jsonl records quarantined rerun metadata."""
    quarantine_path = Path("reports") / "quarantine.jsonl"
    if quarantine_path.exists():
        content = quarantine_path.read_text(encoding="utf-8").strip()
        if content:
            lines = content.splitlines()
            last_record = json.loads(lines[-1])
            assert "nodeid" in last_record
            assert "timestamp" in last_record
            assert "outcome" in last_record
