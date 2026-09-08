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
from typing import Any, NamedTuple

from cohezion.inference.silicon_policy import DEFAULT_POLICY, plan_residency
from cohezion.inference.silicon_residency import (
    ModelStorage,
    SiliconCensus,
    parse_census,
    parse_storage,
)
from cohezion.inference.silicon_supervisor import (
    SiliconEvent,
    diff_census,
    diff_storage,
    next_storage_baseline,
    publish_events,
    stall_events,
)


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


class CycleState(NamedTuple):
    """State carried from one supervision cycle to the next.

    A named record rather than a growing tuple because these five fields are
    THREE independent failure axes plus two baselines, and every one of them was
    added to fix a specific misreport:

      census / storage  Diff baselines. Kept across a gap so recovery reports
                        what actually changed instead of replaying the whole
                        fleet as newly loaded.
      router_down       The router is genuinely unreachable.
      census_stalled    The router is UP but /health and /models are blocked.
                        Conflating this with router_down pages a human every
                        time the fleet gets busy.
      blind             The last reading carried no model_storage block. Held
                        separately from `storage` precisely so a blind cycle
                        cannot overwrite the capacity baseline -- that
                        overwrite is what stranded a critical incident open
                        across `critical -> blind -> ok`.
    """

    census: SiliconCensus | None = None
    router_down: bool = False
    storage: ModelStorage | None = None  # last MEASURED reading, never a blind one
    census_stalled: bool = False
    blind: bool = False
    # Consecutive stalled polls. A count, not a flag, because duration is the
    # only thing that separates a busy fleet from a dead census -- the measured
    # stall cleared within one probe round, a dead backend never would.
    stall_polls: int = 0


async def cycle(
    state: CycleState,
    bus: Any | None,
    apply_changes: bool,
    quiet: bool,
    heal: bool = False,
) -> CycleState:
    """One supervision cycle. Returns the state to carry into the next."""
    previous = state.census
    previous_storage = state.storage
    was_down = state.router_down
    census_stalled = state.census_stalled
    was_blind = state.blind
    stamp = time.strftime("%H:%M:%S")

    # LIVENESS IS PROBED WITH THE CHEAP ENDPOINT, DELIBERATELY.
    #
    # Measured 2026-08-30: /api/v1/health and /api/v1/models intermittently
    # block for 20s+ (two of three probes) while /api/v1/system-info answered in
    # ~3ms every time. Both of the blocking endpoints enumerate loaded models
    # and contend with whatever lock a busy backend holds; system-info reads
    # static device state and does not.
    #
    # The naive daemon polls /health, times out, and reports the router down --
    # a CRITICAL page every time the fleet gets busy, which is the same
    # false-positive class as diagnosing a saturated router as a wedged one.
    # Probing the endpoint that does not share the lock makes
    # `router_unreachable` mean what it says.
    try:
        system_info = await _get("/api/v1/system-info")
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
        # Every baseline and flag is carried through untouched: an outage tells
        # us nothing new about capacity or the census, so it must not reset
        # what we knew before it started.
        return state._replace(router_down=True)

    if was_down:
        recovered = SiliconEvent(
            kind="router_recovered",
            detail=f"{OMNI} responding again",
            at=time.time(),
        )
        print(f"[{stamp}] {recovered}", flush=True)
        await publish_events(bus, [recovered])

    now = time.time()
    storage = parse_storage(system_info)
    # The baseline handed to the NEXT cycle is the last MEASURED storage, never
    # a blind reading. `critical -> blind -> ok` must compare `ok` against the
    # retained `critical`, or the incident is stranded open forever. The rule
    # lives in the supervisor module so it is tested next to the diff it pairs
    # with; the two are only correct together.
    next_storage = next_storage_baseline(previous_storage, storage)
    next_blind = not storage.measured

    # The census endpoints are fetched SEPARATELY from the liveness probe above,
    # so that their known 20s+ stalls degrade observability without being
    # mistaken for an outage -- and, importantly, without taking capacity
    # monitoring down with them. Storage comes from the endpoint that does not
    # block, so the store guard keeps working through a census stall. That is
    # not incidental: a stall means the fleet is BUSY, which is exactly when a
    # download is most likely to be starting.
    try:
        health = await _get("/api/v1/health")
        catalog = (await _get("/api/v1/models")).get("data", [])
    except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
        # Count the stall, then let the supervisor decide what (if anything) it
        # is worth saying. Edge-triggered twice: once when it starts, once when
        # it has gone on long enough to stop being contention.
        stall_n = state.stall_polls + 1
        pending: list[SiliconEvent] = [
            SiliconEvent(kind=e.kind, detail=f"{e.detail} [{type(exc).__name__}]", at=now)
            for e in stall_events(stall_n)
        ]
        pending.extend(diff_storage(previous_storage, storage, at=now, was_blind=was_blind))
        for event in pending:
            print(f"[{stamp}] {event}", flush=True)
        await publish_events(bus, pending)
        if not quiet:
            print(f"[{stamp}] {storage.summary} (census unavailable, poll {stall_n})", flush=True)
        return CycleState(
            census=previous,
            router_down=False,
            storage=next_storage,
            census_stalled=True,
            blind=next_blind,
            stall_polls=stall_n,
        )

    if census_stalled:
        resumed = SiliconEvent(
            kind="census_resumed",
            detail=f"/health answering again after {state.stall_polls} stalled poll(s)",
            at=now,
        )
        print(f"[{stamp}] {resumed}", flush=True)
        await publish_events(bus, [resumed])

    census = parse_census(health, catalog=catalog, checked_at=now)
    # Storage events ride the same publish path as residency events so a single
    # `accepted` count covers the cycle and one bus failure cannot deliver half
    # the picture.
    events = diff_census(previous, census) + diff_storage(
        previous_storage, storage, at=now, was_blind=was_blind
    )

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
        print(f"[{stamp}] {storage.summary}", flush=True)
        for warning in plan.warnings:
            print(f"    WARN    {warning}", flush=True)
        for refusal in plan.refused:
            print(f"    REFUSED {refusal}", flush=True)
    if plan.actions:
        await _apply_plan(plan, apply_pins=apply_changes, heal=heal, quiet=quiet)

    return CycleState(
        census=census,
        router_down=False,
        storage=next_storage,
        census_stalled=False,
        blind=next_blind,
        stall_polls=0,  # explicit: a successful census resets the escalation clock
    )


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

    state = CycleState()
    cycles = 0
    try:
        while _running:
            state = await cycle(state, bus, args.apply, args.quiet, args.heal)
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
