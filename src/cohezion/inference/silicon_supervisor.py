"""Transition detection for 24/7 silicon supervision.

Lemonade 11.8.1 exposes a websocket on :9000, but it speaks an undocumented
non-HTTP framed protocol (probed 2026-08-29: a standards-compliant websocket
handshake is rejected, and a plain HTTP request gets no response at all).
Rather than reverse-engineer an unversioned wire format, we derive the event
stream by diffing successive `/api/v1/health` censuses.

That is the better engineering trade regardless of the socket: a polled diff is
deterministic, replayable from stored snapshots, and cannot silently drop a
frame the way an undocumented socket can. The cost is latency bounded by the
poll interval, which is irrelevant for residency events measured in minutes.

Emits `SiliconEvent`s that the data mesh can persist and act on.
"""

from __future__ import annotations

import logging
from collections.abc import Sequence
from dataclasses import dataclass

from cohezion.inference.silicon_residency import ModelStorage, ResidentModel, SiliconCensus


logger = logging.getLogger(__name__)


__all__ = [
    "SiliconEvent",
    "bus_event_type_name",
    "diff_census",
    "diff_storage",
    "next_storage_baseline",
    "publish_events",
    "severity_of",
]


# Ordered least -> most urgent, so callers can threshold on it.
_SEVERITY_RANK: dict[str, int] = {"info": 0, "notice": 1, "warning": 2, "critical": 3}

_EVENT_SEVERITY: dict[str, str] = {
    "model_loaded": "info",
    "model_evicted": "notice",
    "device_engaged": "info",
    "device_idle": "info",
    "device_vacated": "warning",  # silicon lost its last model
    "watchdog_reset": "warning",  # server had to restart a backend
    "backend_unhealthy": "critical",
    # Split to match ResidentModel.ctx_risk. ctx_size=0 is the documented
    # hard-hang crasher; ctx_size=-1 means "use the model's own maximum" (
    # measured) and is a POLICY risk, not a crash. An earlier revision paged
    # CRITICAL for both with the wording "unbounded KV cache", which
    # silicon_residency.py in the same change calls inaccurate for -1.
    "ctx_crasher_appeared": "critical",  # ctx_size=0 -- Strix Halo hard hang
    "ctx_uncapped_appeared": "warning",  # ctx_size=-1/None -- KV size unchosen
    "pin_lost": "warning",  # a protected model is no longer protected
    "router_unreachable": "critical",
    "router_recovered": "notice",  # paired with router_unreachable, closes the incident
    # MEASURED 2026-08-30: /api/v1/health and /api/v1/models intermittently
    # block for 20s+ while /api/v1/system-info answers in ~3ms throughout. The
    # first two enumerate loaded models and evidently contend with a lock a busy
    # backend holds; system-info reads static device state and does not.
    #
    # So a /health timeout is NOT evidence the router is down, and reporting it
    # as `router_unreachable` would page a human every time the fleet got busy.
    # This kind means "the census is unavailable this cycle" -- degraded
    # observability, not an outage. `router_unreachable` is now reserved for the
    # case where even the cheap endpoint fails.
    "census_stalled": "warning",
    "census_resumed": "notice",
    # Model-store capacity. Gated on ABSOLUTE free bytes, not the used fraction
    # -- see the rationale block in silicon_residency.py. A store that cannot
    # accept a write does not announce itself; it surfaces much later as a
    # mid-download failure in whatever job happened to need a model next.
    "store_critical": "critical",  # cannot fit even a small model
    "store_low": "warning",  # roughly one mid-size model of notice left
    "store_recovered": "notice",  # paired, closes a store incident
    # Not a store problem -- a BLINDNESS problem. The server stopped reporting
    # capacity, so the guard above is now inert. Worth saying once, because a
    # silent guard and a healthy store look identical from the outside.
    "store_unmeasured": "notice",
}


def severity_of(kind: str) -> str:
    return _EVENT_SEVERITY.get(kind, "info")


@dataclass(frozen=True)
class SiliconEvent:
    """One observed transition in fleet residency."""

    kind: str
    model: str = ""
    device: str = ""
    detail: str = ""
    at: float = 0.0

    @property
    def severity(self) -> str:
        return severity_of(self.kind)

    @property
    def actionable(self) -> bool:
        """True when a human or supervisor should react now."""
        return _SEVERITY_RANK[self.severity] >= _SEVERITY_RANK["warning"]

    def __str__(self) -> str:
        loc = f"[{self.device}]" if self.device else ""
        tail = f" -- {self.detail}" if self.detail else ""
        return f"{self.severity.upper():8s} {self.kind:20s} {self.model}{loc}{tail}"


def _index(census: SiliconCensus) -> dict[str, ResidentModel]:
    return {m.name: m for m in census.residents}


def diff_census(
    previous: SiliconCensus | None,
    current: SiliconCensus,
) -> tuple[SiliconEvent, ...]:
    """Derive transition events between two censuses.

    A `None` previous census means this is the first observation: we report
    only standing hazards, not a spurious "everything just loaded" burst.
    """
    at = current.checked_at
    events: list[SiliconEvent] = []

    def emit(kind: str, model: str = "", device: str = "", detail: str = "") -> None:
        events.append(SiliconEvent(kind=kind, model=model, device=device, detail=detail, at=at))

    # Standing hazards are reported on every observation, first one included:
    # a hazard that predates the supervisor is still a hazard.
    for hazard in current.ctx_hazards:
        prior = _index(previous).get(hazard.name) if previous else None
        if prior is None or not prior.ctx_hazard:
            # Rank by ctx_risk rather than paging CRITICAL for both classes.
            if hazard.ctx_crasher:
                emit(
                    "ctx_crasher_appeared",
                    hazard.name,
                    hazard.device,
                    "ctx_size=0 -- the documented Strix Halo hard-hang vector",
                )
            else:
                emit(
                    "ctx_uncapped_appeared",
                    hazard.name,
                    hazard.device,
                    f"ctx_size={hazard.ctx_size} -- no explicit cap; KV sized by "
                    f"the model's own advertised window",
                )

    # Emit on TRANSITION only. A standing fault re-announced every poll buries
    # genuinely new events under its own noise.
    for sick in current.unhealthy:
        prior = _index(previous).get(sick.name) if previous else None
        if prior is None or not prior.unhealthy:
            emit(
                "backend_unhealthy",
                sick.name,
                sick.device,
                f"alive={sick.backend_alive} health={sick.backend_health!r}",
            )

    for flapped in current.watchdog_resets:
        prior = _index(previous).get(flapped.name) if previous else None
        if prior is None or not prior.watchdog_reset:
            emit(
                "watchdog_reset",
                flapped.name,
                flapped.device,
                "server restarted this backend",
            )

    if previous is None:
        return tuple(events)

    prev_models = _index(previous)
    curr_models = _index(current)

    for name in curr_models.keys() - prev_models.keys():
        m = curr_models[name]
        emit("model_loaded", name, m.device, f"{m.size_gb:g}GB ctx={m.ctx_size}")

    for name in prev_models.keys() - curr_models.keys():
        m = prev_models[name]
        detail = "was pinned" if m.pinned else f"last_use={m.last_use}"
        emit("model_evicted", name, m.device, detail)

    for name in curr_models.keys() & prev_models.keys():
        was, now = prev_models[name], curr_models[name]
        if was.pinned and not now.pinned:
            emit("pin_lost", name, now.device, "model is no longer protected")
        if was.device != now.device:
            emit(
                "model_loaded",
                name,
                now.device,
                f"migrated from {was.device} to {now.device}",
            )

    # Device-level transitions matter more than per-model ones for capacity
    # planning: losing the last model on a device idles that silicon entirely.
    for device in previous.by_device.keys() | current.by_device.keys():
        before, after = previous.occupancy(device), current.occupancy(device)
        if before.count > 0 and after.count == 0:
            emit("device_vacated", device=device, detail="silicon now carries no model")
        if not before.busy and after.busy:
            emit("device_engaged", device=device, detail=f"{after.count} model(s)")
        if before.busy and not after.busy:
            emit("device_idle", device=device, detail=f"{after.count} model(s) resident")

    return tuple(events)


# --------------------------------------------------------------------------
# Data-mesh bridge
# --------------------------------------------------------------------------
#
# `EventBus.publish_sync()` only ENQUEUES. The queue is drained by
# `_process_loop`, which runs only while `_running` is True -- i.e. only after
# `await bus.start()`. Publishing to an unstarted bus returns True and
# increments the `published` metric while delivering to nobody.
#
# Measured 2026-08-29 (two-arm probe): unstarted bus -> subscriber saw 0 of 1
# events; started bus -> 1 of 1. Both calls returned True. That is a convincing
# no-op, which is why `publish_events` refuses to be silent about it.

# SiliconEvent.kind -> EventType member name. Kinds without a natural lifecycle
# type ride SYSTEM_HEALTH so nothing is silently dropped.
_BUS_EVENT_TYPE_NAMES: dict[str, str] = {
    "model_loaded": "MODEL_LOADED",
    "model_evicted": "MODEL_EVICTED",
    "device_vacated": "MODEL_ROSTER_CHANGED",
    "pin_lost": "MODEL_ROSTER_CHANGED",
}


def bus_event_type_name(kind: str) -> str:
    """EventType member name for a SiliconEvent kind (never raises)."""
    return _BUS_EVENT_TYPE_NAMES.get(kind, "SYSTEM_HEALTH")


def bus_is_running(bus: object) -> bool:
    """Best-effort check that an EventBus will actually drain its queue.

    Returns False when the state cannot be determined, so an unknown bus is
    reported as not-delivering rather than assumed healthy.
    """
    return bool(getattr(bus, "_running", False))


async def publish_events(bus: object, events: Sequence[SiliconEvent]) -> int:
    """Publish silicon events onto a STARTED EventBus. Returns count accepted.

    Never raises: a supervisor must survive a broken bus. But it will not
    publish into an undrained queue silently -- an unstarted bus logs an error
    and returns 0, because "published 12 events" that nobody received is worse
    than an explicit failure.
    """
    if bus is None or not events:
        return 0

    if not bus_is_running(bus):
        logger.error(
            "EventBus is not started; %d silicon event(s) would be enqueued but never "
            "delivered. Call `await bus.start()` before publishing.",
            len(events),
        )
        return 0

    try:
        from cohezion.core.event_bus import Event, EventType
    except ImportError as exc:
        logger.warning("event bus unavailable (%s); silicon events not published", exc)
        return 0

    # `bus` is typed `object` on purpose: this module must not import EventBus
    # at module scope (the daemon has to run when the bus is unavailable, and
    # the import above is what decides that). The trade is that the attribute
    # access below is invisible to the type checker, so name it explicitly here
    # rather than leaving a standing error for a reader to re-diagnose.
    publish = getattr(bus, "publish", None)
    if publish is None:
        logger.error("bus has no publish(); %d silicon event(s) dropped", len(events))
        return 0

    published = 0
    for event in events:
        try:
            etype = getattr(EventType, bus_event_type_name(event.kind), None) or (
                EventType.SYSTEM_HEALTH
            )
            ok = await publish(
                Event(
                    type=etype,
                    source="silicon_supervisor",
                    payload={
                        "kind": event.kind,
                        "model": event.model,
                        "device": event.device,
                        "detail": event.detail,
                        "severity": event.severity,
                    },
                    priority=2 if event.actionable else 0,
                )
            )
            published += 1 if ok else 0
        except Exception:
            logger.exception("failed publishing silicon event %s", event.kind)
    return published


def _capacity_state(store: ModelStorage) -> str:
    """Collapse a MEASURED store to the label alerting cares about.

    Callers must not pass an unmeasured store: capacity and measurability are
    separate axes (see `diff_storage`), and folding "we could not read it" in
    here as a fourth value is what produced the stuck-incident bug below.
    """
    if store.critical:
        return "critical"
    if store.warning:
        return "low"
    return "ok"


def next_storage_baseline(
    previous: ModelStorage | None,
    current: ModelStorage,
) -> ModelStorage | None:
    """The capacity baseline to carry into the next cycle.

    Lives here, named and tested, rather than inline in the daemon, because it
    is where the stranded-incident bug actually was. `diff_storage` was only
    ever as correct as the baseline it was handed: a caller that carried a blind
    reading forward destroyed the memory of an open incident no matter how the
    diff was written, and the two are only correct together.
    """
    return current if current.measured else previous


def diff_storage(
    previous: ModelStorage | None,
    current: ModelStorage,
    at: float = 0.0,
    was_blind: bool = False,
) -> tuple[SiliconEvent, ...]:
    """Emit store-capacity events on STATE CHANGE only.

    `previous` is the last MEASURED storage (or None), NOT simply the last
    reading; `was_blind` says whether the previous cycle failed to measure.
    Capacity and measurability are tracked as two independent state machines,
    and that separation is load-bearing rather than tidiness:

        An unmeasured reading is not an observation of the store, so it must
        not be allowed to overwrite what we last knew about capacity.

    The single-machine version, where `unmeasured` was a fourth capacity state,
    had a hole two independent reviewers found before this landed:
    `critical -> unmeasured -> ok` compared `ok` against a prior of
    `unmeasured`, matched no recovery branch, and emitted nothing -- leaving a
    critical incident open forever while the store was in fact fine. A test in
    this suite asserted that silence was correct, which is how the bug survived
    being written down.

    Edge-triggered on both axes, deliberately. Level-triggered, a store that
    stays full re-emits `store_critical` every poll: at 30s that is 2880
    identical CRITICALs a day for one unchanging condition -- the same flooding
    already fixed twice for `backend_unhealthy` and `router_unreachable`.

    A `None` previous means first observation: a standing problem is still
    reported (a store that was full before the supervisor started is still
    full), but a healthy store produces nothing.
    """
    # --- Axis 1: measurability. Does not touch the capacity baseline. ---
    if not current.measured:
        if was_blind:
            return ()
        return (
            SiliconEvent(
                kind="store_unmeasured",
                detail="server stopped reporting model_storage; capacity guard is inert",
                at=at,
            ),
        )

    # --- Axis 2: capacity. Only advances on measured observations. ---
    #
    # No paired "measurement resumed" event: `store_unmeasured` is a notice, not
    # an incident needing closure, and resumption is directly observable because
    # capacity events start flowing again. Coming back from blindness into the
    # SAME capacity state is correctly silent -- the incident was never closed,
    # so re-announcing it would be the duplicate this function exists to avoid.
    state = _capacity_state(current)
    prior = _capacity_state(previous) if previous is not None else None

    if state == prior:
        return ()

    detail = current.summary
    if state == "critical":
        return (SiliconEvent(kind="store_critical", detail=detail, at=at),)
    if state == "low":
        return (SiliconEvent(kind="store_low", detail=detail, at=at),)
    # state == "ok". Only meaningful as the close of an incident -- announcing a
    # healthy store on the first observation is noise, not news.
    if prior in ("critical", "low"):
        return (SiliconEvent(kind="store_recovered", detail=detail, at=at),)
    return ()
