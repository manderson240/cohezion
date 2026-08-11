#!/usr/bin/env -S uv run python
"""Run the OOM guard: pressure monitor -> OOMEvictor -> lemonade unload.

WHY THIS EXISTS. Every piece of this was already in the tree and NONE of it ran:
`OOMEvictor` had ZERO production consumers, so `install_oom_evictor()` was never called and
the evictor never saw a pressure event. Meanwhile this box repeatedly walked itself to
108 GB used / 14 GB available / 6.9 GB swapping — below the 16 GB N3 floor — because models
accumulate and nothing evicts them. `max_models` is a PER-CATEGORY count (6 x 7 categories),
and a count cannot bound bytes when models span 0.36 GB to 42.3 GB.

This is the ~40 lines of glue that turns a dormant safeguard into a running one.

    scripts/oom_guard.py                 # run until killed, 30s cadence
    scripts/oom_guard.py --once          # single evaluation, print state, exit
    scripts/oom_guard.py --interval 60

Verified 2026-07-29: the chain reclaims real memory (unloading Gemma-4-31B freed 20 GB).
The lister reads /api/v1/health -> all_models_loaded (NOT /api/v1/models, which is the
catalog — that bug made the evictor blind to 6 of 10 loaded models; see
tests/platform/test_oom_evictor_lister.py).
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path


REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "src"))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--interval", type=float, default=30.0, help="seconds between samples")
    ap.add_argument("--once", action="store_true", help="evaluate once and exit")
    ap.add_argument("--verbose", action="store_true")
    args = ap.parse_args()

    logging.basicConfig(
        level=logging.DEBUG if args.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
    )
    log = logging.getLogger("oom_guard")

    from cohezion.platform.oom_evictor import PressureDriver, _default_lister, install_oom_evictor

    evictor = install_oom_evictor()
    driver = PressureDriver()

    loaded = _default_lister()
    log.info(
        "OOM guard installed — %d managed model(s) evictable: %s",
        len(loaded),
        ", ".join(f"{m.model_id}(p{m.priority})" for m in loaded) or "none",
    )

    if args.once:
        level = driver.tick()
        log.info("pressure level: %s", level)
        for ev in evictor.evictions:
            log.info("eviction: %s succeeded=%s (%s)", ev.model_id, ev.succeeded, ev.reason)
        return 0

    log.info("running at %.0fs cadence — Ctrl-C to stop", args.interval)
    try:
        # stop=lambda: False runs forever; KeyboardInterrupt is the intended exit and is NOT
        # caught by the driver's per-tick handler (it catches Exception, and KeyboardInterrupt
        # derives from BaseException — so Ctrl-C propagates here as designed).
        driver.run(interval_s=args.interval, stop=lambda: False)
    except KeyboardInterrupt:
        log.info("stopped. %d eviction(s) this run:", len(evictor.evictions))
        for ev in evictor.evictions:
            log.info("  %s succeeded=%s (%s)", ev.model_id, ev.succeeded, ev.reason)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
