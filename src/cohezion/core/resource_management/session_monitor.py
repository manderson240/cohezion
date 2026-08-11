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
import signal
import sys
import time
from types import FrameType

from cohezion.compound.oom_guard import (
    HEAVY_THRESHOLD_GB,
    RAM_LOAD_BUFFER_GB,
    SAFE_CTX_LIMIT,
    MemorySnapshot,
    audit_heavy_models,
)

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

_running = True


def _stop(signum: int, _frame: FrameType | None) -> None:  # noqa: ARG001
    global _running
    _running = False
    logger.info("resource-guard: signal %s received, shutting down", signum)


def poll_once(poll_index: int) -> dict[str, object]:
    """One observation. Returns a record so a caller (or a test) can assert on real values."""
    snap = MemorySnapshot.capture()
    breach = snap.available_gb < N3_FLOOR_GB
    record: dict[str, object] = {
        "poll": poll_index,
        "available_gb": round(snap.available_gb, 2),
        "used_gb": round(snap.used_gb, 2),
        "floor_gb": N3_FLOOR_GB,
        "load_buffer_gb": RAM_LOAD_BUFFER_GB,
        "below_floor": breach,
        "hazards": [],
    }

    if breach:
        logger.warning(
            "RAM BELOW FLOOR: %.1f GB available < %.1f GB floor — do not load any heavy model",
            snap.available_gb,
            N3_FLOOR_GB,
        )

    # ctx_size hazards are the actual N3 crasher: footprint tracks context, not parameter count.
    if poll_index % AUDIT_EVERY_N_POLLS == 0:
        try:
            audit = audit_heavy_models()
        except Exception as e:  # noqa: BLE001 — a monitor must never die on a probe failure
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

    # COMPLETED-WORK line, not a heartbeat: carries the observed values, so an idle-but-"healthy"
    # guard is visible as such rather than reading green.
    logger.info(
        'resource-guard poll: {"poll":%d,"available_gb":%.2f,"below_floor":%s,"hazards":%d}',
        poll_index,
        snap.available_gb,
        str(breach).lower(),
        len(record["hazards"]),  # type: ignore[arg-type]
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
        except Exception as e:  # noqa: BLE001 — never let one bad poll kill a 24/7 guard
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
