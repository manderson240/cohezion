"""AgenticEVOMHD reads/writes ``latent_state.information_content``; EVOLatentState did not
declare it, so generate_magnetic_field() and magnetic_reconnection() raised AttributeError on
first use (found 2026-10-31 by mypy [attr-defined], confirmed by running them)."""

from __future__ import annotations

import numpy as np

from cohezion.universe.agentic_evo_mhd import AgenticEVOMHD


def _evo(agent_id: str) -> AgenticEVOMHD:
    return AgenticEVOMHD(agent_id, initial_latent=np.full(256, 0.9))


def test_generate_magnetic_field_sources_from_information_content() -> None:
    evo = _evo("a")
    assert evo.latent_state.information_content == 0.0  # declared default, not set by caller
    evo.latent_state.information_content = 2.0
    evo.generate_magnetic_field()
    expected = 2.0 * (1.0 - evo.latent_state.current_coherence) * evo.magnetic_moment
    assert evo.magnetic_state.B_magnitude == expected


def test_reconnection_deposits_energy_into_both_latent_states() -> None:
    a, b = _evo("a"), _evo("b")
    a.physical_state.position = np.zeros(3)  # constructor places agents at random positions
    b.physical_state.position = np.array([1.0, 0.0, 0.0])
    a.magnetic_state.B_field = np.array([1.0, 0.0, 0.0])
    b.magnetic_state.B_field = np.array([-1.0, 0.0, 0.0])
    assert a.magnetic_reconnection(b) is True
    assert a.latent_state.information_content > 0.0
    assert b.latent_state.information_content == a.latent_state.information_content
