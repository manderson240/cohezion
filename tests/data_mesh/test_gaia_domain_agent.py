"""Tests for GaiaDataAgent — V-model invariants GDA1–GDA5.

GDA1: structural interface (domain attr, subscribe, coroutine)
GDA2: HEAL decision → CUSTOM event published (consumption invariant)
GDA3: fail-open — inference unavailable → no CUSTOM event (neutralize test)
GDA4: domain filter — wrong-domain event → no action
GDA5: proactive_check returns list of action strings
"""

from __future__ import annotations

import asyncio
from unittest.mock import MagicMock, patch

import pytest

from cohezion.core.event_bus import Event, EventBus, EventType, reset_event_bus
from cohezion.data_mesh.gaia_domain_agent import GaiaDataAgent


# ── fixtures ──────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


@pytest.fixture
def agent():
    return GaiaDataAgent(domain="compound-loop")


@pytest.fixture
def bus():
    return EventBus()


async def _drain(bus: EventBus, delay: float = 0.05) -> None:
    """Let bus processor dispatch queued events."""
    await asyncio.sleep(delay)


# ── GDA1: structural ──────────────────────────────────────────────────────────


def test_gda1_domain_attribute(agent):
    assert agent.domain == "compound-loop"


def test_gda1_subscribe_wires_handlers(agent, bus):
    agent.subscribe(bus)
    # Bound methods are new objects on each attribute access; compare by __self__ instead.
    assert any(
        getattr(h, "__self__", None) is agent
        for et in [EventType.DATA_PRODUCT_QUALITY_ALERT, EventType.DOMAIN_HEALTH_DEGRADED]
        for h in bus._handlers[et]
    )


def test_gda1_handle_event_is_coroutine(agent):
    import inspect

    assert inspect.iscoroutinefunction(agent.handle_event)


def test_gda1_bus_reference_stored_after_subscribe(agent, bus):
    agent.subscribe(bus)
    assert agent._bus is bus


# ── GDA2: discriminating consumption invariant ─────────────────────────────────
# Neutralizing inference must make the CUSTOM event disappear.


@pytest.mark.asyncio
async def test_gda2_heal_decision_publishes_custom_event(agent, bus):
    """HEAL decision → CUSTOM event published to bus (side effect, not return)."""
    await bus.start()
    received: list[Event] = []

    @bus.subscribe(EventType.CUSTOM)
    async def capture(event: Event) -> None:
        received.append(event)

    agent.subscribe(bus)

    alert = Event(
        type=EventType.DATA_PRODUCT_QUALITY_ALERT,
        source="test-source",
        payload={"domain": "compound-loop", "quality_score": 0.2},
    )

    with patch.object(agent, "_infer_action", return_value=("HEAL", "skill baselines degraded")):
        await bus.publish(alert)
        await _drain(bus, delay=0.1)

    await bus.stop()

    assert len(received) == 1
    p = received[0].payload
    assert p["action"] == "HEAL"
    assert p["domain"] == "compound-loop"
    assert p["trigger_event"] == "DATA_PRODUCT_QUALITY_ALERT"


@pytest.mark.asyncio
async def test_gda2_neutralize_inference_no_custom_event(agent, bus):
    """Neutralizing inference (PASS) → no CUSTOM event published.

    This is the discriminating test: if CUSTOM appeared despite PASS,
    the handler would not be acting on inference — just presence of code.
    """
    await bus.start()
    received: list[Event] = []

    @bus.subscribe(EventType.CUSTOM)
    async def capture(event: Event) -> None:
        received.append(event)

    agent.subscribe(bus)

    alert = Event(
        type=EventType.DATA_PRODUCT_QUALITY_ALERT,
        source="test-source",
        payload={"domain": "compound-loop", "quality_score": 0.9},
    )

    with patch.object(agent, "_infer_action", return_value=("PASS", "nominal")):
        await bus.publish(alert)
        await _drain(bus, delay=0.1)

    await bus.stop()

    assert len(received) == 0, "PASS decision must not publish any CUSTOM event"


@pytest.mark.asyncio
async def test_gda2_alert_decision_publishes_custom_event(agent, bus):
    """ALERT decision also triggers a CUSTOM event (all non-PASS decisions do)."""
    await bus.start()
    received: list[Event] = []

    @bus.subscribe(EventType.CUSTOM)
    async def capture(event: Event) -> None:
        received.append(event)

    agent.subscribe(bus)
    alert = Event(
        type=EventType.DOMAIN_HEALTH_DEGRADED,
        source="health-monitor",
        payload={"domain": "compound-loop"},
    )
    with patch.object(agent, "_infer_action", return_value=("ALERT", "coherence below threshold")):
        await bus.publish(alert)
        await _drain(bus, delay=0.1)

    await bus.stop()
    assert len(received) == 1
    assert received[0].payload["action"] == "ALERT"


# ── GDA3: fail-open ───────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gda3_fail_open_when_gaia_not_installed(bus):
    """If gaia is not importable, handle_event is a no-op (fail-open)."""
    await bus.start()
    received: list[Event] = []

    @bus.subscribe(EventType.CUSTOM)
    async def capture(event: Event) -> None:
        received.append(event)

    agent = GaiaDataAgent(domain="compound-loop")
    agent.subscribe(bus)

    alert = Event(
        type=EventType.DATA_PRODUCT_QUALITY_ALERT,
        source="test",
        payload={"domain": "compound-loop"},
    )

    # Simulate ImportError from gaia
    import builtins

    original_import = builtins.__import__

    def blocked_import(name, *args, **kwargs):
        if name == "gaia.llm.lemonade_client":
            raise ImportError("gaia not installed")
        return original_import(name, *args, **kwargs)

    with patch("builtins.__import__", side_effect=blocked_import):
        await bus.publish(alert)
        await _drain(bus, delay=0.1)

    await bus.stop()
    assert len(received) == 0, "fail-open: ImportError must not publish CUSTOM events"


# ── GDA4: domain filter ───────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gda4_wrong_domain_event_is_ignored(agent, bus):
    """Events explicitly for another domain are silently filtered."""
    await bus.start()
    received: list[Event] = []

    @bus.subscribe(EventType.CUSTOM)
    async def capture(event: Event) -> None:
        received.append(event)

    agent.subscribe(bus)

    wrong_domain_alert = Event(
        type=EventType.DATA_PRODUCT_QUALITY_ALERT,
        source="other-service",
        payload={"domain": "inference", "quality_score": 0.1},  # not our domain
    )

    with patch.object(agent, "_infer_action", return_value=("HEAL", "reason")) as mock_infer:
        await bus.publish(wrong_domain_alert)
        await _drain(bus, delay=0.1)
        # inference must NOT have been called for a foreign domain
        mock_infer.assert_not_called()

    await bus.stop()
    assert len(received) == 0


@pytest.mark.asyncio
async def test_gda4_no_domain_in_payload_is_accepted(agent, bus):
    """Events without a domain payload field are accepted (not filtered)."""
    await bus.start()
    received: list[Event] = []

    @bus.subscribe(EventType.CUSTOM)
    async def capture(event: Event) -> None:
        received.append(event)

    agent.subscribe(bus)
    generic_alert = Event(
        type=EventType.DATA_PRODUCT_QUALITY_ALERT,
        source="generic",
        payload={"quality_score": 0.1},  # no domain key
    )

    with patch.object(agent, "_infer_action", return_value=("ALERT", "degraded")):
        await bus.publish(generic_alert)
        await _drain(bus, delay=0.1)

    await bus.stop()
    assert len(received) == 1


# ── GDA5: proactive_check ─────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_gda5_proactive_check_returns_action_list(agent, bus):
    """proactive_check returns one action string per replayed row."""
    await bus.start()
    agent.subscribe(bus)

    bridge = MagicMock()
    bridge.replay_since.return_value = [
        {"domain": "compound-loop", "source": "bridge", "payload": {"quality_score": 0.2}},
        {"domain": "compound-loop", "source": "bridge", "payload": {"quality_score": 0.1}},
    ]

    with patch.object(agent, "_infer_action", return_value=("HEAL", "degraded")):
        actions = await agent.proactive_check(bridge)

    await bus.stop()
    assert len(actions) == 2
    assert all(a == "HEAL" for a in actions)


@pytest.mark.asyncio
async def test_gda5_proactive_check_updates_last_seen_ts(agent, bus):
    """last_seen_ts advances after proactive_check so rows aren't reprocessed."""
    await bus.start()
    agent.subscribe(bus)

    ts_before = agent._last_seen_ts
    bridge = MagicMock()
    bridge.replay_since.return_value = []

    await agent.proactive_check(bridge)
    await bus.stop()

    assert agent._last_seen_ts > ts_before


@pytest.mark.asyncio
async def test_gda5_proactive_check_skips_foreign_domain_rows(agent, bus):
    """Rows for a different domain are skipped (action = PASS)."""
    await bus.start()
    agent.subscribe(bus)

    bridge = MagicMock()
    bridge.replay_since.return_value = [
        {"domain": "inference", "source": "bridge", "payload": {}},
    ]

    with patch.object(agent, "_infer_action") as mock_infer:
        actions = await agent.proactive_check(bridge)
        mock_infer.assert_not_called()

    await bus.stop()
    assert actions == ["PASS"]


@pytest.mark.asyncio
async def test_gda5_proactive_check_returns_error_on_bridge_failure(agent, bus):
    """Bridge replay failure → ['error'] returned, no crash."""
    await bus.start()
    agent.subscribe(bus)

    bridge = MagicMock()
    bridge.replay_since.side_effect = RuntimeError("SurrealDB unavailable")

    actions = await agent.proactive_check(bridge)
    await bus.stop()
    assert actions == ["error"]
