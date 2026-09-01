"""Long-running resource guard: watch RAM headroom and audit heavy-model ctx_size hazards.

Entrypoint for `cohezion-resource-guard.service`
(`ExecStart=… -m cohezion.core.resource_management.session_monitor`).

Deliberately THIN. Policy lives in `cohezion.compound.oom_guard` (SAFE_CTX_LIMIT=16384,
HEAVY_THRESHOLD_GB=5.0, RAM_LOAD_BUFFER_GB=8.0); this module supplies only the loop, the logging
cadence and a clean shutdown, so the guard and the load-time checks cannot drift apart.

ONE exception, made explicit rather than silent: the alert threshold. `RAM_LOAD_BUFFER_GB` is 8.0,
but the documented N3 operational floor is 16 GB — two different quantities (see N3_FLOOR_GB below).
The monitor alerts on the stricter floor and reports the buffer alongside it.

Observability follows the 24/7 rule learned 2026-07-25: emit a COMPLETED-WORK line per poll, not a
bare heartbeat. `active (running)` is not evidence of work; a poll counter with real values is.
"""

from __future__ import annotations

import logging
import os
import pathlib
import signal
import sys
import time
from dataclasses import dataclass, field
from types import FrameType
from typing import TYPE_CHECKING

from cohezion.compound.oom_guard import (
    HEAVY_THRESHOLD_GB,
    RAM_LOAD_BUFFER_GB,
    SAFE_CTX_LIMIT,
    MemorySnapshot,
    audit_heavy_models,
    get_active_uma_gb,
)
from cohezion.platform.memory_pressure import PressureLevel, classify_pressure


if TYPE_CHECKING:
    from cohezion.platform.oom_evictor import OOMEvictor

logger = logging.getLogger("cohezion.resource_guard")

# N3 documents a 16 GB available-RAM floor, but oom_guard.RAM_LOAD_BUFFER_GB is 8.0. Those are two
# DIFFERENT quantities: the buffer is headroom to keep free *after* a load completes; the floor is the
# absolute operational limit below which no heavy load may start. The monitor alerts on the stricter
# floor and reports the buffer separately, rather than silently treating 8.0 as "the floor".
# Flagged for reconciliation — do not collapse these into one constant without deciding which is right.
N3_FLOOR_GB = float(os.environ.get("COHEZION_RESOURCE_FLOOR_GB", "16.0"))

POLL_SECONDS = float(os.environ.get("COHEZION_RESOURCE_POLL_S", "60"))
# Re-audit heavy-model ctx_size occasionally: a ctx_size=0 entry can reappear when lemond reloads
# recipe_options from download metadata (the 2026-06-13 regression), so a one-shot audit is not enough.
AUDIT_EVERY_N_POLLS = int(os.environ.get("COHEZION_RESOURCE_AUDIT_EVERY", "30"))

# The ACTUATOR thresholds (2026-08-31; hardened per adversarial review). The 08-31 freeze
# happened with this guard logging `below_floor:true` for 8+ consecutive polls while lemond
# loaded a 35B MoE into 10.4 GB of headroom — the floor warning had NO consumer. The guard
# actuates on a sustained breach: EVICT_AFTER_BREACHES consecutive polls, OR the same span
# of WALL-CLOCK time below floor (the 08-31 livelock stretched polls to ~18 min, so a
# poll-count debounce alone becomes ~54 min exactly when memory is tight), OR immediately
# when severity is critical (avail < 8 GB / swap >= 50% — no debounce inside the death
# band). After a pass the debounce is re-earned and a cooldown prevents a 60s-cadence
# unload-vs-reload war with production when the floor is held by non-fleet memory.
EVICT_AFTER_BREACHES = int(os.environ.get("COHEZION_RESOURCE_EVICT_AFTER_BREACHES", "3"))
ACTUATION_COOLDOWN_POLLS = int(os.environ.get("COHEZION_RESOURCE_ACTUATION_COOLDOWN", "3"))
EVICTOR_RETRY_POLLS = 30  # re-attempt a failed evictor build every N polls, never latch off
# FLM/NPU work-path probe cadence (~20 min at the 60s poll). 0 disables.
FLM_PROBE_EVERY_N_POLLS = int(os.environ.get("COHEZION_FLM_PROBE_EVERY", "20"))

_running = True


@dataclass
class GuardState:
    """Mutable across-poll state: breach debounce + cooldown + lazily-built evictor."""

    consecutive_breaches: int = 0
    breach_started_at: float | None = None
    cooldown_polls: int = 0
    evictor: OOMEvictor | None = None
    evictor_retry_countdown: int = field(default=0, repr=False)


_state = GuardState()


def _read_gtt_used_gb() -> float | None:
    """GTT bytes lent to the iGPU, from sysfs. None when unreadable (fail-soft).

    GTT is in NO standard counter — invisible to ps, RSS sums, cgroups, and the kernel's
    own OOM table (the 08-15 forensics' biggest miss was recording only available_gb).
    The sysfs attribute IS readable from agent shells even when /dev/kfd is not.
    """
    total = 0
    seen = False
    for p in sorted(pathlib.Path("/sys/class/drm").glob("card*/device/mem_info_gtt_used")):
        # Per-card try + SUM: GTT is "system RAM lent to GPUs" plural, and one unreadable
        # card must not blank the reading from the others (adversarial review, 2026-08-31).
        try:
            total += int(p.read_text().strip())
            seen = True
        except (OSError, ValueError):
            continue
    return total / (1024**3) if seen else None


def _read_swap_pct() -> float | None:
    """Swap used as a percentage of SwapTotal. None when unreadable or no swap."""
    try:
        info: dict[str, int] = {}
        for line in pathlib.Path("/proc/meminfo").read_text().splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                info[k.strip()] = int(v.split()[0])
        total = info.get("SwapTotal", 0)
        if total <= 0:
            return None
        return 100.0 * (total - info.get("SwapFree", 0)) / total
    except (OSError, ValueError, IndexError):
        return None


_SEVERITY = {
    PressureLevel.OK: "ok",
    PressureLevel.WARNING: "warn",
    PressureLevel.CRITICAL: "critical",
}


def _build_evictor() -> OOMEvictor | None:
    """Construct the fleet-backed evictor; None on failure (guard degrades to a watcher).

    Constructs DIRECTLY rather than via install_oom_evictor(): install also subscribes the
    evictor to the process-global pressure monitor, which in this process is dead wiring
    (the guard never calls monitor.evaluate()) and in any process that does evaluate would
    be a SECOND uncoordinated relief loop over the same fleet — the exact race
    PressureDriver's own docstring forbids. One trigger path per process.

    The lister gets a longer health budget than the 1.5s default: under genuine pressure
    the health endpoint blocks mid-load, and 1.5s is exactly the budget it cannot meet.
    """
    try:
        from cohezion.platform.oom_evictor import OOMEvictor, _default_lister, _default_unloader

        return OOMEvictor(
            lister=lambda: _default_lister(timeout_s=8.0),
            unloader=_default_unloader,
        )
    except Exception as e:  # a 24/7 guard must survive a missing actuator
        logger.warning("resource-guard: evictor unavailable (%s) — watching only", type(e).__name__)
        return None


def _get_evictor(state: GuardState) -> OOMEvictor | None:
    """Lazily build the evictor with retry — a transient failure must never latch the
    actuator off for the life of the service (that re-creates 'floor warning with no
    consumer' behind a flag). Retries every EVICTOR_RETRY_POLLS polls."""
    if state.evictor is not None:
        return state.evictor
    if state.evictor_retry_countdown > 0:
        state.evictor_retry_countdown -= 1
        return None
    state.evictor = _build_evictor()
    if state.evictor is None:
        state.evictor_retry_countdown = EVICTOR_RETRY_POLLS
    return state.evictor


def _uma_committed_gb() -> float | None:
    """Byte-aware UMA commitment from the live topology; None when unreadable.

    This is the production consumer of the byte-aware topology layer — the very metric
    that under-counted 15× on 08-15 (0.89 GB reported vs 13.9 GiB actual GTT) now lands
    in every poll record next to the sysfs GTT reading it should roughly track.
    """
    try:
        return round(get_active_uma_gb(timeout_s=2.0), 2)
    except Exception:
        return None


def _stop(signum: int, _frame: FrameType | None) -> None:
    global _running
    _running = False
    logger.info("resource-guard: signal %s received, shutting down", signum)


def poll_once(poll_index: int, state: GuardState | None = None) -> dict[str, object]:
    """One observation. Returns a record so a caller (or a test) can assert on real values.

    ``state`` carries the breach debounce counter and the evictor across polls; the module
    singleton is used when omitted (tests inject a fresh GuardState).
    """
    state = state if state is not None else _state
    snap = MemorySnapshot.capture()
    swap_pct = _read_swap_pct()
    gtt_gb = _read_gtt_used_gb()
    breach = snap.available_gb < N3_FLOOR_GB
    if breach:
        state.consecutive_breaches += 1
        if state.breach_started_at is None:
            state.breach_started_at = time.monotonic()
    else:
        state.consecutive_breaches = 0
        state.breach_started_at = None
    if state.cooldown_polls > 0:
        state.cooldown_polls -= 1
    severity = _SEVERITY[classify_pressure(snap.available_gb, swap_pct or 0.0)]
    record: dict[str, object] = {
        "poll": poll_index,
        "available_gb": round(snap.available_gb, 2),
        "used_gb": round(snap.used_gb, 2),
        "floor_gb": N3_FLOOR_GB,
        "load_buffer_gb": RAM_LOAD_BUFFER_GB,
        "below_floor": breach,
        "consecutive_breaches": state.consecutive_breaches,
        "severity": severity,
        "swap_used_pct": round(swap_pct, 2) if swap_pct is not None else None,
        "gtt_used_gb": round(gtt_gb, 2) if gtt_gb is not None else None,
        "uma_committed_gb": _uma_committed_gb(),
        "hazards": [],
        "evictions": [],
    }

    if breach:
        logger.warning(
            "RAM BELOW FLOOR: %.1f GB available < %.1f GB floor — do not load any heavy model",
            snap.available_gb,
            N3_FLOOR_GB,
        )

    # ACTUATOR (2026-08-31): a sustained floor breach gets relief, not just a log line.
    # Fires on: N consecutive breach polls, OR the same span of wall-clock time below
    # floor (poll starvation stretches the counter exactly when memory is tight), OR
    # immediately at critical severity. A post-pass cooldown + debounce reset prevent a
    # per-poll unload war when the floor is held by non-fleet memory (tmpfs/GTT).
    elapsed = time.monotonic() - state.breach_started_at if state.breach_started_at else 0.0
    should_act = (
        breach
        and state.cooldown_polls == 0
        and (
            state.consecutive_breaches >= EVICT_AFTER_BREACHES
            or severity == "critical"
            or elapsed >= EVICT_AFTER_BREACHES * POLL_SECONDS
        )
    )
    if should_act:
        evictor = _get_evictor(state)
        if evictor is not None:
            try:
                evs = evictor.evict_until_relieved(
                    snap.available_gb,
                    swap_pct or 0.0,
                    target_available_gb=N3_FLOOR_GB,
                )
            except Exception as e:  # actuator failure must not kill the guard
                logger.warning("resource-guard: eviction pass failed: %s", type(e).__name__)
            else:
                record["evictions"] = [e.model_id for e in evs]
                for e in evs:
                    logger.warning(
                        "resource-guard: evicted %s (succeeded=%s) to restore the %.0f GB floor",
                        e.model_id,
                        e.succeeded,
                        N3_FLOOR_GB,
                    )
            # Re-earn the debounce and cool down regardless of outcome: acting again on
            # the very next poll re-attacks a fleet production is actively reloading.
            state.consecutive_breaches = 0
            state.breach_started_at = time.monotonic() if breach else None
            state.cooldown_polls = ACTUATION_COOLDOWN_POLLS

    # ctx_size hazards are the actual N3 crasher: footprint tracks context, not parameter count.
    if poll_index % AUDIT_EVERY_N_POLLS == 0:
        try:
            audit = audit_heavy_models()
        except Exception as e:  # a monitor must never die on a probe failure
            logger.warning("resource-guard: heavy-model audit failed: %s", type(e).__name__)
        else:
            hazards = [m for m, ctx in audit.items() if ctx == 0]
            record["hazards"] = hazards
            for m in hazards:
                logger.error(
                    "OOM HAZARD: %s (>=%.0f GB) has ctx_size=0 — bound it to %d before any load",
                    m,
                    HEAVY_THRESHOLD_GB,
                    SAFE_CTX_LIMIT,
                )

    # FLM/NPU work-path liveness (2026-09-01): lemond's BackendWatchdog probes /api/tags
    # (metadata) — an amdxdna wedge answers it while inference hangs. A bounded 1-token
    # generation is the only honest NPU liveness signal. Runs AFTER the actuator so a
    # wedged probe (up to its timeout) never delays memory relief.
    if FLM_PROBE_EVERY_N_POLLS > 0 and poll_index % FLM_PROBE_EVERY_N_POLLS == 0:
        try:
            from cohezion.platform.flm_liveness import probe_flm_generation

            probe = probe_flm_generation()
        except Exception as e:  # a monitor must never die on a probe failure
            logger.warning("resource-guard: FLM liveness probe failed: %s", type(e).__name__)
        else:
            record["flm_liveness"] = probe.status
            if probe.status == "wedged":
                record["flm_wedge_detail"] = probe.detail

    # COMPLETED-WORK line, not a heartbeat: carries the observed values, so an idle-but-"healthy"
    # guard is visible as such rather than reading green.
    logger.info(
        'resource-guard poll: {"poll":%d,"available_gb":%.2f,"below_floor":%s,"breaches":%d,'
        '"severity":"%s","swap_pct":%s,"gtt_gb":%s,"hazards":%d,"evictions":%d}',
        poll_index,
        snap.available_gb,
        str(breach).lower(),
        state.consecutive_breaches,
        severity,
        f"{swap_pct:.1f}" if swap_pct is not None else "null",
        f"{gtt_gb:.1f}" if gtt_gb is not None else "null",
        len(record["hazards"]),  # type: ignore[arg-type]
        len(record["evictions"]),  # type: ignore[arg-type]
    )
    return record


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        stream=sys.stdout,
        format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    )
    signal.signal(signal.SIGTERM, _stop)
    signal.signal(signal.SIGINT, _stop)

    logger.info(
        "resource-guard starting: poll=%.0fs floor=%.1fGB audit_every=%d polls",
        POLL_SECONDS,
        N3_FLOOR_GB,
        AUDIT_EVERY_N_POLLS,
    )

    i = 0
    while _running:
        try:
            poll_once(i)
        except Exception as e:  # never let one bad poll kill a 24/7 guard
            logger.warning("resource-guard: poll %d failed: %s", i, type(e).__name__)
        i += 1
        # Sleep in short slices so SIGTERM is honoured promptly instead of after a full interval.
        slept = 0.0
        while _running and slept < POLL_SECONDS:
            time.sleep(min(1.0, POLL_SECONDS - slept))
            slept += 1.0

    logger.info("resource-guard stopped after %d polls", i)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
