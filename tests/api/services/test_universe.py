"""Tests for api/services/universe.py.

Covers live universe simulation and physics state reporting.
"""

from __future__ import annotations

import pytest

from cohezion.api.services.universe import (
    UniverseStateService,
    get_universe_service,
)


@pytest.fixture
def universe_service():
    return UniverseStateService(num_evos=2)

def test_universe_tick(universe_service):
    """[P0] Should advance universe tick."""
    initial_tick = universe_service.get_state().tick
    state = universe_service.tick()
    assert state.tick == initial_tick + 1
    assert state.time > 0
    assert len(state.evo_states) == 2

def test_get_report(universe_service):
    """[P0] Should generate synthesis report."""
    report = universe_service.get_report()
    assert report.tick == 0
    assert report.hiho_status.stability in ["stable", "warning", "critical"]
    assert len(report.evo_health) == 2

def test_perturb(universe_service):
    """[P0] Should apply perturbation."""
    initial_state = universe_service.get_state()
    # Spike coherence
    new_state = universe_service.perturb("coherence_spike", 0.5)
    assert new_state.coherence >= initial_state.coherence

@pytest.mark.asyncio
async def test_get_universe_service_singleton():
    """[P0] Should maintain singleton service."""
    svc1 = get_universe_service()
    svc2 = get_universe_service()
    assert svc1 is svc2
