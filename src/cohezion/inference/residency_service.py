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
