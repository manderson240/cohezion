#!/usr/bin/env python3
"""24/7 silicon residency supervisor for the Strix Halo fleet.

Polls the Lemonade OmniRouter (:13305), derives residency transitions across
NPU / iGPU / CPU, and publishes them onto the Cohezion event bus.

Safety posture
--------------
* **Dry-run by default.** Mutating actions require `--apply`, and even then only
  `pin` (protective, trivially reversible) is applied. Loads and evictions are
  always left to an operator because this server is shared with live sessions.
* **Never crashes the loop.** A router outage emits a critical event and keeps
  polling; a supervisor that dies during an outage is useless precisely when
  it is needed.
* **The bus is STARTED before publishing.** `EventBus.publish_sync()` only
  enqueues, and the queue is drained solely by the processor task that
  `start()` launches. An earlier revision of this script published to an
  unstarted bus: every call returned True and delivered to nobody. That is why
  the loop is async and why publishing goes through
  `silicon_supervisor.publish_events`, which refuses an unstarted bus loudly.

Usage:
    .venv/bin/python3 scripts/ops/silicon_supervisor_daemon.py --once
    .venv/bin/python3 scripts/ops/silicon_supervisor_daemon.py --interval 60
    .venv/bin/python3 scripts/ops/silicon_supervisor_daemon.py --apply   # pins only
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import signal
import sys
import time
import urllib.error
import urllib.request
from typing import Any

from cohezion.inference.silicon_policy import DEFAULT_POLICY, plan_residency
from cohezion.inference.silicon_residency import SiliconCensus, parse_census
from cohezion.inference.silicon_supervisor import SiliconEvent, diff_census, publish_events


# :13305 is the OmniRouter and the only port that matters (harness N1). The
# override exists so outage-resilience can be exercised against a dead endpoint
# -- "the loop survives a router outage" is a claim that needs a test, and the
# only way to test it is to point the daemon somewhere that is genuinely down.
# lemonade's own CLI reads LEMONADE_HOST/LEMONADE_PORT, so this is idiomatic.
OMNI = os.environ.get("COHEZION_OMNI_URL", "http://localhost:13305")
TIMEOUT = float(os.environ.get("COHEZION_OMNI_TIMEOUT", "10.0"))

_running = True


def _stop(_signum: int, _frame: Any) -> None:
    global _running
    _running = False
    print("\n[supervisor] shutdown requested; finishing current cycle", flush=True)


def _get_blocking(path: str) -> dict[str, Any]:
    with urllib.request.urlopen(f"{OMNI}{path}", timeout=TIMEOUT) as resp:  # noqa: S310
        return json.loads(resp.read().decode())


async def _get(path: str) -> dict[str, Any]:
    """Off-thread HTTP so a slow router never stalls the bus processor task."""
    return await asyncio.to_thread(_get_blocking, path)


def _available_ram_gb() -> float:
    try:
        with open("/proc/meminfo") as fh:
            for line in fh:
                if line.startswith("MemAvailable:"):
                    return int(line.split()[1]) / (1024 * 1024)
    except OSError:
        pass
    return 0.0


async def _make_started_bus() -> tuple[Any | None, bool]:
    """Construct a STARTED EventBus with the data-mesh bridge attached.

    Returns (bus, mesh_attached).

    Two failure modes are deliberately distinguished, because an earlier
    revision hit both and reported neither:

      1. Publishing to an UNSTARTED bus. `publish_sync` returns True and
         increments `published` while the queue is never drained.
      2. Publishing to a started bus with NO SUBSCRIBERS. Measured live:
         `{'published': 5, 'delivered': 0}`. Events are accepted and dispatched
         to an empty handler list -- they reach nobody and persist nowhere.

    Fixing (1) alone leaves (2), which is why the DataMeshEventBridge is
    attached here: it is what actually persists events to SurrealDB.
    """
    try:
        from cohezion.core.event_bus import EventBus, EventType
    except Exception as exc:
        print(f"[supervisor] event bus unavailable ({exc}); console only", flush=True)
        return None, False

    bus = EventBus()
    await bus.start()

    mesh_attached = False
    try:
        from cohezion.data_mesh.event_bridge import make_event_bridge

        bridge = make_event_bridge()
        if bridge is not None:
            # Fleet residency events are not in the bridge's default type list;
            # subscribe it to them explicitly rather than widening its globals.
            bridge.subscribe(
                bus,
                extra_types=[
                    EventType.MODEL_LOADED,
                    EventType.MODEL_EVICTED,
                    EventType.MODEL_ROSTER_CHANGED,
                    EventType.SYSTEM_HEALTH,
                ],
            )
            mesh_attached = True
        else:
            print(
                "[supervisor] data mesh bridge unavailable (SurrealDB down?); "
                "events will be published but NOT persisted",
                flush=True,
            )
    except Exception as exc:
        print(f"[supervisor] data mesh bridge failed to attach: {exc}", flush=True)

    return bus, mesh_attached


async def _run_lemonade(args: list[str], label: str) -> bool:
    """Run a lemonade CLI command, reporting outcome. Never raises."""
    try:
        proc = await asyncio.create_subprocess_exec(
            "lemonade",
            *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        out, err = await asyncio.wait_for(proc.communicate(), timeout=300)
        ok = proc.returncode == 0
        detail = (err or out).decode(errors="replace").strip()[:160]
        print(
            f"    APPLIED {label}: {'ok' if ok else f'rc={proc.returncode}'} {detail}",
            flush=True,
        )
        return ok
    except Exception as exc:
        print(f"    {label} FAILED: {exc}", flush=True)
        return False


async def _apply_plan(plan: Any, apply_pins: bool, heal: bool, quiet: bool = False) -> None:
    """Apply the advisory plan, subject to two independent opt-in gates.

    The gates are asymmetric on purpose, and the asymmetry is the safety
    property: this supervisor can RESTORE starved silicon but can never take
    anything away.

      --apply   pin actions. Protective and reversible (`lemonade unpin`).
      --heal    load actions ONLY. Restores a tier the policy says should be
                resident, and only when `plan_residency` already proved the
                byte budget allows it (a load that would breach the RAM
                reserve never reaches this function -- it is `refused`).

    Eviction is deliberately NOT applicable at any flag level. Loading a
    missing model is additive and self-limiting; evicting one destroys warm
    state that another session may be mid-request against, and on a shared
    server that is not a decision a daemon should make unattended.
    """
    for action in plan.of("pin"):
        if not apply_pins:
            if not quiet:
                print(f"    DRY-RUN would run: {action.as_command()}", flush=True)
            continue
        await _run_lemonade(["pin", action.model], f"pin {action.model}")

    for action in plan.of("load"):
        if not heal:
            if not quiet:
                print(f"    ADVISORY (needs --heal): {action.as_command()}", flush=True)
            continue
        await _run_lemonade(
            ["load", action.model, "--ctx-size", str(action.ctx_size)],
            f"load {action.model} on {action.device}",
        )


async def cycle(
    previous: SiliconCensus | None,
    bus: Any | None,
    apply_changes: bool,
    quiet: bool,
    was_down: bool = False,
    heal: bool = False,
) -> tuple[SiliconCensus | None, bool]:
    """One supervision cycle. Returns (census, router_is_down).

    On outage the previous census is kept as the diff baseline, so recovery
    reports the models that actually changed during the outage rather than
    replaying the whole fleet as newly loaded.
    """
    stamp = time.strftime("%H:%M:%S")
    try:
        health = await _get("/api/v1/health")
        catalog = (await _get("/api/v1/models")).get("data", [])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        # Emit on the EDGE, not every poll. A 24/7 outage polled at 45s would
        # otherwise produce ~1900 identical CRITICALs a day, burying every
        # other event -- the same flooding bug already fixed for
        # `backend_unhealthy`, which recurred here because the outage path
        # lives in the daemon rather than in diff_census().
        if not was_down:
            outage = SiliconEvent(
                kind="router_unreachable",
                detail=f"{type(exc).__name__}: {exc}",
                at=time.time(),
            )
            print(f"[{stamp}] {outage}", flush=True)
            await publish_events(bus, [outage])
        else:
            print(f"[{stamp}] (router still down: {type(exc).__name__})", flush=True)
        return previous, True

    if was_down:
        recovered = SiliconEvent(
            kind="router_recovered",
            detail=f"{OMNI} responding again",
            at=time.time(),
        )
        print(f"[{stamp}] {recovered}", flush=True)
        await publish_events(bus, [recovered])

    census = parse_census(health, catalog=catalog, checked_at=time.time())
    events = diff_census(previous, census)

    for event in events:
        print(f"[{stamp}] {event}", flush=True)
    accepted = await publish_events(bus, events)
    if events:
        # "accepted", not "delivered": publish_events counts what the bus took,
        # which is not the same as what a subscriber received. The bus's own
        # `delivered` metric is the authority and is printed at shutdown.
        print(f"[{stamp}] bus: {accepted}/{len(events)} event(s) accepted", flush=True)

    # The plan is ALWAYS computed and applied. `--quiet` controls REPORTING
    # only. An earlier revision nested both under `if not quiet:`, so --quiet
    # silently disabled --apply and --heal while run() still announced
    # mode=APPLY(pins+heal) -- and --quiet is the natural flag for a
    # journal-friendly 24/7 unit, i.e. exactly where the gates matter most.
    plan = plan_residency(
        census,
        policy=DEFAULT_POLICY,
        catalog=catalog,
        available_gb=_available_ram_gb(),
    )
    if not quiet:
        print(f"[{stamp}] {census.summary} | {plan.summary}", flush=True)
        for warning in plan.warnings:
            print(f"    WARN    {warning}", flush=True)
        for refusal in plan.refused:
            print(f"    REFUSED {refusal}", flush=True)
    if plan.actions:
        await _apply_plan(plan, apply_pins=apply_changes, heal=heal, quiet=quiet)

    return census, False


async def run(args: argparse.Namespace) -> int:
    bus, mesh_attached = await _make_started_bus()
    gates = [g for g, on in (("pins", args.apply), ("heal", args.heal)) if on]
    mode = f"APPLY({'+'.join(gates)})" if gates else "DRY-RUN"
    if bus is None:
        bus_state = "none"
    elif mesh_attached:
        bus_state = "started+mesh"
    else:
        bus_state = "started(NO SUBSCRIBERS - events reach nobody)"
    print(
        f"[supervisor] watching {OMNI} every {args.interval:g}s mode={mode} bus={bus_state}",
        flush=True,
    )

    previous: SiliconCensus | None = None
    was_down = False
    cycles = 0
    try:
        while _running:
            previous, was_down = await cycle(
                previous, bus, args.apply, args.quiet, was_down, args.heal
            )
            cycles += 1
            if args.once or (args.max_cycles and cycles >= args.max_cycles):
                break
            slept = 0.0
            while _running and slept < args.interval:
                await asyncio.sleep(min(0.5, args.interval - slept))
                slept += 0.5
    finally:
        if bus is not None:
            try:
                await asyncio.wait_for(bus.stop(), timeout=5)
            except Exception as exc:
                print(f"[supervisor] bus stop failed: {exc}", flush=True)

    print(f"[supervisor] stopped after {cycles} cycle(s)", flush=True)
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--interval", type=float, default=30.0, help="seconds between polls")
    parser.add_argument("--once", action="store_true", help="single cycle then exit")
    parser.add_argument("--max-cycles", type=int, default=0, help="0 = unbounded")
    parser.add_argument(
        "--apply",
        action="store_true",
        help="apply protective PIN actions (reversible via `lemonade unpin`)",
    )
    parser.add_argument(
        "--heal",
        action="store_true",
        help=(
            "apply LOAD actions to restore starved silicon -- additive only, and "
            "only within the byte budget. Eviction is never applied at any flag level."
        ),
    )
    parser.add_argument("--quiet", action="store_true", help="events only, no plan")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _stop)
    signal.signal(signal.SIGTERM, _stop)
    return asyncio.run(run(args))


if __name__ == "__main__":
    sys.exit(main())
