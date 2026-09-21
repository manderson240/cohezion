"""tests/inference fixtures: keep mocked fleet tests off the live :13305 router."""

from __future__ import annotations

import pytest


@pytest.fixture(autouse=True)
def _fleet_live_probes_report_unknown(request, monkeypatch):
    """`fleet.route()` asks the live router which models are resident and which recipes are
    healthy. Tests here register FAKE model ids, so an UP router made them "(not-loaded)" and a
    slow one made them pass: 4 failures then 0 on back-to-back runs of one tree (2026-09-21).
    Stub both probes to None -- the documented "unknown -> fail-open" state -- and drop the
    15 s module caches. Tests that patch a probe still override this; tests marked
    `integration` exercise the real router and are left alone.
    """
    if request.node.get_closest_marker("integration"):
        yield
        return
    from cohezion.inference import fleet as fleet_mod

    async def _unknown():
        return None

    monkeypatch.setattr(fleet_mod, "_get_lemonade_loaded_models", _unknown)
    monkeypatch.setattr(fleet_mod, "_get_lemonade_health", _unknown)
    monkeypatch.setattr(fleet_mod, "_LEMONADE_LOADED_MODELS", None)
    monkeypatch.setattr(fleet_mod, "_LEMONADE_LAST_RESULT", None)
    yield
