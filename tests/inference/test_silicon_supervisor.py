"""Tests for silicon transition detection (the 24/7 event stream).

The scenario in `test_t2_real_observed_churn_*` is not invented: it is the
actual fleet change observed live on 2026-08-29 between two census runs
minutes apart, where Qwen3-0.6B was evicted and a 16.9GB Gemma-4-26B-A4B
took its place. Real churn is the best fixture for a churn detector.
"""

from __future__ import annotations

import asyncio

import pytest

from cohezion.inference.silicon_residency import parse_census
from cohezion.inference.silicon_supervisor import (
    SiliconEvent,
    bus_event_type_name,
    diff_census,
    publish_events,
    severity_of,
)


def _entry(name, device, **kw):
    base = {
        "model_name": name,
        "device": device,
        "type": kw.pop("type", "llm"),
        "recipe_options": {"ctx_size": kw.pop("ctx_size", 8192)},
        "pinned": kw.pop("pinned", False),
        "is_busy": kw.pop("is_busy", False),
        "is_streaming": kw.pop("is_streaming", False),
        "last_use": kw.pop("last_use", 1000),
        "backend_alive": kw.pop("backend_alive", True),
        "backend_health": kw.pop("backend_health", "ready"),
    }
    base.update(kw)
    return base


def _census(entries, at=0.0):
    return parse_census({"all_models_loaded": entries}, checked_at=at)


# --------------------------- first observation ---------------------------


def test_first_observation_does_not_emit_a_load_burst() -> None:
    """DISCRIMINATING: an impl treating None as an empty census emits N loads.

    On startup the supervisor must not claim every already-resident model
    just loaded -- that would poison any rate-of-change alerting.
    """
    current = _census([_entry("a", "npu"), _entry("b", "gpu")])
    events = diff_census(None, current)
    assert [e.kind for e in events] == []


def test_first_observation_still_reports_standing_hazards() -> None:
    """A hazard predating the supervisor is still a hazard."""
    current = _census([_entry("a", "npu", ctx_size=-1)])
    events = diff_census(None, current)
    assert [e.kind for e in events] == ["ctx_uncapped_appeared"]


# --------------------------- real observed churn ---------------------------


def test_t2_real_observed_churn_reports_both_sides() -> None:
    """Live 2026-08-29: Qwen3-0.6B evicted, Gemma-4-26B-A4B loaded."""
    before = _census(
        [
            _entry("llama3.2-1b-FLM", "npu", ctx_size=4096),
            _entry("Gemma-4-E4B-it-GGUF", "gpu"),
            _entry("Qwen3-0.6B-GGUF", "gpu", last_use=936739),
        ]
    )
    after = _census(
        [
            _entry("llama3.2-1b-FLM", "npu", ctx_size=4096),
            _entry("Gemma-4-E4B-it-GGUF", "gpu"),
            _entry("Gemma-4-26B-A4B-it-GGUF", "gpu", ctx_size=32768),
        ]
    )
    kinds = {(e.kind, e.model) for e in diff_census(before, after)}
    assert ("model_evicted", "Qwen3-0.6B-GGUF") in kinds
    assert ("model_loaded", "Gemma-4-26B-A4B-it-GGUF") in kinds


def test_t2_unchanged_fleet_emits_nothing() -> None:
    """DISCRIMINATING: an impl re-emitting current state floods on every poll."""
    snapshot = _census([_entry("a", "npu"), _entry("b", "gpu")])
    assert diff_census(snapshot, snapshot) == ()


# --------------------------- device-level transitions ---------------------------


def test_t2_device_vacated_is_detected() -> None:
    """Losing the last model on a device idles that silicon -- a capacity event."""
    before = _census([_entry("a", "npu"), _entry("b", "gpu")])
    after = _census([_entry("b", "gpu")])
    events = diff_census(before, after)
    vacated = [e for e in events if e.kind == "device_vacated"]
    assert [e.device for e in vacated] == ["npu"]


def test_t2_device_engaged_and_idle_are_distinct_transitions() -> None:
    idle = _census([_entry("a", "npu", is_busy=False)])
    busy = _census([_entry("a", "npu", is_busy=True)])

    assert [e.kind for e in diff_census(idle, busy)] == ["device_engaged"]
    assert [e.kind for e in diff_census(busy, idle)] == ["device_idle"]


def test_model_migration_between_silicon_is_reported() -> None:
    before = _census([_entry("a", "cpu")])
    after = _census([_entry("a", "gpu")])
    events = [e for e in diff_census(before, after) if e.model == "a"]
    assert any("migrated from cpu to igpu" in e.detail for e in events)


# --------------------------- safety-critical signals ---------------------------


def test_t2_pin_lost_is_detected() -> None:
    """DISCRIMINATING: an impl diffing only membership misses attribute loss.

    A tier-0 router silently losing its pin becomes LRU-evictable again --
    an availability regression with no membership change to notice.
    """
    before = _census([_entry("router", "npu", pinned=True)])
    after = _census([_entry("router", "npu", pinned=False)])
    assert [e.kind for e in diff_census(before, after)] == ["pin_lost"]


def test_t2_new_ctx_hazard_is_critical_and_actionable() -> None:
    before = _census([_entry("a", "npu", ctx_size=4096)])
    after = _census([_entry("a", "npu", ctx_size=-1)])
    events = diff_census(before, after)
    hazard = next(e for e in events if e.kind == "ctx_uncapped_appeared")
    assert hazard.severity == "warning", "ctx=-1 is a policy risk, not a crasher"
    assert hazard.actionable is True
    assert "unbounded" not in hazard.detail, (
        "an earlier revision called ctx=-1 an 'unbounded KV cache', wording "
        "silicon_residency.py itself documents as inaccurate for -1"
    )


def test_t2_ctx_zero_is_critical_but_ctx_minus_one_is_not() -> None:
    """REVIEW FINDING: the two ctx classes must not page at the same severity.

    ResidentModel.ctx_risk was added to rank them and was never read -- the
    event kind was hard-coded 'critical' for both. ctx_size=0 is the documented
    Strix Halo hard hang; ctx_size=-1 means "use the model's own maximum".
    """
    before = _census([_entry("a", "npu", ctx_size=4096)])
    crasher = diff_census(before, _census([_entry("a", "npu", ctx_size=0)]))
    uncapped = diff_census(before, _census([_entry("a", "npu", ctx_size=-1)]))

    assert [e.kind for e in crasher] == ["ctx_crasher_appeared"]
    assert crasher[0].severity == "critical"
    assert [e.kind for e in uncapped] == ["ctx_uncapped_appeared"]
    assert uncapped[0].severity == "warning"


def test_pre_existing_hazard_is_not_re_emitted_every_poll() -> None:
    """DISCRIMINATING: re-emitting a standing hazard buries new ones in noise."""
    hazard = _census([_entry("a", "npu", ctx_size=0)])
    assert diff_census(hazard, hazard) == ()


def test_watchdog_reset_is_reported_once_per_occurrence() -> None:
    quiet = _census([_entry("a", "npu", watchdog_reset=False)])
    flapped = _census([_entry("a", "npu", watchdog_reset=True)])

    assert [e.kind for e in diff_census(quiet, flapped)] == ["watchdog_reset"]
    assert diff_census(flapped, flapped) == ()


def test_unhealthy_backend_is_critical() -> None:
    before = _census([_entry("a", "npu")])
    after = _census([_entry("a", "npu", backend_alive=False)])
    events = diff_census(before, after)
    assert any(e.kind == "backend_unhealthy" and e.severity == "critical" for e in events)


def test_t2_standing_fault_is_not_re_emitted_every_poll() -> None:
    """REGRESSION (live 2026-08-29): the same CRITICAL fired on every cycle.

    DISCRIMINATING: an impl without the transition guard emits on both polls.
    A fault re-announced forever buries genuinely new events in its own noise.
    """
    faulted = _census([_entry("a", "npu", backend_alive=False)])
    assert [e.kind for e in diff_census(None, faulted)] == ["backend_unhealthy"]
    assert diff_census(faulted, faulted) == (), "standing fault must not re-emit"


def test_t2_busy_model_produces_no_health_alert_at_all() -> None:
    """REGRESSION: a serving model must not look like a fault to the supervisor."""
    before = _census([_entry("a", "npu", backend_health="ready")])
    after = _census([_entry("a", "npu", backend_health="busy", is_busy=True)])
    kinds = {e.kind for e in diff_census(before, after)}
    assert "backend_unhealthy" not in kinds
    assert "device_engaged" in kinds, "it should read as engagement, not failure"


# --------------------------- severity contract ---------------------------


def test_severity_ranking_separates_noise_from_action() -> None:
    assert severity_of("model_loaded") == "info"
    assert severity_of("model_evicted") == "notice"
    assert severity_of("ctx_crasher_appeared") == "critical"
    assert severity_of("ctx_uncapped_appeared") == "warning"
    assert severity_of("unknown_kind") == "info", "unknown events must not page anyone"


def test_routine_churn_is_not_actionable() -> None:
    """DISCRIMINATING: marking every event actionable makes alerting useless."""
    before = _census([_entry("a", "npu")])
    after = _census([_entry("a", "npu"), _entry("b", "gpu")])
    events = diff_census(before, after)
    assert events and not any(e.actionable for e in events)


# --------------------- data-mesh bridge (CONSUMPTION) ---------------------
#
# These assert DELIVERY to a real subscriber on a real EventBus, not that
# publish returned True. `publish_sync` returns True on an unstarted bus while
# delivering to nobody, so a test that only checks the return value proves
# nothing. Measured 2026-08-29: unstarted bus delivered 0 of 1.


def _bus_and_inbox(event_type):
    from cohezion.core.event_bus import EventBus

    bus = EventBus()
    inbox: list = []

    async def handler(event):
        inbox.append(event)

    bus.register_handler(handler, event_type)
    return bus, inbox


def test_t2_events_reach_a_real_subscriber_on_a_started_bus() -> None:
    """CONSUMPTION: a real handler must actually receive the event."""
    from cohezion.core.event_bus import EventType

    async def scenario():
        bus, inbox = _bus_and_inbox(EventType.MODEL_EVICTED)
        await bus.start()
        n = await publish_events(bus, [SiliconEvent(kind="model_evicted", model="m", device="npu")])
        await asyncio.sleep(0.2)
        await bus.stop()
        return n, inbox

    published, inbox = asyncio.run(scenario())
    assert published == 1
    assert len(inbox) == 1, "subscriber must actually receive the event"
    assert inbox[0].payload["kind"] == "model_evicted"
    assert inbox[0].payload["device"] == "npu"


def test_t2_unstarted_bus_is_refused_not_silently_dropped() -> None:
    """DISCRIMINATING: the pre-fix daemon published here and delivered nothing.

    An unstarted bus enqueues into a queue no one drains. Returning a nonzero
    count would report success for events nobody receives.
    """
    from cohezion.core.event_bus import EventType

    async def scenario():
        bus, inbox = _bus_and_inbox(EventType.MODEL_EVICTED)
        # deliberately NOT started -- exactly the original daemon's behaviour
        n = await publish_events(bus, [SiliconEvent(kind="model_evicted", model="m", device="npu")])
        await asyncio.sleep(0.2)
        return n, inbox

    published, inbox = asyncio.run(scenario())
    assert published == 0, "must not claim to have published to an undrained queue"
    assert inbox == []


def test_t2_actionable_events_get_higher_priority() -> None:
    from cohezion.core.event_bus import EventType

    async def scenario():
        bus, inbox = _bus_and_inbox(EventType.MODEL_ROSTER_CHANGED)
        await bus.start()
        await publish_events(bus, [SiliconEvent(kind="pin_lost", model="router")])
        await asyncio.sleep(0.2)
        await bus.stop()
        return inbox

    inbox = asyncio.run(scenario())
    assert len(inbox) == 1
    assert inbox[0].priority == 2, "warning-or-worse must outrank routine churn"


def test_unknown_kind_rides_system_health_not_dropped() -> None:
    assert bus_event_type_name("model_loaded") == "MODEL_LOADED"
    assert bus_event_type_name("pin_lost") == "MODEL_ROSTER_CHANGED"
    assert bus_event_type_name("some_future_kind") == "SYSTEM_HEALTH"


def test_publishing_nothing_or_no_bus_is_a_safe_noop() -> None:
    assert asyncio.run(publish_events(None, [SiliconEvent(kind="model_loaded")])) == 0
    assert asyncio.run(publish_events(object(), [])) == 0


@pytest.mark.parametrize("kind", ["model_loaded", "model_evicted", "device_vacated", "pin_lost"])
def test_every_mapped_kind_resolves_to_a_real_event_type(kind: str) -> None:
    """A mapping naming an EventType that does not exist would silently degrade."""
    from cohezion.core.event_bus import EventType

    assert hasattr(EventType, bus_event_type_name(kind))


# ------------------- router outage incident semantics -------------------
#
# The outage path lives in the daemon (it is an HTTP failure, not a census
# diff), so these lock the SEVERITY CONTRACT the daemon depends on. Verified
# live 2026-08-29 against a dead port and a mid-run recovery:
#   [10:55:30] CRITICAL router_unreachable -- Connection refused
#   [10:55:33] NOTICE   router_recovered   -- responding again
# Before the edge-trigger fix, router_unreachable re-fired on EVERY poll:
# at a 45s interval that is ~1900 identical CRITICALs per day.


def test_router_outage_is_critical_and_actionable() -> None:
    outage = SiliconEvent(kind="router_unreachable", detail="connection refused")
    assert outage.severity == "critical"
    assert outage.actionable is True


def test_router_recovery_is_not_actionable() -> None:
    """DISCRIMINATING: paging on recovery doubles every incident's noise.

    Recovery closes an incident; it does not open one. Marking it actionable
    would make every outage generate two pages instead of one.
    """
    recovered = SiliconEvent(kind="router_recovered", detail="responding again")
    assert recovered.severity == "notice"
    assert recovered.actionable is False


def test_outage_and_recovery_are_a_matched_pair() -> None:
    """Both kinds must exist in the severity table, or one rides the default.

    An unmapped kind silently becomes "info", which would downgrade a total
    router outage to routine chatter.
    """
    assert severity_of("router_unreachable") == "critical"
    assert severity_of("router_recovered") == "notice"
    assert bus_event_type_name("router_unreachable") == "SYSTEM_HEALTH"
    assert bus_event_type_name("router_recovered") == "SYSTEM_HEALTH"
