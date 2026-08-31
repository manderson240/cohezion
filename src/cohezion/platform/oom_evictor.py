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
    WARNING_AVAIL_GB,
    MemoryPressureEvent,
    MemoryPressureMonitor,
    PressureLevel,
    classify_pressure,
    get_pressure_monitor,
)
from cohezion.platform.resource_manager import SWAP_PRESSURE_PCT, _read_system_memory


logger = logging.getLogger(__name__)

# Relief loop bounds (2026-08-31 rebuild of the lost agent-1786851059 fix).
# MIN_RELIEF_GB encodes the 08-15 incident's own lesson: an unload that buys nothing is
# evidence the fleet is NOT the memory holder (unmapped tmpfs / GTT held the 45 GB that
# night), so shredding the rest of it repeats the kernel's mistake of killing victims that
# free nothing. MAX_EVICTIONS_PER_EMERGENCY bounds a genuinely-relieving cascade.
# Adversarial-review hardening (2026-08-31): one no-relief reading cannot distinguish
# "unload freed nothing" from "something ate what it freed" during a concurrent-allocation
# cascade — so the loop breaks only on TWO consecutive no-relief evictions. Relief also
# counts a swap-pressure drop (MIN_SWAP_RELIEF_PCT), because a swap-driven emergency can
# be genuinely relieved without MemAvailable moving. A wall-clock deadline bounds the pass
# so a slow-but-succeeding unload cascade cannot starve the caller's loop (SIGTERM budget).
MIN_RELIEF_GB = 0.25
MIN_SWAP_RELIEF_PCT = 0.5
NO_RELIEF_STRIKES = 2
MAX_EVICTIONS_PER_EMERGENCY = 6
DEFAULT_PASS_DEADLINE_S = 45.0


@dataclass(frozen=True)
class LoadedModel:
    """A currently-loaded model. ``priority`` follows the registry convention: lower =
    preferred, so the HIGHEST priority number is the least-preferred eviction victim.
    ``size_gb`` is a TIE-BREAK only: among equal-priority victims the largest goes first
    (the 08-15 evictor freed a 0.38 GB model while a 23.3 GB sibling stayed resident)."""

    model_id: str
    priority: int = 100
    lane: str = ""
    size_gb: float = 0.0


@dataclass(frozen=True)
class Eviction:
    model_id: str
    succeeded: bool
    reason: str
    timestamp: float


Lister = Callable[[], Iterable[LoadedModel]]
Unloader = Callable[[str], bool]
Measure = Callable[[], tuple[float, float] | None]


class OOMEvictor:
    """Unloads least-preferred loaded models under pressure, re-measuring between unloads.

    ``measure`` returns a fresh ``(available_gb, swap_pct)`` reading (None when memory
    can't be read); defaults to the same psutil read the pressure monitor uses. Injectable
    so the relief loop is testable without real memory state.
    """

    def __init__(self, lister: Lister, unloader: Unloader, measure: Measure | None = None) -> None:
        self._lister = lister
        self._unloader = unloader
        self._measure: Measure = measure if measure is not None else _read_system_memory
        self._evictions: list[Eviction] = []

    @property
    def evictions(self) -> list[Eviction]:
        return list(self._evictions)

    def on_event(self, event: MemoryPressureEvent) -> Eviction | None:
        """Subscriber handler. Acts ONLY on a CRITICAL *rising* transition.

        Seeds the relief loop with the EVENT'S OWN readings, never a fresh read: the
        monitor accepts injected snapshots (``PressureDriver.tick(snapshot=...)``), so
        re-reading here would second-guess the caller that classified the emergency.
        Returns the first eviction (or None) to preserve the original handler contract.
        """
        if event.level == PressureLevel.CRITICAL and event.rising:
            # Target the WARNING floor, not merely non-CRITICAL: the 08-31 freeze happened
            # at ~10.4 GB available — ABOVE the 8 GB CRITICAL line. Relieving only to
            # "not critical" would deliberately stop inside the known freeze band.
            evs = self.evict_until_relieved(
                event.available_gb, event.swap_pct, target_available_gb=WARNING_AVAIL_GB
            )
            return evs[0] if evs else None
        return None

    def evict_until_relieved(
        self,
        available_gb: float,
        swap_pct: float,
        *,
        target_available_gb: float | None = None,
        deadline_s: float | None = DEFAULT_PASS_DEADLINE_S,
    ) -> list[Eviction]:
        """Evict least-preferred models until pressure clears, re-measuring between unloads.

        Seeded with the caller's reading; stops on the FIRST of:
          - pressure cleared (with ``target_available_gb``: available >= target and swap
            below the rule-5 precursor; without: level is no longer CRITICAL),
          - relief from the last unload < MIN_RELIEF_GB (the fleet is not the culprit),
          - an unload failed,
          - victims exhausted (already-tried victims are skipped — /api/v1/health can lag
            an unload, so the lister is not trusted to shrink),
          - measurement unavailable (cannot verify relief -> conservative single step),
          - MAX_EVICTIONS_PER_EMERGENCY reached.

        The single-shot ``on_event`` predecessor performed exactly one eviction per
        emergency ever — measured 08-15 as ~one 0.38 GB eviction per 18 minutes while the
        box died. The 08-31 freeze happened at ~10.4 GB available (the WARNING band), so
        callers guarding an operational floor pass it as ``target_available_gb``.
        """
        evs: list[Eviction] = []
        tried: set[str] = set()
        avail, swap = available_gb, swap_pct
        no_relief_strikes = 0
        started = time.monotonic()

        while len(evs) < MAX_EVICTIONS_PER_EMERGENCY:
            if self._relieved(avail, swap, target_available_gb):
                break
            if deadline_s is not None and time.monotonic() - started > deadline_s:
                logger.warning(
                    "OOMEvictor: eviction pass exceeded %.0fs deadline after %d "
                    "eviction(s) — yielding to the caller's loop",
                    deadline_s,
                    len(evs),
                )
                break
            try:
                candidates = [m for m in self._lister() if m.model_id not in tried]
            except Exception as exc:  # a broken lister must not break the notify chain
                logger.warning("OOMEvictor: lister failed: %s", exc)
                break
            if not candidates:
                if not evs:
                    # The actuator is BLIND, not idle: under genuine pressure the health
                    # endpoint blocks mid-load, and a silent no-op here is exactly the
                    # 'watcher with no actuator' failure this loop exists to end.
                    logger.warning(
                        "OOMEvictor: pressure present but no evictable candidates "
                        "(health blocked/unreachable, or fleet empty/all busy)"
                    )
                break
            victim = self._pick_victim(candidates)
            tried.add(victim.model_id)
            ev = self._evict(victim)
            evs.append(ev)
            if not ev.succeeded:
                break
            snap = self._safe_measure()
            if snap is None:
                break
            new_avail, new_swap = snap
            ram_relief = new_avail - avail
            swap_relief = swap - new_swap
            avail, swap = new_avail, new_swap
            if ram_relief >= MIN_RELIEF_GB or swap_relief >= MIN_SWAP_RELIEF_PCT:
                no_relief_strikes = 0
                continue
            no_relief_strikes += 1
            if no_relief_strikes >= NO_RELIEF_STRIKES:
                logger.warning(
                    "OOMEvictor: %d consecutive evictions freed <%.2f GB each "
                    "(last: %s, %.2f GB) — fleet is not the memory holder, "
                    "stopping the eviction cascade",
                    no_relief_strikes,
                    MIN_RELIEF_GB,
                    victim.model_id,
                    ram_relief,
                )
                break
        return evs

    @staticmethod
    def _relieved(avail: float, swap: float, target_available_gb: float | None) -> bool:
        if target_available_gb is not None:
            return avail >= target_available_gb and swap < SWAP_PRESSURE_PCT
        return classify_pressure(avail, swap) is not PressureLevel.CRITICAL

    @staticmethod
    def _pick_victim(candidates: list[LoadedModel]) -> LoadedModel:
        # Priority leads (highest number = least preferred); size_gb breaks ties so an
        # equal-preference 23.3 GB model goes before its 0.38 GB sibling. A NaN size
        # (m.size_gb != m.size_gb) would make every comparison False and let an unknown
        # model win ties arbitrarily — treat it as smallest instead.
        return max(
            candidates,
            key=lambda m: (m.priority, m.size_gb if m.size_gb == m.size_gb else float("-inf")),
        )

    def _safe_measure(self) -> tuple[float, float] | None:
        try:
            return self._measure()
        except Exception as exc:
            logger.warning("OOMEvictor: measurement failed: %s", exc)
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
        return self._evict(self._pick_victim(loaded))

    def _evict(self, victim: LoadedModel) -> Eviction:
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
                "OOMEvictor: evicted %s (priority=%d, %.1f GB) under memory pressure",
                victim.model_id,
                victim.priority,
                victim.size_gb,
            )
        return ev


class PressureDriver:
    """Periodically samples the monitor so pressure transitions fire without a load attempt."""

    def __init__(
        self,
        monitor: MemoryPressureMonitor | None = None,
        *,
        on_tick: Callable[[], None] | None = None,
    ) -> None:
        """``on_tick`` runs once per loop iteration, after the pressure sample.

        This is the seam for the AMBIENT residency pass (`ResidencyService.tick`). This
        driver is pressure-driven — it reacts to a CRITICAL rising edge — and has no
        demand-driven half; RS6 supplies it. Joining this loop rather than starting a second
        timer is deliberate: two independent eviction loops over one fleet can race, both
        reading residency and both choosing an LRU victim to unload.
        """
        self._monitor = monitor if monitor is not None else get_pressure_monitor()
        self._on_tick = on_tick

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
            if self._on_tick is not None:
                # Isolated from the pressure sample above: a residency pass that throws
                # (health unreachable, an unload 500) must neither kill the loop nor
                # suppress the pre-existing sampling job.
                try:
                    self._on_tick()
                except Exception as exc:
                    logger.warning("PressureDriver: on_tick failed: %s", exc)
            ticks += 1
            sleep(interval_s)
        return ticks


# ── default fleet-backed lister/unloader (fail-soft; only touch known fleet models) ──────
def _default_lister(timeout_s: float = 1.5) -> list[LoadedModel]:
    """Loaded lemonade models mapped to registry priority. Returns ONLY known fleet models.

    SOURCE OF TRUTH IS ``/api/v1/health`` -> ``all_models_loaded``, NOT ``/api/v1/models``.
    The latter is the CATALOG of everything available (131 entries on this fleet); reading it
    as "loaded" broke the evictor in both directions, measured live 2026-07-29:

      PHANTOMS  reported Gemma-4-31B and deepseek-r1-0528-8b-FLM as loaded when they were not
                -> the evictor spends its one eviction on a model holding ZERO bytes
      BLIND     missed 6 of 10 truly-loaded models (incl. SD-Turbo, Whisper, kokoro)
                -> their RAM could never be reclaimed, which is exactly the accumulation
                   that drove this box to 108GB used / 14GB free with 6.9GB swapping

    This survived because the module had ZERO production consumers: the lister was never
    exercised against a real server. Regression cover: tests/platform/test_oom_evictor_lister.py

    Fail-soft: if lemonade is unreachable or the registry can't be read, returns []
    (the evictor becomes a no-op rather than guessing at unknown processes).
    """
    try:
        from cohezion.compound.oom_guard import (
            MODEL_FOOTPRINT_GB,
            _catalog_sizes,
            _resolve_footprint_gb,
            fetch_loaded_models,
        )
        from cohezion.inference.registry import get_registry

        loaded = fetch_loaded_models(timeout_s=timeout_s)
        if loaded is None:
            # Not "fleet empty" — CANNOT SEE. The health endpoint blocks during model
            # load/unload, i.e. exactly when eviction is most needed. Be loud so a blind
            # actuator is distinguishable from an idle one in the journal.
            logger.warning(
                "OOMEvictor lister blind: /api/v1/health unreachable or blocked "
                "(timeout %.1fs) — no eviction candidates this pass",
                timeout_s,
            )
            return []
        models = get_registry().models
        # One batch catalog fetch covers every managed loaded model absent from the
        # curated table; per-model lookups inside an emergency pass were worst-case
        # ~2s each x N models x 6 loop iterations against an already-busy router.
        names = [str(m.get("model_name", "")) for m in loaded]
        catalog = (
            _catalog_sizes(timeout_s=timeout_s)
            if any(n in models and n not in MODEL_FOOTPRINT_GB for n in names)
            else {}
        )
        out: list[LoadedModel] = []
        busy_skipped = 0
        for m in loaded:
            mid = str(m.get("model_name", ""))
            entry = models.get(mid)
            if entry is None:  # never evict a model we don't manage
                continue
            if m.get("is_busy") or m.get("is_streaming"):
                # Unloading a backend mid-inference kills the in-flight production
                # request — and _pick_victim prefers the LARGEST model, which is the
                # one most likely to be mid-generation. Skip busy backends this pass.
                busy_skipped += 1
                continue
            # size_gb powers the equal-priority tie-break; the registry's ModelEntry
            # has NO size field, so without this lookup the tie-break is dormant.
            out.append(
                LoadedModel(
                    model_id=mid,
                    priority=entry.priority,
                    lane=str(entry.lane),
                    size_gb=_resolve_footprint_gb(mid, catalog_sizes=catalog),
                )
            )
        if busy_skipped and not out:
            logger.warning(
                "OOMEvictor lister: all %d managed loaded model(s) are busy — "
                "standing down this pass rather than killing in-flight work",
                busy_skipped,
            )
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
