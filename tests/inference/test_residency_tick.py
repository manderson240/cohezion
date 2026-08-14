"""RS6 — the ambient reclamation pass.

The original ask was "a process for unloading and loading models on demand". `request()`
covers LOADING on demand (the synchronous path). Nothing covered UNLOADING: the router
hoards up to `max_loaded_models` and never releases an idle model, which is how the box
reached 113 GB used / 8 GB available with the count cap holding perfectly at 2.

`tick()` is that missing half — one ambient pass, safe to call on a timer:
  1. repair ledger drift from a healthy server,
  2. release idle models ONLY while under memory pressure,
  3. report what it did.

The pressure condition is load-bearing and gets a positive control: a tick that releases
models when there is no pressure is worse than none, because it destroys a warm fleet for
nothing.
"""

from __future__ import annotations

import pytest

from cohezion.inference.residency_ledger import ResidencyLedger
from cohezion.inference.residency_service import ResidencyService


def _server(*specs):
    """(name, busy) -> health-shaped rows, newest-used first."""
    return [
        {"model_name": n, "loaded": True, "is_busy": b, "last_use": 100 - i}
        for i, (n, b) in enumerate(specs)
    ]


@pytest.fixture
def svc():
    return ResidencyService(ledger=ResidencyLedger())


class TestRS6Structural:
    def test_tick_exists_and_takes_a_pressure_threshold(self):
        import inspect

        assert hasattr(ResidencyService, "tick")
        assert "pressure_gb" in inspect.signature(ResidencyService.tick).parameters


class TestRS6PressureGating:
    def test_DISCRIMINATING_releases_idle_models_under_pressure(self, monkeypatch, svc):
        from cohezion.inference import hotswap as h

        released: list[str] = []
        monkeypatch.setattr(h, "resident_models", lambda: _server(("hot", False), ("cold", False)))
        monkeypatch.setattr(h, "free_gb_or_none", lambda: 8.0)  # below the floor -> pressure
        monkeypatch.setattr(h, "free_gb", lambda: 8.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: (released.append(m), True)[1])

        out = svc.tick()
        assert released, f"under pressure nothing was released; out={out}"
        assert out["released"] == released

    def test_POSITIVE_CONTROL_releases_nothing_when_there_is_no_pressure(self, monkeypatch, svc):
        """A tick that evicts a warm fleet for no reason is worse than no tick at all."""
        from cohezion.inference import hotswap as h

        released: list[str] = []
        monkeypatch.setattr(h, "resident_models", lambda: _server(("a", False), ("b", False)))
        monkeypatch.setattr(h, "free_gb_or_none", lambda: 90.0)  # plenty
        monkeypatch.setattr(h, "free_gb", lambda: 90.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: (released.append(m), True)[1])

        out = svc.tick()
        assert released == [], "released models with no memory pressure"
        assert out["released"] == []

    def test_DISCRIMINATING_never_releases_a_BUSY_model(self, monkeypatch, svc):
        """Evicting a model mid-generation corrupts an in-flight request."""
        from cohezion.inference import hotswap as h

        released: list[str] = []
        monkeypatch.setattr(h, "resident_models", lambda: _server(("busy", True), ("idle", False)))
        monkeypatch.setattr(h, "free_gb_or_none", lambda: 4.0)
        monkeypatch.setattr(h, "free_gb", lambda: 4.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: (released.append(m), True)[1])

        svc.tick()
        assert "busy" not in released, f"evicted a BUSY model: {released}"

    def test_protected_models_survive_pressure(self, monkeypatch, svc):
        from cohezion.inference import hotswap as h

        released: list[str] = []
        monkeypatch.setattr(h, "resident_models", lambda: _server(("keep", False), ("drop", False)))
        monkeypatch.setattr(h, "free_gb_or_none", lambda: 4.0)
        monkeypatch.setattr(h, "free_gb", lambda: 4.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: (released.append(m), True)[1])

        svc.tick(protect=("keep",))
        assert "keep" not in released and "drop" in released

    def test_releases_LEAST_recently_used_first(self, monkeypatch, svc):
        """Order matters: dropping the hottest model guarantees an immediate reload."""
        from cohezion.inference import hotswap as h

        released: list[str] = []
        # newest-first: "new" then "old" -> "old" is the LRU victim
        monkeypatch.setattr(h, "resident_models", lambda: _server(("new", False), ("old", False)))
        # one release is enough to clear pressure
        monkeypatch.setattr(h, "free_gb_or_none", lambda: 40.0 if released else 4.0)
        monkeypatch.setattr(h, "free_gb", lambda: 40.0 if released else 4.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: (released.append(m), True)[1])

        svc.tick()
        assert released == ["old"], f"expected LRU-first, got {released}"

    def test_stops_as_soon_as_pressure_clears(self, monkeypatch, svc):
        from cohezion.inference import hotswap as h

        released: list[str] = []
        monkeypatch.setattr(
            h, "resident_models", lambda: _server(("a", False), ("b", False), ("c", False))
        )
        monkeypatch.setattr(h, "free_gb_or_none", lambda: 40.0 if released else 4.0)
        monkeypatch.setattr(h, "free_gb", lambda: 40.0 if released else 4.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: (released.append(m), True)[1])

        svc.tick()
        assert len(released) == 1, f"kept evicting after pressure cleared: {released}"


class TestRS6DriftAndReporting:
    def test_tick_adopts_the_server_view_repairing_ledger_drift(self, monkeypatch, svc):
        """Models loaded by something else must enter the ledger, or eviction can never
        consider them (measured live: only_in_server=['Gemma-4-E4B','Qwen3-0.6B'])."""
        from cohezion.inference import hotswap as h

        monkeypatch.setattr(h, "resident_models", lambda: _server(("elsewhere", False)))
        monkeypatch.setattr(h, "free_gb_or_none", lambda: 90.0)
        monkeypatch.setattr(h, "free_gb", lambda: 90.0)
        out = svc.tick()
        assert out["drift_repaired"] is True
        assert [e["model_name"] for e in svc._ledger.entries()] == ["elsewhere"]

    def test_tick_publishes_what_it_released(self, monkeypatch):
        from cohezion.inference import hotswap as h

        published: list[tuple[str, dict]] = []
        released: list[str] = []
        monkeypatch.setattr(h, "resident_models", lambda: _server(("cold", False)))
        monkeypatch.setattr(h, "free_gb_or_none", lambda: 40.0 if released else 4.0)
        monkeypatch.setattr(h, "free_gb", lambda: 40.0 if released else 4.0)
        monkeypatch.setattr(h, "unload", lambda m, **k: (released.append(m), True)[1])

        svc = ResidencyService(
            ledger=ResidencyLedger(), publish=lambda t, p: published.append((t, p))
        )
        svc.tick()
        assert "model_idle" in [t for t, _ in published]

    def test_tick_never_raises_when_the_server_is_unreachable(self, monkeypatch, svc):
        """The daemon calls this on a timer; one bad pass must not kill the loop."""
        from cohezion.inference import hotswap as h

        def boom():
            raise RuntimeError("health down")

        monkeypatch.setattr(h, "resident_models", boom)
        monkeypatch.setattr(h, "free_gb_or_none", lambda: 4.0)
        monkeypatch.setattr(h, "free_gb", lambda: 4.0)
        out = svc.tick()
        assert out["released"] == [] and "error" in out


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
