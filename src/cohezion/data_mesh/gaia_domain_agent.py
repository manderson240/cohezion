"""GAIA-powered domain agents for event-driven data mesh ownership.

Each GaiaDataAgent owns a specific data domain and reacts to DataMesh
events via local AMD silicon (Bonsai-8B-gguf at :13305, $0 cost).

Design:
- Subscribes only to low-frequency domain-alert event types
  (DATA_PRODUCT_QUALITY_ALERT, DOMAIN_HEALTH_DEGRADED) — never chatty
  types like LLM_CALL or CACHE_HIT that would flood the NPU.
- When GAIA decides HEAL/ALERT/ENRICH, it publishes a follow-on
  EventType.CUSTOM event — side effect is the consumption signal,
  not the return value (EventBus discards handler return values).
- Fail-open: if inference is unavailable, events pass through silently.

Usage:
    agent = GaiaDataAgent(domain="compound-loop")
    agent.subscribe(bus)                           # wires reactive handlers
    actions = await agent.proactive_check(bridge)  # single catch-up pass
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import TYPE_CHECKING, Any

from cohezion.core.event_bus import Event, EventBus, EventType


if TYPE_CHECKING:
    from cohezion.data_mesh.event_bridge import DataMeshEventBridge

logger = logging.getLogger(__name__)

_LEMONADE_URL = "http://localhost:13305/api/v1"
_MODEL = "Bonsai-8B-gguf"

# Only subscribe to decision-worthy, low-frequency domain alert events.
_AGENT_SUBSCRIBED_TYPES: list[EventType] = [
    EventType.DATA_PRODUCT_QUALITY_ALERT,
    EventType.DOMAIN_HEALTH_DEGRADED,
]

_PROMPT_TEMPLATE = """\
You are the {domain} domain agent for Cohezion's data mesh.
A domain event occurred that requires your attention:
  type: {event_type}
  source: {source}
  payload: {payload}

Decide on an action. Output EXACTLY one of these on the first line:
  HEAL     — trigger self-repair (e.g. re-seed skill baselines, restart detector)
  ALERT    — escalate to DegradationDetector or log a critical warning
  ENRICH   — add metadata or quality context to the data product
  PASS     — no action needed, event is nominal

Then on a second line: ≤15 words explaining why.
"""


class GaiaDataAgent:
    """Local-inference domain agent that owns a data mesh domain.

    Reacts to DataMesh events at $0 via Bonsai-8B-gguf on Lemonade :13305.
    When inference decides HEAL/ALERT/ENRICH, publishes a follow-on CUSTOM
    event with the action payload so downstream consumers can act further.
    """

    def __init__(
        self,
        domain: str,
        *,
        model: str = _MODEL,
        lemonade_url: str = _LEMONADE_URL,
        subscribed_types: list[EventType] | None = None,
    ) -> None:
        self.domain = domain
        self._model = model
        self._url = lemonade_url
        self._subscribed_types = subscribed_types or list(_AGENT_SUBSCRIBED_TYPES)
        self._bus: EventBus | None = None
        self._last_seen_ts: float = 0.0

    # ── Bus wiring ─────────────────────────────────────────────────────────────

    def subscribe(self, bus: EventBus) -> None:
        """Attach reactive handler to bus; store reference for publishing follow-on events."""
        self._bus = bus
        for event_type in self._subscribed_types:
            bus._handlers[event_type].append(self.handle_event)

    def unsubscribe(self, bus: EventBus) -> None:
        for event_type in self._subscribed_types:
            bus.unsubscribe(self.handle_event, event_type)

    # ── Reactive handler (EventHandler protocol: async, returns None) ──────────

    async def handle_event(self, event: Event) -> None:
        """Async EventBus handler — called by bus._dispatch via asyncio.gather."""
        # Domain filter: skip events explicitly belonging to another domain
        payload_domain = event.payload.get("domain") or event.payload.get("owner_domain")
        if payload_domain and payload_domain != self.domain:
            return

        action, rationale = await asyncio.to_thread(self._infer_action, event)
        await self._act(action, rationale, event)

    # ── Inference (sync — runs inside asyncio.to_thread) ──────────────────────

    def _infer_action(self, event: Event) -> tuple[str, str]:
        """Call Bonsai-8B to classify the event and recommend an action."""
        try:
            from gaia.llm.lemonade_client import LemonadeClient  # type: ignore[import-not-found]
        except ImportError:
            return "PASS", "inference unavailable — gaia not installed"

        prompt = _PROMPT_TEMPLATE.format(
            domain=self.domain,
            event_type=event.type.name,
            source=event.source,
            payload=str(event.payload)[:400],
        )
        try:
            client = LemonadeClient(base_url=self._url, model=self._model, verbose=False)
            resp = client.chat_completions(
                model=self._model,
                messages=[{"role": "user", "content": prompt}],
                max_tokens=60,
                temperature=0.0,
            )
            raw = resp["choices"][0]["message"].get("content", "").strip()  # type: ignore[index]
        except Exception as exc:
            logger.warning("GaiaDataAgent[%s] inference failed: %s", self.domain, exc)
            return "PASS", f"inference error: {exc}"

        lines = [ln.strip() for ln in raw.splitlines() if ln.strip()]
        action_raw = lines[0].upper() if lines else "PASS"
        rationale = lines[1] if len(lines) > 1 else ""

        for keyword in ("HEAL", "ALERT", "ENRICH", "PASS"):
            if action_raw.startswith(keyword):
                return keyword, rationale

        return "PASS", f"unexpected model output: {raw[:40]!r}"

    # ── Action dispatch (side-effecting: publishes CUSTOM event) ──────────────

    async def _act(self, action: str, rationale: str, trigger: Event) -> None:
        """Publish a follow-on CUSTOM event when action requires it.

        PASS → no-op (inference said event is nominal).
        HEAL/ALERT/ENRICH → CUSTOM event published back to bus so downstream
        consumers (e.g. DegradationDetector, SurrealDB bridge) can act further.
        """
        if action == "PASS" or self._bus is None:
            return
        follow_on = Event(
            type=EventType.CUSTOM,
            source=f"GaiaDataAgent/{self.domain}",
            payload={
                "action": action,
                "domain": self.domain,
                "rationale": rationale,
                "trigger_event": trigger.type.name,
                "trigger_source": trigger.source,
            },
        )
        published = await self._bus.publish(follow_on)
        if published:
            logger.info(
                "GaiaDataAgent[%s] %s — %s (trigger=%s)",
                self.domain,
                action,
                rationale,
                trigger.type.name,
            )
        else:
            logger.warning("GaiaDataAgent[%s] %s dropped — bus queue full", self.domain, action)

    # ── Proactive check (single-iteration catch-up pass) ──────────────────────

    async def proactive_check(self, bridge: DataMeshEventBridge) -> list[str]:
        """Replay events since last checkpoint and act on unprocessed ones.

        Single-iteration: call this on a schedule from outside rather than
        running an infinite internal loop (sandbox-hostile; hard to test).
        Updates _last_seen_ts so subsequent calls don't re-process.

        Returns list of action strings taken per row.
        """
        try:
            rows: list[dict[str, Any]] = bridge.replay_since(self._last_seen_ts)
        except Exception as exc:
            logger.warning("GaiaDataAgent[%s] replay_since failed: %s", self.domain, exc)
            return ["error"]

        actions: list[str] = []
        for row in rows:
            row_domain = row.get("domain") or (row.get("payload") or {}).get("domain")
            if row_domain and row_domain != self.domain:
                actions.append("PASS")
                continue

            synthetic = Event(
                type=EventType.DATA_PRODUCT_QUALITY_ALERT,
                source=row.get("source", "bridge-replay"),
                payload=row.get("payload") or row,
            )
            action, rationale = await asyncio.to_thread(self._infer_action, synthetic)
            await self._act(action, rationale, synthetic)
            actions.append(action)

        self._last_seen_ts = time.time()
        return actions
