"""Demand-driven model hotswap orchestrator — composes existing pieces instead of rebuilding.

This module is the thin composition layer the fleet has been missing:

* ``inference/hotswap.py`` already knows how to evict LRU models and load safely.
* ``inference/fleet_roles.py`` already selects the best live model for a role.
* ``inference/oom_guard.py`` / ``load_safety.py`` already gate unsafe loads.
* ``core/event_bus.py`` already publishes system events.
* ``data_mesh/kanban_bridge.py`` already persists backlog items.
* ``researcher/daily_researcher.py`` already provides ``FleetLock``.

``ModelSprintOrchestrator`` wires them together:

1. Polling or EventBus ``MODEL_ROSTER_CHANGED`` triggers an update.
2. For each requested role, resolve a candidate from the live :13305 catalog.
3. Run preflight + weight-fit gate before any load.
4. Acquire ``fleet_lock:modelload`` (single-flight for model loads).
5. Call ``hotswap.ensure_resident`` with card-aligned params.
6. Publish lifecycle events and Kanban items for human review.

This is intentionally daemon-friendly: the orchestrator has no CLI/UI coupling and
works in an async event loop.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from typing import Any

from cohezion.core.event_bus import Event, EventBus, EventType, get_event_bus
from cohezion.data_mesh.kanban_bridge import persist_item
from cohezion.inference import hotswap
from cohezion.inference.fleet_roles import ROLE_SPECS, ROSTER, FleetRoster
from cohezion.inference.model_card_harness import ModelCardHarness
from cohezion.inference.oom_guard import pre_load_gate
from cohezion.researcher.daily_researcher import FleetLock


logger = logging.getLogger(__name__)

DEFAULT_BASE_URL = "http://localhost:13305"
MODEL_LOAD_LOCK = "modelload"


@dataclass
class SprintResult:
    """Outcome of one model-sprint attempt."""

    role: str
    model_id: str
    ok: bool
    reason: str = ""
    evicted: list[str] = field(default_factory=list)
    already_resident: bool = False


class ModelSprintOrchestrator:
    """Demand-driven orchestrator that safely hot-swaps the local model fleet.

    Args:
        base_url: Lemonade OmniRouter URL.
        roster: Optional FleetRoster instance (defaults to singleton).
        bus: Optional EventBus instance (defaults to global).
        lock: Optional FleetLock instance (defaults to new).
        min_free_gb: Minimum free RAM floor passed to the safety gate.
    """

    def __init__(
        self,
        base_url: str = DEFAULT_BASE_URL,
        roster: FleetRoster | None = None,
        bus: EventBus | None = None,
        lock: FleetLock | None = None,
        min_free_gb: float = 20.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.roster = roster if roster is not None else ROSTER
        self.bus = bus
        self.lock = lock if lock is not None else FleetLock()
        self.min_free_gb = min_free_gb
        self._previous_catalog_ids: set[str] = set()

    # ── Public API ────────────────────────────────────────────────────────────

    async def refresh_catalog(self) -> list[dict[str, Any]]:
        """Fetch live model catalog from :13305, updating the roster cache."""
        return self.roster.catalog(force=True)

    async def detect_roster_changes(self) -> tuple[list[str], list[str], list[str]]:
        """Return (new_models, removed_models, current_models) since last call."""
        current = [m.get("id", "") for m in await self.refresh_catalog() if m.get("id")]
        current_set = set(current)
        new_models = sorted(current_set - self._previous_catalog_ids)
        removed_models = sorted(self._previous_catalog_ids - current_set)
        self._previous_catalog_ids = current_set
        return new_models, removed_models, current

    async def run_sprint(
        self,
        roles: list[str] | None = None,
        *,
        protect: tuple[str, ...] = (),
        load_timeout: float = 300.0,
    ) -> list[SprintResult]:
        """Ensure the best model for each role is resident.

        If a role is omitted, the default sprint targets the roles referenced by
        ``user.cohezion-router`` policy: interactive, code, reason, fast, route.
        """
        if roles is None:
            roles = ["interactive", "code", "reason", "fast", "route"]

        # Translate user-facing aliases to FleetRoster role names.

        role_alias: dict[str, str] = {
            "interactive": "interactive",
            "code": "interactive",
            "reason": "npu_reason",
            "fast": "draft",
            "route": "npu_route",
            "deep": "deep",
            "draft": "draft",
            "bbq": "bbq",
            "npu_reason": "npu_reason",
            "npu_route": "npu_route",
            "npu_embed": "npu_embed",
            "embed": "embed",
            "image": "image",
            "mesh_3d": "mesh_3d",
        }
        normalized_roles = [role_alias.get(r, r) for r in roles]

        await self.refresh_catalog()
        results: list[SprintResult] = []

        for role, norm_role in zip(roles, normalized_roles, strict=True):
            try:
                result = await self._ensure_role(role, norm_role, protect, load_timeout)
            except Exception as exc:
                logger.exception("sprint failed for role %s", role)
                result = SprintResult(role, "", False, f"exception: {exc}")
            results.append(result)

        return results

    async def ensure_model(
        self,
        model_id: str,
        *,
        protect: tuple[str, ...] = (),
        load_timeout: float = 300.0,
    ) -> SprintResult:
        """Ensure a specific model_id is resident, bypassing role resolution."""
        await self.refresh_catalog()
        # Find a role that maps to this model so _aligned_ctx_size works.
        norm_role = None
        for role in ROLE_SPECS:
            if self.roster.select(role, loadable=True) == model_id:
                norm_role = role
                break
        if norm_role is None:
            norm_role = "interactive"
        return await self._ensure_role(
            "ensure_model", norm_role, protect, load_timeout, forced_model=model_id
        )

    async def update_on_roster_change(
        self,
        new_models: list[str],
        removed_models: list[str],
        current_models: list[str],
    ) -> None:
        """React to a roster change: publish events, create kanban items, and sprint."""
        await self._publish(Event.roster_changed(new_models, removed_models, current_models))

        for mid in new_models:
            role_guess = self._guess_role_for_model(mid)
            if role_guess:
                await self._publish(
                    Event.model_lifecycle(
                        EventType.MODEL_LOADING,
                        mid,
                        reason=f"auto-detected role: {role_guess}",
                    )
                )
                # Run a focused sprint for the discovered role.
                await self.run_sprint([role_guess], protect=tuple(current_models))
            else:
                await self._backlog_new_model(mid)

        for mid in removed_models:
            await self._publish(
                Event.model_lifecycle(EventType.MODEL_EVICTED, mid, reason="removed from catalog")
            )

    async def poll_forever(self, interval_s: float = 60.0) -> None:
        """Daemon loop: detect roster changes and react forever."""
        while True:
            try:
                new_models, removed_models, current = await self.detect_roster_changes()
                if new_models or removed_models:
                    await self.update_on_roster_change(new_models, removed_models, current)
            except Exception as exc:
                logger.exception("roster poll iteration failed: %s", exc)
            await asyncio.sleep(interval_s)

    # ── Internal helpers ──────────────────────────────────────────────────────

    async def _ensure_role(
        self,
        role: str,
        norm_role: str,
        protect: tuple[str, ...],
        load_timeout: float,
        *,
        forced_model: str | None = None,
    ) -> SprintResult:
        """Resolve role -> model and ensure resident, guarded and locked."""
        model_id = forced_model or self.roster.select(norm_role, loadable=True)
        if model_id is None:
            return SprintResult(role, "", False, "no loadable model for role")

        # 0. Already resident → nothing to load: skip the RAM gate and the load lock.
        #    Gating a resident model on free RAM reported "insufficient RAM" failures (and
        #    persisted spurious model-load-failed items) on any box under the floor — the
        #    CI runner included — for a model that was already serving.
        if any(m.get("model_name") == model_id for m in hotswap.resident_models()):
            await self._publish(
                Event.model_lifecycle(
                    EventType.MODEL_LOADED,
                    model_id,
                    reason="already resident",
                    already_resident=True,
                    role=role,
                )
            )
            return SprintResult(role, model_id, True, "already resident", already_resident=True)

        # 1. Safety gate (static refusal if unsafe).
        ctx_size = self._aligned_ctx_size(model_id, norm_role)
        allowed, reason = pre_load_gate(model_id, ctx_size, min_free_gb=self.min_free_gb)
        if not allowed:
            await self._publish(
                Event.model_lifecycle(
                    EventType.MODEL_LOAD_REFUSED,
                    model_id,
                    reason=f"pre_load_gate: {reason}",
                    role=role,
                )
            )
            return SprintResult(role, model_id, False, reason)

        # 2. Single-flight model load.
        async with self.lock.acquire(MODEL_LOAD_LOCK, timeout=600.0):
            await self._publish(
                Event.model_lifecycle(
                    EventType.MODEL_LOADING,
                    model_id,
                    reason=f"role={role}",
                    ctx_size=ctx_size,
                )
            )
            hotswap.MAX_CTX = min(hotswap.MAX_CTX, ctx_size)
            result = await asyncio.to_thread(
                hotswap.ensure_resident,
                model_id,
                ctx_size=ctx_size,
                min_free_gb=self.min_free_gb,
                protect=protect,
                load_timeout=load_timeout,
            )

        if result.ok:
            await self._publish(
                Event.model_lifecycle(
                    EventType.MODEL_LOADED,
                    model_id,
                    reason=result.reason,
                    evicted=result.evicted,
                    already_resident=result.already_resident,
                    role=role,
                )
            )
        else:
            await self._publish(
                Event.model_lifecycle(
                    EventType.MODEL_LOAD_REFUSED,
                    model_id,
                    reason=result.reason,
                    role=role,
                )
            )
            await self._backlog_failed_load(model_id, role, result.reason)

        return SprintResult(
            role,
            model_id,
            result.ok,
            result.reason,
            evicted=list(result.evicted),
            already_resident=result.already_resident,
        )

    def _aligned_ctx_size(self, model_id: str, role: str) -> int:
        """Card-aligned context size; never returns 0."""
        from cohezion.inference.registry import Task

        role_upper = role.upper()
        task = next(
            (t for t in Task if t.value.upper() == role_upper),
            Task.GENERAL,
        )
        try:
            port = 13305
            if self.base_url.startswith("http://localhost:"):
                try:
                    port = int(self.base_url.rsplit(":", 1)[-1])
                except ValueError:
                    port = 13305
            harness = ModelCardHarness.from_live_api(port=port)
            params = harness.aligned_params(model_id, task)
            ctx = params.max_tokens
            if isinstance(ctx, (int, float)) and ctx > 0:
                return int(ctx)
        except Exception as exc:
            logger.debug("could not resolve aligned ctx_size for %s: %s", model_id, exc)
        # Conservative defaults by role.
        defaults: dict[str, int] = {
            "interactive": 32768,
            "code": 32768,
            "reason": 40960,
            "fast": 4096,
            "route": 4096,
            "npu_embed": 8192,
            "embed": 8192,
            "image": 2048,
            "mesh_3d": 2048,
            "bbq": 40960,
            "deep": 16384,
            "draft": 4096,
            "npu_reason": 40960,
            "npu_route": 4096,
        }
        return defaults.get(role, 16384)

    def _guess_role_for_model(self, model_id: str) -> str | None:
        """Map a newly discovered model to a router role, or None if ambiguous."""
        mid = model_id.lower()
        # Vision / image generation
        if any(x in mid for x in ("flux", "sd-turbo", "vision", "qwen3vl")):
            return "image"
        # Embeddings
        if any(x in mid for x in ("embed", "nomic", "embedding")):
            if "flm" in mid:
                return "npu_embed"
            return "embed"
        # Code
        if any(x in mid for x in ("coder", "code-", "starcoder", "qwen3-coder")):
            return "code"
        # Reasoning / deep
        if any(x in mid for x in ("deepseek-r1", "nemotron", "mistral-medium", "128b", "70b")):
            return "reason"
        # Tiny routing / ack models
        if any(x in mid for x in ("1b", "llama3.2-1b", "gemma3-1b")) and "flm" in mid:
            return "route"
        # Fast QnA
        if any(x in mid for x in ("qwen3-4b", "gemma3-4b", "phi-4", "llama3.2-3b")):
            return "fast"
        # Interactive default
        if any(x in mid for x in ("qwen3.6", "moe", "a3b", "mtp")):
            return "interactive"
        return None

    async def _publish(self, event: Event) -> None:
        """Publish event to the configured bus, if any.

        Works whether or not a running asyncio loop exists. If no bus was
        supplied, the global singleton is lazily created (only inside an async
        context, to avoid cross-loop queue binding issues).
        """
        bus = self.bus
        if bus is None:
            try:
                asyncio.get_running_loop()
            except RuntimeError:
                logger.debug("no running loop; skipping event %s", event.type)
                return
            try:
                bus = await get_event_bus()
                self.bus = bus
            except Exception as exc:
                logger.debug("could not get event bus: %s", exc)
                return
        try:
            if bus._running:
                await bus.publish(event)
            else:
                bus.publish_sync(event)
        except Exception as exc:
            logger.warning("failed to publish event %s: %s", event.type, exc)

    async def _backlog_new_model(self, model_id: str) -> None:
        """Create a kanban item for an ambiguous newly discovered model."""
        item = {
            "id": f"model-roster-new-{model_id}",
            "title": f"Review new model in Lemonade catalog: {model_id}",
            "status": "backlog",
            "priority": "medium",
            "source": "model_sprint_orchestrator",
            "category": "model_roster",
            "notes": "Auto-detected role is ambiguous. Add to config/router/cohezion-router.json if it should become a routing candidate.",
        }
        try:
            await asyncio.to_thread(persist_item, item)
        except Exception as exc:
            logger.warning("failed to persist kanban item for %s: %s", model_id, exc)

    async def _backlog_failed_load(self, model_id: str, role: str, reason: str) -> None:
        """Create a kanban item when a model load is refused or fails."""
        item = {
            "id": f"model-load-failed-{model_id}",
            "title": f"Failed to load model {model_id} for role {role}",
            "status": "backlog",
            "priority": "high",
            "source": "model_sprint_orchestrator",
            "category": "fleet_health",
            "notes": reason,
        }
        try:
            await asyncio.to_thread(persist_item, item)
        except Exception as exc:
            logger.warning("failed to persist kanban item for %s: %s", model_id, exc)


# ── Convenience entry points ────────────────────────────────────────────────


async def run_model_sprint(
    roles: list[str] | None = None,
    base_url: str = DEFAULT_BASE_URL,
    **kwargs: Any,
) -> list[SprintResult]:
    """One-shot ensure-resident for the given roles."""
    orchestrator = ModelSprintOrchestrator(base_url=base_url, **kwargs)
    return await orchestrator.run_sprint(roles)


async def poll_model_roster_forever(
    base_url: str = DEFAULT_BASE_URL,
    interval_s: float = 60.0,
    **kwargs: Any,
) -> None:
    """Daemon entry point: watch the live catalog and react to changes."""
    orchestrator = ModelSprintOrchestrator(base_url=base_url, **kwargs)
    await orchestrator.poll_forever(interval_s)
