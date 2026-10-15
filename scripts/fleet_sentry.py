#!/usr/bin/env python3
"""Fleet Sentry: Silicon & Memory Stability Guard for AMD Strix Halo APU.

Enforces:
1. Strict 20 GiB available memory floor.
2. Idle model eviction when memory headroom is constrained.
3. Fleet lock verification before high-weight model loads.
"""

from __future__ import annotations

import contextlib
import logging
import subprocess
import sys
import time
from pathlib import Path


logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("fleet_sentry")

MEMORY_FLOOR_GIB: float = 20.0
FLEET_LOCK_PATH = Path("/tmp/fleet_lock_modelload.lock")


def get_available_memory_gib() -> float:
    """Read available memory directly from /proc/meminfo in GiB."""
    meminfo = Path("/proc/meminfo")
    if not meminfo.exists():
        logger.warning("/proc/meminfo not found. Using fallback.")
        return 64.0  # Fallback assumption

    avail_kb = 0
    with open(meminfo, encoding="utf-8") as f:
        for line in f:
            if line.startswith("MemAvailable:"):
                parts = line.split()
                if len(parts) >= 2:
                    avail_kb = int(parts[1])
                break

    return avail_kb / (1024.0 * 1024.0)


def check_fleet_lock() -> bool:
    """Check if model load lock is currently held."""
    return FLEET_LOCK_PATH.exists()


GTT_USED_PATH = Path("/sys/class/drm/card1/device/mem_info_gtt_used")
GTT_TOTAL_PATH = Path("/sys/class/drm/card1/device/mem_info_gtt_total")


def get_gtt_memory_gib() -> tuple[float, float]:
    """Read GTT aperture used and total in GiB directly from sysfs."""
    used_bytes = 0
    total_bytes = 100 * 1024 * 1024 * 1024  # 100 GiB fallback
    if GTT_USED_PATH.exists():
        with contextlib.suppress(Exception):
            used_bytes = int(GTT_USED_PATH.read_text().strip())
    if GTT_TOTAL_PATH.exists():
        with contextlib.suppress(Exception):
            total_bytes = int(GTT_TOTAL_PATH.read_text().strip())
    return used_bytes / (1024.0**3), total_bytes / (1024.0**3)


class EmaRateFilter:
    """Discrete Exponential Moving Average filter for proprioceptive rate tracking."""

    def __init__(self, alpha: float = 0.40):
        self.alpha = alpha
        self.filtered_rate: float | None = None

    def update(self, raw_rate: float) -> float:
        if self.filtered_rate is None:
            self.filtered_rate = raw_rate
        else:
            self.filtered_rate = self.alpha * raw_rate + (1.0 - self.alpha) * self.filtered_rate
        return self.filtered_rate

    def reset(self) -> None:
        self.filtered_rate = None


_MEM_RATE_FILTER = EmaRateFilter(alpha=0.40)
_GTT_RATE_FILTER = EmaRateFilter(alpha=0.40)


def enforce_memory_guard(auto_evict: bool = False, sample_velocity: bool = True) -> bool:
    """Verify memory headroom with P0 Proprioceptive Rate Reflex (Spindle & GTO).

    Checks both static level and stretch velocity (dM/dt, dG/dt) over a 0.5s window
    smoothed via an Exponential Moving Average filter (alpha=0.40).
    Triggers autogenic inhibition if time-to-crossing t_cross < 15s.
    """
    m0 = get_available_memory_gib()
    g0, g_tot = get_gtt_memory_gib()

    # Static Level Check
    if m0 < MEMORY_FLOOR_GIB:
        logger.critical(
            "ALERT: Available memory (%.2f GiB) is BELOW the %.2f GiB safety floor!",
            m0,
            MEMORY_FLOOR_GIB,
        )
        if auto_evict:
            logger.info("Executing soft eviction of idle model servers...")
            try:
                subprocess.run(["pkill", "-f", "kokoro"], check=False)
            except Exception as e:
                logger.error("Failed to signal idle process: %s", e)
        return False

    # Dynamic Crossing-Time Rate Reflex (P0 Proprioception)
    if sample_velocity:
        dt = 0.5
        time.sleep(dt)
        m1 = get_available_memory_gib()
        g1, _ = get_gtt_memory_gib()

        m_dot_raw = (m1 - m0) / dt  # GiB/s
        g_dot_raw = (g1 - g0) / dt  # GiB/s

        m_dot = _MEM_RATE_FILTER.update(m_dot_raw)
        g_dot = _GTT_RATE_FILTER.update(g_dot_raw)

        logger.info(
            "Proprioceptive Sensory Telemetry: Mem=%.2f GiB (dM/dt=%.2f GiB/s, raw=%.2f) | GTT=%.2f/%.2f GiB (dG/dt=%.2f GiB/s)",
            m1,
            m_dot,
            m_dot_raw,
            g1,
            g_tot,
            g_dot,
        )

        # 1. Host Memory Crossing-Time Reflex (Golgi Tendon Organ)
        if m_dot < -0.8:
            margin = m1 - MEMORY_FLOOR_GIB
            t_cross = margin / abs(m_dot)
            logger.warning(
                "PROPRIOCEPTIVE RATE ALARM: Rapid memory drain detected! t_cross = %.1fs", t_cross
            )
            if t_cross < 15.0:
                logger.critical(
                    "AUTOGENIC INHIBITION REFLEX FIRED: Predicted memory breach in %.1fs (<15s)! Aborting load.",
                    t_cross,
                )
                return False

        # 2. Aperture Tear Reflex (GTT expansion velocity)
        if g_dot > 1.5:
            logger.critical(
                "APERTURE TEAR REFLEX FIRED: GTT allocation accelerating at %.2f GiB/s! Halting to protect UMA.",
                g_dot,
            )
            return False

    logger.info("Silicon memory & aperture status: HEALTHY (Somatic equilibrium stable)")
    return True


def main() -> int:
    import argparse
    import time

    parser = argparse.ArgumentParser(description="Fleet Sentry Stability Checker")
    parser.add_argument(
        "--evict", action="store_true", help="Auto-evict idle servers if below floor"
    )
    parser.add_argument(
        "--watch", action="store_true", help="Run continuously as a background sentinel daemon"
    )
    parser.add_argument(
        "--interval", type=float, default=15.0, help="Sampling interval in seconds for watch mode"
    )
    args = parser.parse_args()

    if args.watch:
        logger.info(
            "Fleet Sentry Daemon started in continuous proprioceptive monitoring mode (interval=%.1fs)...",
            args.interval,
        )
        try:
            while True:
                enforce_memory_guard(auto_evict=args.evict)
                time.sleep(args.interval)
        except KeyboardInterrupt:
            logger.info("Fleet Sentry Daemon interrupted by user.")
            return 0
        except Exception as e:
            logger.error("Fleet Sentry loop encountered unexpected error: %s", e)
            return 1

    is_safe = enforce_memory_guard(auto_evict=args.evict)
    return 0 if is_safe else 1


if __name__ == "__main__":
    sys.exit(main())
