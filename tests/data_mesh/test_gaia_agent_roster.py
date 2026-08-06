"""Tests for GaiaAgentRoster — V-model invariants GAR1–GAR6.

GAR1: structural — default specs valid (known roles, unique domains, governance lineage watch)
GAR2: consumption — resolve_model READS FleetRoster.select (top-tier binding), falls back on miss
GAR3: consumption — deploy subscribes every agent's handler to the bus
GAR4: consumption — improvement_pass drives proactive_check per agent
GAR5: discriminating — refresh swaps an agent when the catalog's best model changes
GAR6: fail-fast — unknown fleet role rejected at construction
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, cast
from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.core.event_bus import EventBus, EventType, reset_event_bus
from cohezion.data_mesh.gaia_agent_roster import (
    DEFAULT_AGENT_SPECS,
    AgentSpec,
    GaiaAgentRoster,
)
from cohezion.inference.fleet_roles import ROLE_SPECS


if TYPE_CHECKING:
    from cohezion.data_mesh.event_bridge import DataMeshEventBridge


@pytest.fixture(autouse=True)
def _reset_bus():
    reset_event_bus()
    yield
    reset_event_bus()


class StubFleet:
    """FleetRoster stand-in with a scriptable select()."""

    def __init__(self, by_role: dict[str, str | None] | None = None, raise_exc: bool = False):
        self.by_role = by_role or {}
        self.raise_exc = raise_exc
        self.calls: list[str] = []

    def select(self, role: str, *, loadable: bool = False, force: bool = False) -> str | None:
        self.calls.append(role)
        if self.raise_exc:
            raise RuntimeError("catalog down")
        return self.by_role.get(role)


# ── GAR1: structural ──────────────────────────────────────────────────────────


def test_gar1_default_spec_roles_exist_in_fleet():
    assert DEFAULT_AGENT_SPECS
    for spec in DEFAULT_AGENT_SPECS:
        assert spec.role in ROLE_SPECS, spec


def test_gar1_default_spec_domains_unique():
    domains = [s.domain for s in DEFAULT_AGENT_SPECS]
    assert len(domains) == len(set(domains))


def test_gar1_governance_agent_watches_lineage():
    gov = next(s for s in DEFAULT_AGENT_SPECS if s.domain == "governance")
    assert EventType.LINEAGE_UPDATED in gov.subscribed_types


# ── GAR2: model resolution consumes FleetRoster ───────────────────────────────


def test_gar2_build_binds_top_tier_model_from_fleet():
    fleet = StubFleet({"interactive": "TopTier-Model", "bbq": "Reasoner-26B"})
    roster = GaiaAgentRoster(fleet=fleet)
    agents = roster.build()
    assert agents["inference"]._model == "TopTier-Model"
    assert agents["research"]._model == "Reasoner-26B"
    assert fleet.calls  # a wrong impl that ignores the fleet never calls select


def test_gar2_fallback_when_catalog_empty():
    roster = GaiaAgentRoster(fleet=StubFleet({}))
    agents = roster.build()
    assert all(a._model == "Bonsai-8B-gguf" for a in agents.values())


def test_gar2_fallback_when_select_raises():
    roster = GaiaAgentRoster(fleet=StubFleet(raise_exc=True))
    agents = roster.build()
    assert all(a._model == "Bonsai-8B-gguf" for a in agents.values())


# ── GAR3: deploy wires every agent onto the bus ───────────────────────────────


def test_gar3_deploy_subscribes_all_agents():
    roster = GaiaAgentRoster(fleet=StubFleet({}))
    bus = EventBus()
    agents = roster.deploy(bus)
    for agent in agents.values():
        assert any(
            getattr(h, "__self__", None) is agent
            for et in agent._subscribed_types
            for h in bus._handlers[et]
        ), f"agent {agent.domain} not subscribed"


def test_gar3_governance_subscribed_to_lifecycle_events():
    roster = GaiaAgentRoster(fleet=StubFleet({}))
    bus = EventBus()
    gov = roster.deploy(bus)["governance"]
    handlers = bus._handlers[EventType.LINEAGE_UPDATED]
    assert any(getattr(h, "__self__", None) is gov for h in handlers)


# ── GAR4: improvement_pass drives proactive_check ─────────────────────────────


def test_gar4_improvement_pass_calls_each_agent():
    roster = GaiaAgentRoster(fleet=StubFleet({}))
    roster.build()
    mocks: dict[str, AsyncMock] = {}
    for domain, agent in roster._agents.items():
        mocks[domain] = AsyncMock(return_value=["HEAL"])
        agent.proactive_check = mocks[domain]  # type: ignore[method-assign]
    bridge = cast("DataMeshEventBridge", MagicMock())
    results = asyncio.run(roster.improvement_pass(bridge))
    assert set(results) == {s.domain for s in DEFAULT_AGENT_SPECS}
    assert all(v == ["HEAL"] for v in results.values())
    for mock in mocks.values():
        mock.assert_awaited_once_with(bridge)


# ── GAR5: refresh swaps agents when the catalog's best model changes ──────────


def test_gar5_refresh_swaps_model_and_resubscribes():
    fleet = StubFleet({"interactive": "Model-A", "bbq": "Model-A"})
    roster = GaiaAgentRoster(fleet=fleet)
    bus = EventBus()
    old = roster.deploy(bus)["inference"]
    assert old._model == "Model-A"

    fleet.by_role["interactive"] = "Model-B"
    models = roster.refresh()

    new = roster._agents["inference"]
    assert models["inference"] == "Model-B"
    assert new is not old  # a no-op refresh impl keeps the stale agent
    handlers = bus._handlers[EventType.DATA_PRODUCT_QUALITY_ALERT]
    assert any(getattr(h, "__self__", None) is new for h in handlers)
    assert not any(getattr(h, "__self__", None) is old for h in handlers)


def test_gar5_refresh_noop_when_best_model_unchanged():
    fleet = StubFleet({"interactive": "Model-A", "bbq": "Model-A"})
    roster = GaiaAgentRoster(fleet=fleet)
    roster.build()
    before = dict(roster._agents)
    roster.refresh()
    assert roster._agents == before


# ── GAR7: first-pass replay is bounded ────────────────────────────────────────


def test_gar7_built_agents_start_catchup_from_now():
    """bridge.replay_since has no LIMIT — an agent left at _last_seen_ts=0 would
    replay the ENTIRE event table on its first improvement_pass."""
    import time

    before = time.time()
    roster = GaiaAgentRoster(fleet=StubFleet({}))
    agents = roster.build()
    for agent in agents.values():
        assert agent._last_seen_ts >= before, f"{agent.domain} would replay full history"


def test_gar7_refresh_preserves_catchup_checkpoint():
    fleet = StubFleet({"interactive": "Model-A", "bbq": "Model-A"})
    roster = GaiaAgentRoster(fleet=fleet)
    roster.build()
    roster._agents["inference"]._last_seen_ts = 12345.0
    fleet.by_role["interactive"] = "Model-B"
    roster.refresh()
    assert roster._agents["inference"]._last_seen_ts == 12345.0


# ── GAR6: fail-fast on unknown role ───────────────────────────────────────────


def test_gar6_unknown_role_rejected():
    bad = (AgentSpec(domain="x", role="nonexistent-role", mission="m"),)
    with pytest.raises(KeyError):
        GaiaAgentRoster(specs=bad)


def test_summary_manifest_shape():
    roster = GaiaAgentRoster(fleet=StubFleet({"interactive": "M", "bbq": "M"}))
    roster.build()
    rows = roster.summary()
    assert len(rows) == len(DEFAULT_AGENT_SPECS)
    assert {"domain", "model", "role", "mission", "events"} <= set(rows[0])
