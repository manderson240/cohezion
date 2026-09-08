#!/usr/bin/env python3
"""Consolidated physics/universe demo runner.

Demo functions moved verbatim out of library modules (elegant-simplicity
audit 2026-08-14): universe/agentic_evo_swift.py and universe/agentic_evo_mhd.py. Library classes are untouched.

Usage:
    uv run python scripts/demos/physics_demos.py [swift|mhd]
"""

from __future__ import annotations

import sys

from cohezion.universe.agentic_evo_mhd import AgenticMHDSystem, IonizationState
from cohezion.universe.agentic_evo_swift import AgenticEVOSimulation


def demo_agentic_evo_simulation():
    """Demonstrate agentic EVO simulation."""
    print("=" * 70)
    print("AGENTIC EVO JOURNEY SIMULATION")
    print("FLUME Latent Space + SWIFT Physical Space + EVO Coupling")
    print("=" * 70)

    print("\nInitializing 100 EVO agents...")
    sim = AgenticEVOSimulation(n_evos=100, box_size=1000.0)

    stats = sim.get_statistics()
    print(f"  Standard EVOs: {stats['n_evos'] - stats['n_exotic']}")
    print(f"  Exotic EVOs: {stats['n_exotic']}")
    print(f"  Initial coherence: {stats['avg_coherence']:.3f}")

    print("\nRunning 100 coupled timesteps...")
    for step in range(100):
        sim.step(dt=0.01)

        if step % 20 == 0:
            stats = sim.get_statistics()
            print(
                f"  Step {step}: coherence={stats['avg_coherence']:.3f}, "
                f"journey_len={stats['total_journey_steps']}"
            )

    print("\n" + "=" * 70)
    print("GENERATING SWIFT INITIAL CONDITIONS")
    print("=" * 70)

    ics_path = "/tmp/evo_swift_ics.hdf5"
    sim.generate_swift_ics(ics_path)

    print("\n" + "=" * 70)
    print("FINAL STATISTICS")
    print("=" * 70)

    stats = sim.get_statistics()
    print(f"Total timesteps: {stats['timestep']}")
    print(f"Total journey steps: {stats['total_journey_steps']}")
    print(f"Final coherence: {stats['avg_coherence']:.3f}")
    print(f"ICs ready for SWIFT at: {ics_path}")

    print("\nTo run with SWIFT:")
    print(f"  mpirun -np 4 ./swift --self-gravity --hydro {ics_path}")

    return sim


def demo_mhd_simulation():
    """Demonstrate MHD EVO simulation."""
    print("=" * 70)
    print("AGENTIC EVO WITH MHD (Magnetohydrodynamics)")
    print("Coupling: FLUME↔MHD Fields↔Plasma Dynamics")
    print("=" * 70)

    print("\nInitializing 50 MHD-EVOs on 32³ grid...")
    system = AgenticMHDSystem(n_evos=50, grid_size=(32, 32, 32), box_size=100.0)

    stats = system.get_mhd_statistics()
    print(f"  Standard: {stats['n_evos'] - stats['ionized'] - stats['exotic_plasma']}")
    print(f"  Plasma (ionized): {stats['ionized']}")
    print(f"  Exotic plasma: {stats['exotic_plasma']}")
    print(f"  Initial mean |B|: {stats['mean_b_field']:.4f}")

    print("\nRunning 50 MHD timesteps...")
    print("Tracking: Div B errors, Reconnections, Plasma states")

    for step in range(50):
        mhd_info = system.step(dt=0.01)

        if step % 10 == 0:
            stats = system.get_mhd_statistics()
            print(
                f"  Step {step}: DivB={mhd_info['max_div_b']:.2e}, "
                f"Rc={mhd_info['reconnections']}, "
                f"<B>={stats['mean_b_field']:.3f}, "
                f"β={stats['mean_plasma_beta']:.2f}"
            )

    print("\n" + "=" * 70)
    print("FINAL MHD STATISTICS")
    print("=" * 70)

    stats = system.get_mhd_statistics()
    print(f"Timesteps: {stats['timestep']}")
    print("Final plasma states:")
    print(
        f"  Neutral: {sum(1 for e in system.evos if e.magnetic_state.ionization_state == IonizationState.NEUTRAL)}"
    )
    print(
        f"  Partially ionized: {sum(1 for e in system.evos if e.magnetic_state.ionization_state == IonizationState.PARTIALLY_IONIZED)}"
    )
    print(
        f"  Fully ionized: {sum(1 for e in system.evos if e.magnetic_state.ionization_state == IonizationState.FULLY_IONIZED)}"
    )
    print(f"  Exotic plasma: {stats['exotic_plasma']}")
    print("\nMagnetic field statistics:")
    print(f"  Mean |B|: {stats['mean_b_field']:.4f}")
    print(f"  Mean plasma β: {stats['mean_plasma_beta']:.2f}")
    print(f"  Max ∇·B error: {stats['max_div_b_error']:.2e}")

    print("\n" + "=" * 70)
    print("MHD SIMULATION COMPLETE")
    print("=" * 70)
    print("\nTo couple with SWIFT:")
    print("  1. Export B-field grid to SWIFT MHD ICs")
    print("  2. Include ionization fractions in particle data")
    print("  3. Run with --mhd flag in SWIFT")

    return system


def main() -> None:
    which = sys.argv[1] if len(sys.argv) > 1 else "swift"
    if which == "swift":
        demo_agentic_evo_simulation()
    elif which == "mhd":
        demo_mhd_simulation()
    else:
        raise SystemExit(f"unknown demo {which!r} — pick swift|mhd")


if __name__ == "__main__":
    main()
