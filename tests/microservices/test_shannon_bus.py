"""Unit tests for ShannonMicroserviceBus and microservices specifications."""

from __future__ import annotations

import asyncio
import pytest

from cohezion.microservices.bus import ShannonEvent, ShannonMicroserviceBus
from cohezion.microservices.spec import (
    BoundedContext,
    MicroserviceContract,
    MicroserviceHealth,
    MicroserviceStatus,
)


@pytest.mark.asyncio
async def test_bounded_context_and_contract():
    ctx = BoundedContext(
        name="inference_routing",
        lead_scientist="Shannon",
        scientific_domain="Information Theory",
        description="Unified Hybrid Router microservice",
        consolidated_modules=["inference/unified_hybrid_router.py"],
        invariants=["Noisy Channel Coding Theorem"],
    )
    assert ctx.name == "inference_routing"
    assert ctx.lead_scientist == "Shannon"

    contract = MicroserviceContract(
        context=ctx,
        port=8010,
        published_events=["inference.dispatched", "inference.completed"],
        subscribed_events=["inference.requested"],
        max_latency_ms=25.0,
        zero_copy_ipc=True,
    )
    assert contract.port == 8010
    assert contract.max_latency_ms == 25.0


@pytest.mark.asyncio
async def test_shannon_event_entropy_calculation():
    event = ShannonEvent(
        topic="metric.recorded",
        source_service="telemetry",
        target_service="analytics",
        payload={"score": 0.95, "iteration": 42, "status": "nominal"},
    )
    entropy = event.calculate_entropy()
    assert entropy > 0.0
    assert event.entropy_bits == entropy


@pytest.mark.asyncio
async def test_shannon_bus_publish_and_subscribe():
    bus = ShannonMicroserviceBus()
    received_events: list[ShannonEvent] = []

    async def sample_handler(evt: ShannonEvent) -> None:
        received_events.append(evt)

    bus.subscribe("data.processed", sample_handler)

    evt1 = ShannonEvent(
        topic="data.processed",
        source_service="preprocessor",
        target_service="trainer",
        payload={"batch_size": 64},
    )

    handlers_called = await bus.publish(evt1)
    assert handlers_called == 1
    assert len(received_events) == 1
    assert received_events[0].lamport_clock == 1
    assert bus.current_clock == 1
    assert bus.total_messages == 1


@pytest.mark.asyncio
async def test_lamport_clock_monotonicity():
    bus = ShannonMicroserviceBus()
    received: list[ShannonEvent] = []

    async def log_handler(evt: ShannonEvent) -> None:
        received.append(evt)

    bus.subscribe("task.event", log_handler)

    for i in range(5):
        await bus.publish(
            ShannonEvent(
                topic="task.event",
                source_service="worker",
                target_service="coordinator",
                payload={"index": i},
                lamport_clock=i,
            )
        )

    assert len(received) == 5
    clocks = [e.lamport_clock for e in received]
    # Verify strictly monotonic increasing
    assert clocks == [1, 2, 3, 4, 5]
    assert bus.current_clock == 5


@pytest.mark.asyncio
async def test_wildcard_subscription():
    bus = ShannonMicroserviceBus()
    wildcard_received: list[ShannonEvent] = []

    async def wildcard_handler(evt: ShannonEvent) -> None:
        wildcard_received.append(evt)

    bus.subscribe("*", wildcard_handler)

    await bus.publish(
        ShannonEvent(
            topic="alpha.one",
            source_service="s1",
            target_service="s2",
            payload={"key": "val1"},
        )
    )
    await bus.publish(
        ShannonEvent(
            topic="beta.two",
            source_service="s2",
            target_service="s3",
            payload={"key": "val2"},
        )
    )

    assert len(wildcard_received) == 2


@pytest.mark.asyncio
async def test_microservice_health():
    health = MicroserviceHealth(
        service_name="arc_solver",
        status=MicroserviceStatus.HEALTHY,
        latency_ms=12.4,
        memory_mb=256.0,
        error_rate=0.0,
    )
    assert health.is_operational is True

    degraded_health = MicroserviceHealth(
        service_name="arc_solver",
        status=MicroserviceStatus.DEGRADED,
        latency_ms=150.0,
        memory_mb=1024.0,
        error_rate=0.08,
    )
    assert degraded_health.is_operational is False
