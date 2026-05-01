#!/usr/bin/env python3
"""
Overnight Quantum-Spin Triune Experiment

Fundamental unit: SPIN (not position/momentum)
- Spin-½ as basis (Pauli matrices)
- 12D = 4 spinor spaces × 3 dimensions
- Awareness of nothing (void at 0.5)
- Percival Triune mapped to spin eigenstates
- Closed-form evolution (no quadrature)
- Runs until 7 AM EST
"""

import json
import sys
import time
from datetime import datetime, timedelta, timezone

import numpy as np


sys.path.insert(0, 'src')

EST = timezone(timedelta(hours=-5))
NOW = datetime.now(EST)
TARGET = NOW.replace(hour=7, minute=0, second=0, microsecond=0)
if TARGET <= NOW:
    TARGET += timedelta(days=1)

print('='*70)
print('QUANTUM-SPIN TRIUNE OVERNIGHT EXPERIMENT')
print('='*70)
print('Fundamental Unit: SPIN (not position)')
print('Duration:', str(TARGET - NOW))
print('='*70)
print()

# Pauli matrices (fundamental spin-½)
PAULI_X = np.array([[0, 1], [1, 0]], dtype=complex)
PAULI_Y = np.array([[0, -1j], [1j, 0]], dtype=complex)
PAULI_Z = np.array([[1, 0], [0, -1]], dtype=complex)

# Identity (the "nothing" - awareness of void)
IDENTITY = np.eye(2, dtype=complex)

# Spinors for 12D (6 spin-½ systems)
# 12 real dims = 6 complex dims = 6 spinor spaces

def create_spinor_state(dims=6):
    """Create normalized spinor state for 6 spin-½ systems."""
    # Random complex amplitudes
    real = np.random.randn(dims, 2, 2)
    imag = np.random.randn(dims, 2, 2)
    state = real + 1j * imag
    # Normalize
    norm = np.linalg.norm(state)
    return state / norm

def measure_spin_z(state, site):
    """Measure Sz at given site (eigenvalue ±½)."""
    spin_state = state[site]
    # Expectation value <ψ|Sz|ψ>
    sz_exp = np.trace(spin_state @ PAULI_Z @ spin_state.conj().T)
    return np.real(sz_exp) / 2

def spin_hamiltonian_closed_form(state, coupling_map):
    """
    Closed-form spin evolution (no quadrature).
    Uses exact diagonalization for small systems.
    """
    new_state = np.zeros_like(state)
    for i in range(len(state)):
        # Local spin term: σz rotation
        rotation = np.cos(coupling_map[i]) * IDENTITY - 1j * np.sin(coupling_map[i]) * PAULI_Z
        new_state[i] = rotation @ state[i] @ rotation.conj().T
    return new_state

# Initialize
print('[Initializing 6-Site Spinor System (12 real dimensions)]')
spinor_state = create_spinor_state(6)

# Coupling constants for 4 fabrics mapped to 6 spin sites
# Site 0-1: Space (Doer) - Physical grounding
# Site 2-3: Field/Control (Thinker) - Reasoning
# Site 4-5: Precipitation (Knower) - Intent/Void

couplings = {
    'Space': {'sites': [0, 1], 'J': 1.0, 'fabric': 'Space'},
    'Field': {'sites': [2, 3], 'J': 0.7, 'fabric': 'Field'},
    'Precip': {'sites': [4, 5], 'J': 0.3, 'fabric': 'Precipitation'}
}

print('Site mapping:')
print('  Sites 0-1 (Space):     J=1.0  → Doer (Physical)')
print('  Sites 2-3 (Field):     J=0.7  → Thinker (Reasoning)')
print('  Sites 4-5 (Precip):    J=0.3  → Knower (Intent/Void)')
print()

metrics_log = []
iteration = 0
start = time.time()
next_log = start + 900

print('[Starting evolution - logging every 15 minutes]')
print()

try:
    while datetime.now(EST) < TARGET:
        iteration += 1

        # === CLOSED-FORM SPIN EVOLUTION ===
        # No quadrature - exact unitary rotation

        # Apply fabric-specific couplings
        coupling_array = np.array([1.0, 1.0, 0.7, 0.7, 0.3, 0.3])

        # Evolution: U = exp(-iHt) ≈ (cos(θ)I - i sin(θ) σz) for each site
        dt = 0.01
        for site in range(6):
            theta = coupling_array[site] * dt
            U = np.cos(theta) * IDENTITY - 1j * np.sin(theta) * PAULI_Z
            spinor_state[site] = U @ spinor_state[site] @ U.conj().T

        # === AWARENESS OF NOTHING ===
        # The void is the identity component - measure trace
        void_awareness = np.abs(np.trace(spinor_state[0])) / 2

        # === PERCIVAL TRIUNE MEASUREMENTS ===
        # Doer (sites 0-1): Physical spin alignment
        doer_spin = (measure_spin_z(spinor_state, 0) + measure_spin_z(spinor_state, 1)) / 2

        # Thinker (sites 2-3): Reasoning/correlation
        thinker_spin = (measure_spin_z(spinor_state, 2) + measure_spin_z(spinor_state, 3)) / 2

        # Knower (sites 4-5): Intent/Void
        knowers_spin = (measure_spin_z(spinor_state, 4) + measure_spin_z(spinor_state, 5)) / 2

        # === HIHO ATTRACTOR (0.5) ===
        # Distance from 0.5 (the balance point)
        doer_dist = abs(doer_spin - 0.5)
        thinker_dist = abs(thinker_spin - 0.5)
        knower_dist = abs(knowers_spin - 0.5)

        # Log every 15 min
        if time.time() >= next_log:
            elapsed = (time.time() - start) / 60

            log = {
                'timestamp': datetime.now(EST).isoformat(),
                'elapsed_min': round(elapsed, 2),
                'iteration': iteration,
                'spin': {
                    'doer': round(float(doer_spin), 4),
                    'thinker': round(float(thinker_spin), 4),
                    'knower': round(float(knowers_spin), 4)
                },
                'void_awareness': round(float(void_awareness), 4),
                'dist_from_0.5': {
                    'doer': round(float(doer_dist), 4),
                    'thinker': round(float(thinker_dist), 4),
                    'knower': round(float(knower_dist), 4)
                }
            }

            metrics_log.append(log)

            ts = datetime.now(EST).strftime('%H:%M:%S')
            print(f"[{ts}] Iter:{iteration:7d} | "
                  f"Doer:{doer_spin:7.4f} | Thinker:{thinker_spin:7.4f} | "
                  f"Knower:{knowers_spin:7.4f} | Void:{void_awareness:7.4f} | "
                  f"{elapsed:.1f}min")

            # Checkpoint
            with open('spin_checkpoint.json', 'w') as f:
                json.dump({'current': log, 'target': TARGET.isoformat()}, f)

            next_log = time.time() + 900

        time.sleep(0.001)

except KeyboardInterrupt:
    print('\nInterrupted')

finally:
    duration = (time.time() - start) / 60

    print()
    print('='*70)
    print('SPIN-TRIUNE EXPERIMENT COMPLETE')
    print('='*70)
    print(f'Duration: {duration:.1f} minutes')
    print(f'Iterations: {iteration}')
    print(f'Spin evolutions: {iteration}')

    if metrics_log:
        final = metrics_log[-1]
        print('\nFinal Spinstate:')
        print(f"  Doer:    {final['spin']['doer']:+.4f} (dist from 0.5: {final['dist_from_0.5']['doer']:.4f})")
        print(f"  Thinker: {final['spin']['thinker']:+.4f} (dist from 0.5: {final['dist_from_0.5']['thinker']:.4f})")
        print(f"  Knower:  {final['spin']['knower']:+.4f} (dist from 0.5: {final['dist_from_0.5']['knower']:.4f})")
        print(f"  Void awareness: {final['void_awareness']:.4f}")

        with open('spin_results.json', 'w') as f:
            json.dump({
                'experiment': 'quantum_spin_triune',
                'fundamental': 'spin',
                'duration_min': duration,
                'iterations': iteration,
                'metrics': metrics_log
            }, f, indent=2)

    print(f"\nMETRIC spin_duration={duration:.0f}")
