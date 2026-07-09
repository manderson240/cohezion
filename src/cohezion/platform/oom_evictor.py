"""OOM eviction subscriber + pressure driver — the ACT half of event-driven OOM.

``memory_pressure`` is the *sense* half: it classifies memory/swap and emits an event on
each pressure-level transition. This module is the *act* half: an :class:`OOMEvictor`
subscribes to that event stream and, on a CRITICAL **rising** edge, unloads the
least-preferred loaded model — proactively reclaiming RAM *before* the next load attempt
would OOM, rather than refusing loads reactively at the gate (K1 / strix-halo rule 5).

A :class:`PressureDriver` calls ``monitor.evaluate()`` on a cadence so transitions fire
from real-memory sampling even when no load is attempted — without a driver, the monitor
only advances when something happens to call it.

Non-destructive: the evictor only unloads models supplied by its ``lister``; the default
lister returns ONLY models it can map to the fleet registry (so unknown/system processes
are never touched), and every external call is fail-soft.
"""

from __future__ import annotations

import logging
import time
from collections.abc import Callable, Iterable
from dataclasses import dataclass

from cohezion.platform.memory_pressure import (
    MemoryPressureEvent,
    MemoryPressureMonitor,
    PressureLevel,
    get_pressure_monitor,
)


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class LoadedModel:
    """A currently-loaded model. ``priority`` follows the registry convention: lower =
    preferred, so the HIGHEST priority number is the least-preferred eviction victim."""

    model_id: str
    priority: int = 100
    lane: str = ""


@dataclass(frozen=True)
class Eviction:
    model_id: str
    succeeded: bool
    reason: str
    timestamp: float


Lister = Callable[[], Iterable[LoadedModel]]
Unloader = Callable[[str], bool]


class OOMEvictor:
    """Unloads the least-preferred loaded model on a CRITICAL rising edge."""

    def __init__(self, lister: Lister, unloader: Unloader) -> None:
        self._lister = lister
        self._unloader = unloader
        self._evictions: list[Eviction] = []

    @property
    def evictions(self) -> list[Eviction]:
        return list(self._evictions)

    def on_event(self, event: MemoryPressureEvent) -> Eviction | None:
        """Subscriber handler. Acts ONLY on a CRITICAL *rising* transition.

        WARNING edges, relieved edges, and sustained-CRITICAL re-evaluations are all
        no-ops — the monitor already guarantees one event per transition, so reacting to
        ``rising and level==CRITICAL`` yields exactly one eviction per rising edge.
        """
        if event.level == PressureLevel.CRITICAL and event.rising:
            return self.evict_one()
        return None

    def evict_one(self) -> Eviction | None:
        """Unload the single least-preferred loaded model. Fail-soft throughout."""
        try:
            loaded = list(self._lister())
        except Exception as exc:  # a broken lister must not break the notify chain
            logger.warning("OOMEvictor: lister failed: %s", exc)
            return None
        if not loaded:
            return None
        victim = max(loaded, key=lambda m: m.priority)  # highest number = least preferred
        try:
            ok = bool(self._unloader(victim.model_id))
            reason = "unloaded" if ok else "unloader returned falsey"
        except Exception as exc:
            ok = False
            reason = f"unloader raised: {exc}"
            logger.warning("OOMEvictor: unloading %s failed: %s", victim.model_id, exc)
        ev = Eviction(model_id=victim.model_id, succeeded=ok, reason=reason, timestamp=time.time())
        self._evictions.append(ev)
        if ok:
            logger.info(
                "OOMEvictor: evicted %s (priority=%d) under CRITICAL pressure",
                victim.model_id,
                victim.priority,
            )
        return ev


class PressureDriver:
    """Periodically samples the monitor so pressure transitions fire without a load attempt."""

    def __init__(self, monitor: MemoryPressureMonitor | None = None) -> None:
        self._monitor = monitor if monitor is not None else get_pressure_monitor()

    def tick(self, *, snapshot: tuple[float, float] | None = None) -> PressureLevel:
        """One sample → classify → maybe-emit. Returns the (new) level."""
        return self._monitor.evaluate(snapshot=snapshot)

    def run(
        self,
        *,
        interval_s: float,
        stop: Callable[[], bool],
        sleep: Callable[[float], None] = time.sleep,
    ) -> int:
        """Tick until ``stop()`` is true. Returns the number of ticks performed.

        ``sleep`` is injectable so the loop is testable without real time. Fail-soft: a
        tick that raises is logged and the loop continues (a transient psutil error must
        not kill the background driver).
        """
        ticks = 0
        while not stop():
            try:
                self.tick()
            except Exception as exc:
                logger.warning("PressureDriver: tick failed: %s", exc)
            ticks += 1
            sleep(interval_s)
        return ticks


# ── default fleet-backed lister/unloader (fail-soft; only touch known fleet models) ──────
def _default_lister() -> list[LoadedModel]:
    """Loaded lemonade models mapped to registry priority. Returns ONLY known fleet models.

    Fail-soft: if lemonade is unreachable or the registry can't be read, returns []
    (the evictor becomes a no-op rather than guessing at unknown processes).
    """
    try:
        import httpx

        from cohezion.inference.registry import get_registry

        resp = httpx.get("http://localhost:13305/api/v1/models", timeout=1.5)
        resp.raise_for_status()
        loaded_ids = [m.get("id", "") for m in resp.json().get("data", [])]
        models = get_registry().models
        out: list[LoadedModel] = []
        for mid in loaded_ids:
            entry = models.get(mid)
            if entry is not None:  # never evict a model we don't manage
                out.append(LoadedModel(model_id=mid, priority=entry.priority, lane=str(entry.lane)))
        return out
    except Exception as exc:
        logger.debug("OOMEvictor default lister unavailable: %s", exc)
        return []


def _default_unloader(model_id: str) -> bool:
    """Unload a model via the lemonade CLI. Fail-soft: returns False on any error."""
    import subprocess

    try:
        r = subprocess.run(
            ["lemonade", "unload", model_id],
            capture_output=True,
            text=True,
            timeout=30,
        )
        return r.returncode == 0
    except Exception as exc:
        logger.warning("OOMEvictor default unloader failed for %s: %s", model_id, exc)
        return False


_installed: OOMEvictor | None = None


def install_oom_evictor(
    *,
    monitor: MemoryPressureMonitor | None = None,
    lister: Lister | None = None,
    unloader: Unloader | None = None,
) -> OOMEvictor:
    """Subscribe an :class:`OOMEvictor` to the pressure monitor and return it.

    Defaults wire the fleet-backed lister/unloader; tests inject fakes. Idempotent at the
    module level via the ``_installed`` reference (re-calls return a fresh evictor but the
    caller decides whether to keep one)."""
    global _installed
    mon = monitor if monitor is not None else get_pressure_monitor()
    evictor = OOMEvictor(
        lister=lister if lister is not None else _default_lister,
        unloader=unloader if unloader is not None else _default_unloader,
    )
    mon.subscribe(evictor.on_event)
    _installed = evictor
    return evictor
