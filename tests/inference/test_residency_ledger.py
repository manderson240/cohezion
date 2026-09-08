"""Tests for the write-through residency ledger.

The defect this closes (measured 2026-08-03): `hotswap.resident_models()` reads
`/api/v1/health`, and returns `[]` on any failure. `/health` is precisely the endpoint
that degrades under the memory pressure the hotswap gate exists to relieve — and an empty
resident list means an empty VICTIM list, so `ensure_resident` can never evict anything.
The gate becomes permanently refusing: fail-closed and therefore safe, but useless.

Residency is observable ONLY via /health — `/api/v1/models` reports `downloaded` (disk,
not RAM) and `/api/v1/system-info` reports neither. So a fallback view has to be built
from what this process itself did.

The ledger is deliberately NOT a replacement for the server view. hotswap's original
design note is correct: local bookkeeping drifts the moment anything else loads a model.
So the server stays authoritative WHENEVER IT ANSWERS; the ledger is the degraded-mode
fallback, and drift is surfaced rather than hidden.
"""

from __future__ import annotations

import pytest

from cohezion.inference.residency_ledger import ResidencyLedger, resident_view


def _server(*names: str) -> list[dict]:
    """Health-shaped entries, newest-used first (hotswap's contract)."""
    return [
        {"model_name": n, "loaded": True, "is_busy": False, "last_use": 100 - i}
        for i, n in enumerate(names)
    ]


class TestStructural:
    def test_ledger_exposes_the_write_through_api(self):
        led = ResidencyLedger()
        for m in ("record_load", "record_unload", "entries", "reconcile"):
            assert hasattr(led, m), f"missing {m}"

    def test_fresh_ledger_is_empty(self):
        assert ResidencyLedger().entries() == []


class TestWriteThrough:
    def test_record_load_then_appears_in_entries(self):
        led = ResidencyLedger()
        led.record_load("A", weights_gb=4.0)
        names = [e["model_name"] for e in led.entries()]
        assert names == ["A"]

    def test_record_unload_removes_it(self):
        led = ResidencyLedger()
        led.record_load("A", weights_gb=4.0)
        led.record_unload("A")
        assert led.entries() == []

    def test_unload_of_unknown_model_is_a_noop_not_an_error(self):
        led = ResidencyLedger()
        led.record_unload("never-seen")  # must not raise
        assert led.entries() == []

    def test_entries_are_newest_used_first(self):
        """hotswap picks victims from `reversed(loaded)`, so ordering is load-bearing:
        a wrong order evicts the MOST recently used model."""
        led = ResidencyLedger()
        led.record_load("old", weights_gb=1.0)
        led.record_load("new", weights_gb=1.0)
        assert [e["model_name"] for e in led.entries()] == ["new", "old"]

    def test_entries_are_health_shaped(self):
        """Callers consume these interchangeably with /health rows."""
        led = ResidencyLedger()
        led.record_load("A", weights_gb=4.0)
        e = led.entries()[0]
        assert {"model_name", "loaded", "is_busy", "last_use"} <= set(e)
        assert e["loaded"] is True


class TestResidentView:
    def test_DISCRIMINATING_server_empty_falls_back_to_ledger(self):
        """THE defect. An implementation that just returns the server list yields [],
        which produces an empty victim list and a permanently-refusing gate."""
        led = ResidencyLedger()
        led.record_load("A", weights_gb=4.0)
        led.record_load("B", weights_gb=4.0)
        view = resident_view([], led)
        assert [e["model_name"] for e in view] == ["B", "A"], (
            "health-down must fall back to the ledger, not report an empty fleet"
        )

    def test_DISCRIMINATING_server_wins_over_stale_ledger(self):
        """The ledger must NOT override a live server, or hotswap's correct design note
        (local bookkeeping drifts) gets reintroduced as a bug."""
        led = ResidencyLedger()
        led.record_load("stale-1", weights_gb=1.0)
        led.record_load("stale-2", weights_gb=1.0)
        view = resident_view(_server("real"), led)
        assert [e["model_name"] for e in view] == ["real"]

    def test_both_empty_is_empty(self):
        assert resident_view([], ResidencyLedger()) == []


class TestReconcile:
    def test_detects_model_the_ledger_missed(self):
        """Something else loaded a model — the case that makes local-only bookkeeping unsafe."""
        led = ResidencyLedger()
        led.record_load("mine", weights_gb=1.0)
        rep = led.reconcile(_server("mine", "someone-elses"))
        assert rep.only_in_server == ["someone-elses"]
        assert rep.agreed == ["mine"]

    def test_detects_ledger_entry_the_server_does_not_have(self):
        """A phantom unload, or an eviction by another process."""
        led = ResidencyLedger()
        led.record_load("gone", weights_gb=1.0)
        rep = led.reconcile(_server())
        assert rep.only_in_ledger == ["gone"]

    def test_reconcile_with_empty_server_does_NOT_wipe_the_ledger(self):
        """Health being down must not be read as 'the fleet is empty' — that would
        destroy the very fallback the ledger exists to provide."""
        led = ResidencyLedger()
        led.record_load("A", weights_gb=1.0)
        led.reconcile([])
        assert [e["model_name"] for e in led.entries()] == ["A"]

    def test_adopt_repairs_drift_from_a_healthy_server(self):
        led = ResidencyLedger()
        led.record_load("stale", weights_gb=1.0)
        led.adopt(_server("real-1", "real-2"))
        assert sorted(e["model_name"] for e in led.entries()) == ["real-1", "real-2"]

    def test_adopt_ignores_an_empty_server_list(self):
        """Same hazard as above, at the mutation site."""
        led = ResidencyLedger()
        led.record_load("A", weights_gb=1.0)
        led.adopt([])
        assert [e["model_name"] for e in led.entries()] == ["A"]

    def test_in_sync_reports_no_drift(self):
        led = ResidencyLedger()
        led.record_load("A", weights_gb=1.0)
        rep = led.reconcile(_server("A"))
        assert rep.only_in_server == [] and rep.only_in_ledger == []
        assert rep.in_sync is True


class TestEvictionIsPossibleWhenHealthIsDown:
    """The load-bearing outcome: without this the whole module is decoration."""

    def test_DISCRIMINATING_ledger_supplies_victims_when_health_is_down(self):
        from unittest.mock import patch

        from cohezion.inference import hotswap as h

        led = ResidencyLedger()
        led.record_load("Evictable", weights_gb=30.0)

        unloaded: list[str] = []

        # free_gb reflects STATE (has the eviction happened?), not call order — a strict
        # iter([...]) breaks whenever the implementation reads free_gb() a different number
        # of times, which is an implementation detail, not a contract.
        #
        # The numbers must also be PHYSICALLY CONSISTENT: freeing a 30GB model returns
        # 30GB (20 -> 50), not 40GB. An earlier version of this test claimed +40GB, which
        # only "passed" because the old code evicted first and measured afterwards; the
        # pre-eviction guard computes the honest figure and correctly refused it.
        # Target is sized so the eviction genuinely helps: 25 + 3 KV = 28 <= 20 - 16 + 30.
        with (
            patch.object(h, "resident_models", return_value=[]),
            patch.object(h, "_catalog_sizes", return_value={"Big": 25.0, "Evictable": 30.0}),
            patch.object(h, "free_gb", side_effect=lambda: 50.0 if unloaded else 20.0),
            patch.object(h, "unload", side_effect=lambda m, **k: (unloaded.append(m), True)[1]),
            patch.object(h, "_post", return_value=(200, "ok")),
        ):
            res = h.ensure_resident("Big", ledger=led)

        assert unloaded == ["Evictable"], (
            "with health down and a ledger supplied, the gate must still find a victim; "
            f"got evictions={unloaded} reason={res.reason!r}"
        )

    def test_without_a_ledger_behaviour_is_unchanged(self):
        """Backward compatibility: the 9 existing hotswap tests must keep passing."""
        from unittest.mock import patch

        from cohezion.inference import hotswap as h

        with (
            patch.object(h, "resident_models", return_value=[]),
            patch.object(h, "_catalog_sizes", return_value={"Big": 40.0}),
            patch.object(h, "free_gb", return_value=20.0),
        ):
            res = h.ensure_resident("Big")
        assert res.ok is False and res.evicted == []


class TestVerificationStrictnessIsPreserved:
    """The relaxation must be OPT-IN.

    HS7 ("HTTP 200 without residency is a failure") is a real safety property, and the
    first version of this change broke it: an empty ``resident_models()`` is AMBIGUOUS —
    it means both "health answered, fleet empty" and "health did not answer". Passing a
    ledger is the caller's explicit declaration that it expects a degraded /health; a
    ledger-less caller keeps the strict contract.
    """

    def _run(self, ledger):
        from unittest.mock import patch

        from cohezion.inference import hotswap as h

        with (
            patch.object(h, "resident_models", return_value=[]),
            patch.object(h, "_catalog_sizes", return_value={"M": 1.0}),
            patch.object(h, "free_gb", return_value=100.0),
            patch.object(h, "_post", return_value=(200, "ok")),
        ):
            return h.ensure_resident("M", ledger=ledger)

    def test_DISCRIMINATING_no_ledger_keeps_strict_failure(self):
        assert self._run(None).ok is False

    def test_DISCRIMINATING_with_ledger_reports_unverified_success(self):
        led = ResidencyLedger()
        res = self._run(led)
        assert res.ok is True and "UNVERIFIED" in res.reason
        assert [e["model_name"] for e in led.entries()] == ["M"]

    def test_health_answering_without_the_model_is_still_a_failure_even_with_a_ledger(self):
        """Ambiguity resolved in the other direction: if health DID answer and lacks the
        model, absence is conclusive and a ledger must not launder it into success."""
        from unittest.mock import patch

        from cohezion.inference import hotswap as h

        with (
            patch.object(h, "resident_models", return_value=_server("something-else")),
            patch.object(h, "_catalog_sizes", return_value={"M": 1.0}),
            patch.object(h, "free_gb", return_value=100.0),
            patch.object(h, "_post", return_value=(200, "ok")),
        ):
            res = h.ensure_resident("M", ledger=ResidencyLedger())
        assert res.ok is False


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
