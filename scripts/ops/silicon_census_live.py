#!/usr/bin/env python3
"""Live un-mocked census of the Strix Halo silicon fleet via the OmniRouter.

Fixtures prove we parse the schema we *recorded*; only a live call proves we
parse the schema the server *emits today*. Run this after any lemonade upgrade
-- an `apt upgrade` has previously reset fleet state and moved the model store.

Usage:
    .venv/bin/python3 scripts/ops/silicon_census_live.py
"""

from __future__ import annotations

import json
import sys
import time
import urllib.request

from cohezion.inference.silicon_policy import plan_residency
from cohezion.inference.silicon_residency import parse_census


OMNI = "http://localhost:13305"
TIMEOUT = 10.0


def _get(path: str) -> dict:
    with urllib.request.urlopen(f"{OMNI}{path}", timeout=TIMEOUT) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


def _available_ram_gb() -> float:
    """Host RAM available right now, from /proc/meminfo (kB -> GB)."""
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except OSError:
        pass
    return 0.0


def main() -> int:
    try:
        health = _get("/api/v1/health")
        catalog = _get("/api/v1/models").get("data", [])
    except Exception as exc:  # report every failure mode plainly
        print(f"UNREACHABLE {OMNI}: {type(exc).__name__}: {exc}")
        return 2

    census = parse_census(health, catalog=catalog, checked_at=time.time())

    print(f"lemonade v{health.get('version')} -- {census.summary}\n")

    unparsed_devices = {m.name for m in census.residents if m.device == "unknown"}

    for device in ("npu", "igpu", "cpu", "unknown"):
        occ = census.occupancy(device)
        if occ.count == 0:
            continue
        state = "BUSY" if occ.busy else "idle"
        print(f"[{device:7s}] {occ.count} model(s)  {occ.resident_gb:6.2f} GB  {state}")
        for m in occ.models:
            flags = []
            if m.pinned:
                flags.append("PINNED")
            if m.in_flight:
                flags.append("IN-FLIGHT")
            if m.ctx_hazard:
                flags.append(f"CTX-HAZARD({m.ctx_size})")
            if m.watchdog_reset:
                flags.append("WATCHDOG-RESET")
            if not m.evictable:
                flags.append("protected")
            print(
                f"    {m.name:34s} {m.type:10s} {m.recipe:10s} "
                f"ctx={m.ctx_size!s:>6s} {m.size_gb:6.2f}GB "
                f"pool={m.slot_pool:20s} {' '.join(flags)}"
            )
        print()

    # Findings that matter for 24/7 operation.
    print("--- 24/7 signals ---")
    print(f"silicon loaded : {sorted(census.devices_loaded)}")
    print(f"silicon engaged: {sorted(census.devices_engaged) or '(all idle)'}")
    print(f"ctx hazards    : {[m.name for m in census.ctx_hazards] or 'none'}")
    print(f"watchdog resets: {[m.name for m in census.watchdog_resets] or 'none'}")
    print(f"unhealthy      : {[m.name for m in census.unhealthy] or 'none'}")
    print(f"reclaimable    : {sum(o.evictable_gb for o in census.by_device.values()):.2f} GB")

    # --- advisory residency plan (never applied here) ---
    available_gb = _available_ram_gb()
    plan = plan_residency(census, catalog=catalog, available_gb=available_gb)
    print(f"\n--- residency plan (advisory, host free={available_gb:.1f}GB) ---")
    print(plan.summary)
    for action in plan.actions:
        print(f"  {action}")
        print(f"      $ {action.as_command()}")
    for warning in plan.warnings:
        print(f"  WARN    {warning}")
    for refusal in plan.refused:
        print(f"  REFUSED {refusal}")

    if unparsed_devices:
        print(f"UNPARSED DEVICE: {sorted(unparsed_devices)} -- schema may have drifted")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
