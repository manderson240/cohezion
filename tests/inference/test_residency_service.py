"""V-model tests for ResidencyService — the consumer that makes the gate real.

The gate itself is NOT new. ``hotswap.ensure_resident`` already computes
``needed = weights + kv_overhead`` against ``free_gb() - floor`` and refuses when it does
not fit. Measured 2026-08-03: it has **zero** production callers. A gate nothing invokes
is decoration, and the box wedged today with the count cap holding perfectly while the
SIZE was unbounded.

So this module adds no new policy. It adds an OWNER and an event entry point.

Test tiers, in V-model order:
  T1 structural   — the surface exists (cheap, fires on signature drift)
  T2 behavioural  — the decision is actually made, and can go BOTH ways
  T3 consumption  — a datamesh event REACHES the gate (the invariant that matters)

A declaration invariant (`hasattr`) proves existence, never reachability, so every
structural test below is paired with a discriminating one that fails when the mechanism
is neutralised.
"""

from __future__ import annotations

import inspect

import pytest

from cohezion.inference.residency_ledger import ResidencyLedger
from cohezion.inference.residency_service import ResidencyService


class _Bus:
    """Minimal event sink; records what the service published."""

    def __init__(self) -> None:
        self.published: list[tuple[str, dict]] = []

    def publish(self, event_type: str, payload: dict) -> None:
        self.published.append((event_type, payload))


def _svc(bus=None, ledger=None, **kw):
    return ResidencyService(
        ledger=ledger or ResidencyLedger(), publish=bus.publish if bus else None, **kw
    )


# --------------------------------------------------------------------- T1 structural
class TestT1Structural:
    def test_surface_exists(self):
        for m in ("request", "release", "handle_event"):
            assert hasattr(ResidencyService, m), f"missing {m}"

    def test_handle_event_takes_a_single_event_mapping(self):
        params = inspect.signature(ResidencyService.handle_event).parameters
        assert "event" in params

    def test_request_accepts_ctx_size_and_protect(self):
        params = inspect.signature(ResidencyService.request).parameters
        assert {"model_id", "ctx_size", "protect"} <= set(params)


# ------------------------------------------------------------------- T2 behavioural
class TestT2TheDecisionCanGoBothWays:
    """A gate that can only refuse is a quarter leak; one that can only admit is a placebo.
    Both directions must be demonstrated (fail-open-demands-discriminating-test)."""

    def test_DISCRIMINATING_oversized_model_is_refused(self, monkeypatch):
        from cohezion.inference import hotswap as h

        monkeypatch.setattr(h, "resident_models", lambda: [])
        monkeypatch.setattr(h, "_catalog_sizes", lambda: {"Huge": 90.0})
        monkeypatch.setattr(h, "free_gb", lambda: 20.0)
        res = _svc().request("Huge")
        assert res.ok is False
        assert "refused before evicting" in res.reason.lower()

    def test_DISCRIMINATING_fitting_model_is_admitted(self, monkeypatch):
        from cohezion.inference import hotswap as h

        monkeypatch.setattr(h, "resident_models", lambda: [])
        monkeypatch.setattr(h, "_catalog_sizes", lambda: {"Small": 1.0})
        monkeypatch.setattr(h, "free_gb", lambda: 100.0)
        monkeypatch.setattr(h, "_post", lambda *a, **k: (200, "ok"))
        res = _svc().request("Small")
        assert res.ok is True

    def test_DISCRIMINATING_hopeless_load_refuses_without_evicting_anything(self, monkeypatch):
        """Observed live: a 128B model evicted 4 models and was THEN refused by 0.1 GB.
        Eviction is destructive; a target that cannot fit even after a full teardown must
        be refused first. An implementation that evicts-then-checks fails here."""
        from cohezion.inference import hotswap as h

        unloaded: list[str] = []
        monkeypatch.setattr(
            h,
            "resident_models",
            lambda: [{"model_name": "Small", "loaded": True, "is_busy": False, "last_use": 1}],
        )
        monkeypatch.setattr(h, "_catalog_sizes", lambda: {"Huge": 90.0, "Small": 2.0})
        monkeypatch.setattr(h, "free_gb", lambda: 20.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: (unloaded.append(m), True)[1])

        res = _svc().request("Huge")
        assert res.ok is False
        assert unloaded == [], f"evicted {unloaded} for a load that could never fit"
        assert "before evicting" in res.reason

    def test_eviction_STILL_happens_when_it_would_actually_help(self, monkeypatch):
        """Positive control — proves the new guard is selective, not a blanket refusal."""
        from cohezion.inference import hotswap as h

        unloaded: list[str] = []

        def _resident():
            """State-based: 'Big' until evicted, then 'Target' once loaded."""
            name = "Target" if unloaded else "Big"
            return [{"model_name": name, "loaded": True, "is_busy": False, "last_use": 1}]

        monkeypatch.setattr(h, "resident_models", _resident)
        monkeypatch.setattr(h, "_catalog_sizes", lambda: {"Target": 30.0, "Big": 40.0})
        # State-based, not call-order-based: free RAM reflects whether the eviction has
        # happened. A strict iter([...]) breaks whenever the implementation reads free_gb()
        # a different number of times, which is an implementation detail, not a contract.
        monkeypatch.setattr(h, "free_gb", lambda: 60.0 if unloaded else 20.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: (unloaded.append(m), True)[1])
        monkeypatch.setattr(h, "_post", lambda *a, **k: (200, "ok"))

        res = _svc().request("Target")
        assert unloaded == ["Big"], "the guard must not block an eviction that would help"
        assert res.ok is True

    def test_already_resident_is_a_cheap_success_with_no_load(self, monkeypatch):
        from cohezion.inference import hotswap as h

        calls: list = []
        monkeypatch.setattr(
            h, "resident_models", lambda: [{"model_name": "A", "loaded": True, "last_use": 1}]
        )
        monkeypatch.setattr(h, "_post", lambda *a, **k: (calls.append(a), (200, "ok"))[1])
        res = _svc().request("A")
        assert res.ok and res.already_resident and calls == []

    def test_release_unloads_and_writes_through_to_the_ledger(self, monkeypatch):
        from cohezion.inference import hotswap as h

        led = ResidencyLedger()
        led.record_load("A", 1.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: True)
        assert _svc(ledger=led).release("A") is True
        assert led.entries() == []

    def test_release_of_unknown_model_does_not_raise(self, monkeypatch):
        from cohezion.inference import hotswap as h

        monkeypatch.setattr(h, "unload", lambda m, **k: True)
        assert _svc().release("never-seen") is True


# ------------------------------------------------------------------- T3 consumption
class TestT3EventsReachTheGate:
    """The invariant that matters. Accepting an event is not consuming it."""

    def test_DISCRIMINATING_model_needed_event_invokes_the_gate(self, monkeypatch):
        """A stub that merely ACCEPTS the event without calling the gate fails here."""
        from cohezion.inference import hotswap as h

        seen: list[str] = []
        monkeypatch.setattr(h, "resident_models", lambda: [])
        monkeypatch.setattr(h, "_catalog_sizes", lambda: (seen.append("gated"), {"M": 1.0})[1])
        monkeypatch.setattr(h, "free_gb", lambda: 100.0)
        monkeypatch.setattr(h, "_post", lambda *a, **k: (200, "ok"))
        _svc().handle_event({"event_type": "model_needed", "model_id": "M"})
        assert seen == ["gated"], "the event did not reach the admission gate"

    def test_DISCRIMINATING_refusal_is_published_not_swallowed(self, monkeypatch):
        from cohezion.inference import hotswap as h

        monkeypatch.setattr(h, "resident_models", lambda: [])
        monkeypatch.setattr(h, "_catalog_sizes", lambda: {"Huge": 90.0})
        monkeypatch.setattr(h, "free_gb", lambda: 20.0)
        bus = _Bus()
        _svc(bus).handle_event({"event_type": "model_needed", "model_id": "Huge"})
        kinds = [k for k, _ in bus.published]
        assert "model_refused" in kinds, f"refusal was swallowed; published={kinds}"

    def test_admission_is_published(self, monkeypatch):
        from cohezion.inference import hotswap as h

        monkeypatch.setattr(h, "resident_models", lambda: [])
        monkeypatch.setattr(h, "_catalog_sizes", lambda: {"S": 1.0})
        monkeypatch.setattr(h, "free_gb", lambda: 100.0)
        monkeypatch.setattr(h, "_post", lambda *a, **k: (200, "ok"))
        bus = _Bus()
        _svc(bus).handle_event({"event_type": "model_needed", "model_id": "S"})
        assert "model_admitted" in [k for k, _ in bus.published]

    def test_model_idle_event_releases(self, monkeypatch):
        from cohezion.inference import hotswap as h

        led = ResidencyLedger()
        led.record_load("A", 1.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: True)
        _svc(ledger=led).handle_event({"event_type": "model_idle", "model_id": "A"})
        assert led.entries() == []

    def test_unknown_event_type_is_a_noop(self):
        assert _svc().handle_event({"event_type": "something_else"}) is None

    def test_malformed_event_does_not_raise(self):
        """The daemon must survive a bad message rather than die on it."""
        svc = _svc()
        assert svc.handle_event({}) is None
        assert svc.handle_event({"event_type": "model_needed"}) is None  # no model_id

    def test_publish_failure_does_not_break_the_decision(self, monkeypatch):
        """A broken sink must not turn a successful admission into a failure."""
        from cohezion.inference import hotswap as h

        monkeypatch.setattr(h, "resident_models", lambda: [])
        monkeypatch.setattr(h, "_catalog_sizes", lambda: {"S": 1.0})
        monkeypatch.setattr(h, "free_gb", lambda: 100.0)
        monkeypatch.setattr(h, "_post", lambda *a, **k: (200, "ok"))

        def boom(*a, **k):
            raise RuntimeError("bus down")

        svc = ResidencyService(ledger=ResidencyLedger(), publish=boom)
        res = svc.handle_event({"event_type": "model_needed", "model_id": "S"})
        assert res is not None and res.ok is True


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
