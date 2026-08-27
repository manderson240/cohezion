"""Roster of top-tier GAIA SDK domain agents for continuous datamesh improvement.

Composes two existing, tested pieces rather than rebuilding either:

- ``cohezion.inference.fleet_roles.ROSTER`` — live-catalog role→model selection
  (:13305 OmniRouter), adaptively re-ranked by SurrealDB ``model_performance``
  quality scores. This is what makes the agents "top tier": each agent runs the
  best currently-installed model for its role, not a hardcoded ID.
- ``cohezion.data_mesh.gaia_domain_agent.GaiaDataAgent`` — the GAIA-SDK
  (LemonadeClient) event-bus domain agent with HEAL/ALERT/ENRICH/PASS actions.

Continuous improvement is two loops:

1. Mesh loop — deployed agents react to DATA_PRODUCT_QUALITY_ALERT /
   DOMAIN_HEALTH_DEGRADED (and, for the governance agent, lineage/product
   lifecycle events) and publish HEAL/ALERT/ENRICH follow-on CUSTOM events.
   ``improvement_pass()`` additionally replays missed events via the bridge.
2. Roster loop — ``refresh()`` re-resolves each role against the live catalog;
   as ``model_performance`` accumulates, stronger models displace weaker ones
   per role with no code change.

Wiring target (Wire-at-Creation): exported via ``cohezion.data_mesh``;
schedulers (compound daemon / cron) call ``deploy_gaia_agent_roster()`` once,
then ``improvement_pass()`` per tick — single-iteration pattern, no internal
infinite loop. CLI entry: ``python -m cohezion.data_mesh.gaia_agent_roster``.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Protocol

from cohezion.core.event_bus import EventBus, EventType, get_event_bus
from cohezion.data_mesh.gaia_domain_agent import GaiaDataAgent
from cohezion.inference.fleet_roles import ROLE_SPECS, ROSTER


if TYPE_CHECKING:
    from cohezion.data_mesh.event_bridge import DataMeshEventBridge


class ModelSelector(Protocol):
    """The one seam the roster needs from fleet_roles.FleetRoster."""

    def select(self, role: str, *, loadable: bool = False, force: bool = False) -> str | None: ...


logger = logging.getLogger(__name__)

_FALLBACK_MODEL = "Bonsai-8B-gguf"  # GaiaDataAgent's proven default; always in catalog

# Governance agent watches low-frequency lifecycle events, not just alerts.
_GOVERNANCE_TYPES: tuple[EventType, ...] = (
    EventType.LINEAGE_UPDATED,
    EventType.DATA_PRODUCT_CREATED,
    EventType.DATA_PRODUCT_UPDATED,
    EventType.DATA_PRODUCT_QUALITY_ALERT,
    EventType.DOMAIN_HEALTH_DEGRADED,
)


@dataclass(frozen=True)
class AgentSpec:
    """One roster seat: which domain an agent owns and which fleet role staffs it."""

    domain: str
    role: str  # key into fleet_roles.ROLE_SPECS
    mission: str  # one line, for logs/summary
    subscribed_types: tuple[EventType, ...] = ()  # () → GaiaDataAgent default alerts


# Domains match the owner_domain values of registered data products
# (data_product.py / inference_products.py / research_products.py).
DEFAULT_AGENT_SPECS: tuple[AgentSpec, ...] = (
    AgentSpec(
        domain="inference",
        role="interactive",
        mission="heal inference data products (routing telemetry, tier SLAs)",
    ),
    AgentSpec(
        domain="skills",
        role="interactive",
        mission="guard skill-registry product quality for the compound loop",
    ),
    AgentSpec(
        domain="journey",
        role="interactive",
        mission="keep journey/trajectory telemetry products healthy",
    ),
    AgentSpec(
        domain="research",
        role="bbq",
        mission="enrich research findings with reasoning-tier context",
    ),
    AgentSpec(
        domain="memory",
        role="interactive",
        mission="watch vault/memory product freshness and quality",
    ),
    AgentSpec(
        domain="governance",
        role="bbq",
        mission="review lineage and product lifecycle changes for architectural drift",
        subscribed_types=_GOVERNANCE_TYPES,
    ),
)


class GaiaAgentRoster:
    """Builds, deploys, and refreshes a fleet of GaiaDataAgents.

    The roster SELECTS (via FleetRoster) and BINDS (agent→bus); the agents ACT.
    """

    def __init__(
        self,
        specs: tuple[AgentSpec, ...] = DEFAULT_AGENT_SPECS,
        fleet: ModelSelector = ROSTER,
    ) -> None:
        unknown = [s.role for s in specs if s.role not in ROLE_SPECS]
        if unknown:
            raise KeyError(f"unknown fleet roles {unknown}; known: {sorted(ROLE_SPECS)}")
        self._specs = specs
        self._fleet = fleet
        self._agents: dict[str, GaiaDataAgent] = {}
        self._bus: EventBus | None = None

    # ── model selection ────────────────────────────────────────────────────────

    def resolve_model(self, spec: AgentSpec) -> str:
        """Best live model for the spec's role; never raises, falls back on any miss."""
        try:
            selected = self._fleet.select(spec.role, loadable=True)
        except Exception as exc:  # catalog down, role drift — degrade, don't crash
            logger.debug("roster: select(%s) failed: %s", spec.role, exc)
            selected = None
        return selected or _FALLBACK_MODEL

    # ── lifecycle ──────────────────────────────────────────────────────────────

    def _make_agent(self, spec: AgentSpec) -> GaiaDataAgent:
        agent = GaiaDataAgent(
            domain=spec.domain,
            model=self.resolve_model(spec),
            subscribed_types=list(spec.subscribed_types) or None,
        )
        # Start catch-up from NOW: bridge.replay_since has no LIMIT, so an agent
        # at the default _last_seen_ts=0 would replay the entire event table
        # (× N agents × one inference each) on its first improvement_pass.
        agent._last_seen_ts = time.time()
        return agent

    def build(self) -> dict[str, GaiaDataAgent]:
        """Instantiate one agent per spec with the current best model per role."""
        self._agents = {spec.domain: self._make_agent(spec) for spec in self._specs}
        return self._agents

    def deploy(self, bus: EventBus) -> dict[str, GaiaDataAgent]:
        """Build (if needed) and subscribe every agent to the bus."""
        self._bus = bus
        if not self._agents:
            self.build()
        for agent in self._agents.values():
            agent.subscribe(bus)
            logger.info("roster: deployed GaiaDataAgent[%s] model=%s", agent.domain, agent._model)
        return self._agents

    def refresh(self) -> dict[str, str]:
        """Re-resolve roles against the live catalog; swap agents whose best model changed.

        Returns {domain: model} after refresh. Swapped agents are unsubscribed
        and their replacements subscribed when the roster is deployed.
        """
        changed: list[str] = []
        for spec in self._specs:
            current = self._agents.get(spec.domain)
            best = self.resolve_model(spec)
            if current is not None and current._model == best:
                continue
            replacement = self._make_agent(spec)
            if current is not None:
                # Preserve the catch-up checkpoint across a model swap so the
                # replacement doesn't re-process (or skip) the handover window.
                replacement._last_seen_ts = current._last_seen_ts
            if self._bus is not None:
                if current is not None:
                    current.unsubscribe(self._bus)
                replacement.subscribe(self._bus)
            self._agents[spec.domain] = replacement
            changed.append(spec.domain)
        if changed:
            logger.info("roster: refreshed agents for domains %s", changed)
        return {domain: agent._model for domain, agent in self._agents.items()}

    # ── improvement pass (single iteration; schedule from outside) ─────────────

    async def improvement_pass(self, bridge: DataMeshEventBridge) -> dict[str, list[str]]:
        """One catch-up pass: each agent replays missed events and acts on them."""
        results: dict[str, list[str]] = {}
        for domain, agent in self._agents.items():
            results[domain] = await agent.proactive_check(bridge)
        return results

    def summary(self) -> list[dict[str, Any]]:
        """Roster manifest: who owns what, on which model, with what mission."""
        by_domain = {s.domain: s for s in self._specs}
        return [
            {
                "domain": domain,
                "model": agent._model,
                "role": by_domain[domain].role,
                "mission": by_domain[domain].mission,
                "events": [t.name for t in agent._subscribed_types],
            }
            for domain, agent in self._agents.items()
        ]


async def deploy_gaia_agent_roster(
    specs: tuple[AgentSpec, ...] = DEFAULT_AGENT_SPECS,
) -> GaiaAgentRoster:
    """Factory: build the roster and subscribe every agent to the global bus."""
    roster = GaiaAgentRoster(specs)
    roster.deploy(await get_event_bus())
    return roster


def main() -> None:  # pragma: no cover - thin CLI shim over tested pieces
    """Deploy the roster and run one improvement pass (cron/daemon entry point)."""
    import asyncio
    import json

    from cohezion.data_mesh.event_bridge import make_event_bridge

    async def _run() -> None:
        roster = await deploy_gaia_agent_roster()
        print(json.dumps(roster.summary(), indent=2))
        bridge = make_event_bridge()
        if bridge is not None:
            actions = await roster.improvement_pass(bridge)
            print(json.dumps({"improvement_pass": actions}, indent=2))

    asyncio.run(_run())


if __name__ == "__main__":  # pragma: no cover
    main()
