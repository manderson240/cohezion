"""ResidencyService — the owner that makes the residency gate real.

This module deliberately adds **no new policy**. ``hotswap.ensure_resident`` already
computes ``needed = weights + kv_overhead`` against ``free_gb() - floor``, refuses when it
does not fit, never evicts a busy or protected model, bounds every ``ctx_size`` (N3), and
verifies unloads by postcondition rather than status code. That gate is correct.

What it lacked was a caller. Measured 2026-08-03: ``ensure_resident`` had **zero**
production callers, and on the same day the box reached 113 GB used / 8 GB available with
lemonade's ``max_loaded_models`` count-cap holding perfectly at 2 — because the cap bounds
COUNT and nothing bounded SIZE. A correct gate that nothing invokes does not protect
anything.

So the whole of this module is: own the decision, expose one event entry point, and
delegate. Two rules keep it honest:

* **Every load and unload goes through the gate.** There is no bypass method.
* **Publishing is best-effort.** A dead bus must never turn a successful admission into a
  failure — the decision is the product, the event is the notification.
"""

from __future__ import annotations

import logging
from collections.abc import Callable, Mapping
from typing import Any

from cohezion.inference import hotswap
from cohezion.inference.residency_ledger import ResidencyLedger


logger = logging.getLogger(__name__)

EVENT_NEEDED = "model_needed"
EVENT_IDLE = "model_idle"
EVENT_ADMITTED = "model_admitted"
EVENT_REFUSED = "model_refused"


class ResidencyService:
    """Owns model residency. The only thing that should load or unload a model."""

    def __init__(
        self,
        *,
        ledger: ResidencyLedger | None = None,
        publish: Callable[[str, dict], None] | None = None,
        min_free_gb: float = hotswap.RAM_FLOOR_GB,
    ) -> None:
        self._ledger = ledger if ledger is not None else ResidencyLedger()
        self._publish = publish
        self._min_free_gb = min_free_gb

    # -------------------------------------------------------------- decisions
    def request(
        self,
        model_id: str,
        *,
        ctx_size: int = hotswap.MAX_CTX,
        protect: tuple[str, ...] = (),
    ) -> hotswap.SwapResult:
        """Admit ``model_id``, evicting LRU models if that is what it takes.

        A refusal is a successful outcome of the safety gate — callers should fall back to
        another lane, never retry into the same wall.
        """
        result = hotswap.ensure_resident(
            model_id,
            ctx_size=ctx_size,
            min_free_gb=self._min_free_gb,
            protect=protect,
            ledger=self._ledger,
        )
        logger.info(
            "residency: %s %s (%s)%s",
            "ADMIT" if result.ok else "REFUSE",
            model_id,
            result.reason,
            f" evicted={result.evicted}" if result.evicted else "",
        )
        return result

    def release(self, model_id: str) -> bool:
        """Explicitly free a model. Write-through happens on the verified postcondition."""
        freed = hotswap.unload(model_id)
        if freed:
            self._ledger.record_unload(model_id)
        return freed

    def reconcile(self):
        """Surface ledger-vs-server drift. Pure — repairing it is a separate decision."""
        return self._ledger.reconcile(hotswap.resident_models())

    def tick(
        self,
        *,
        pressure_gb: float | None = None,
        protect: tuple[str, ...] = (),
    ) -> dict[str, Any]:
        """One ambient pass: repair drift, then reclaim idle models under memory pressure.

        ``request()`` covers loading on demand. This is the missing other half: the router
        hoards up to ``max_loaded_models`` and never releases an idle model, which is how
        the box reached 113 GB used / 8 GB available with the count cap holding at 2.

        Releasing is gated on ACTUAL pressure. A tick that evicts a warm fleet when memory
        is plentiful is worse than no tick — it guarantees an immediate reload. Eviction is
        LRU-first and stops the moment pressure clears.

        Never raises: this runs on a timer, and one bad pass must not end the loop.
        """
        threshold = self._min_free_gb if pressure_gb is None else pressure_gb
        out: dict[str, Any] = {"released": [], "drift_repaired": False, "free_gb": None}
        try:
            server = hotswap.resident_models()
        except Exception as exc:  # health unreachable — report, do not crash the daemon
            out["error"] = str(exc)[:200]
            return out

        # Repair drift FIRST: a model loaded by something else is invisible to eviction
        # until the ledger knows about it (measured live: only_in_server=[...]).
        if server:
            before = {e["model_name"] for e in self._ledger.entries()}
            self._ledger.adopt(server)
            out["drift_repaired"] = {e["model_name"] for e in self._ledger.entries()} != before

        # Victims: least-recently-used first, never busy, never protected.
        victims = [
            m
            for m in reversed(server)
            if not m.get("is_busy") and m.get("model_name") not in protect
        ]
        for victim in victims:
            free = hotswap.free_gb_or_none()
            if free is None:
                # Unknown is NOT pressure: evicting on an unreadable meminfo would
                # tear down the whole non-protected fleet on a sensor failure.
                logger.warning("residency tick: memory state unreadable — abstaining")
                break
            if free >= threshold:
                break  # pressure cleared — stop, do not keep tearing down a warm fleet
            name = victim.get("model_name", "")
            try:
                if self.release(name):
                    out["released"].append(name)
            except Exception as exc:  # one bad unload must not end the pass
                logger.warning("residency tick: release %s failed: %s", name, exc)

        out["free_gb"] = round(hotswap.free_gb(), 1)
        if out["released"]:
            logger.info(
                "residency tick: reclaimed %s -> free %.1f GB",
                out["released"],
                out["free_gb"],
            )
            self._emit(EVENT_IDLE, {"released": out["released"], "free_gb": out["free_gb"]})
        return out

    # ----------------------------------------------------------------- events
    def handle_event(self, event: Mapping[str, Any]) -> Any:
        """Datamesh entry point. Returns the decision, or ``None`` if not ours.

        Malformed messages are ignored rather than raised: a daemon that dies on one bad
        message stops protecting the box against every subsequent good one.
        """
        kind = event.get("event_type")
        model_id = event.get("model_id")

        if kind == EVENT_NEEDED:
            if not model_id:
                logger.debug("residency: %s without model_id — ignoring", kind)
                return None
            result = self.request(
                model_id,
                ctx_size=int(event.get("ctx_size") or hotswap.MAX_CTX),
                protect=tuple(event.get("protect") or ()),
            )
            self._emit(
                EVENT_ADMITTED if result.ok else EVENT_REFUSED,
                {
                    "model_id": model_id,
                    "reason": result.reason,
                    "evicted": result.evicted,
                    "already_resident": result.already_resident,
                    "free_gb": round(hotswap.free_gb(), 1),
                },
            )
            return result

        if kind == EVENT_IDLE:
            if not model_id:
                return None
            return self.release(model_id)

        return None

    def _emit(self, event_type: str, payload: dict) -> None:
        """Best-effort notification. A broken sink must not corrupt the decision."""
        if self._publish is None:
            return
        try:
            self._publish(event_type, payload)
        except Exception as exc:  # a dead bus is not a gate failure
            logger.warning("residency: publish %s failed (ignored): %s", event_type, exc)
