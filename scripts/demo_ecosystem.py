#!/usr/bin/env python3
"""
Demo: Living Manifold Ecosystem
Run a short simulation of the quantum-bioelectric-AI ecosystem.
"""

import sys

sys.path.insert(0, "/home/mike-anderson/dev/cohezion-session-56/src")

from cohezion.quantum import LivingManifoldEcosystem
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


def main():
    """Run ecosystem demo."""
    print("\n" + "=" * 70)
    print("LIVING MANIFOLD ECOSYSTEM DEMO")
    print("=" * 70 + "\n")

    # Create ecosystem
    print("Initializing ecosystem with 1,000 agents...")
    ecosystem = LivingManifoldEcosystem(n_agents=1000, device="cpu")

    # Run simulation
    print("\nRunning 100 epochs...\n")
    metrics_history = ecosystem.run_simulation(n_epochs=100, log_interval=10)

    # Print summary
    print("\n" + "=" * 70)
    print("FINAL SUMMARY")
    print("=" * 70 + "\n")

    stats = ecosystem.get_summary_statistics()

    print(f"Total Epochs: {stats['total_epochs']}")
    print(f"Initial Population: {stats['initial_population']}")
    print(f"Final Population: {stats['final_population']}")
    print(f"Min Population: {stats['min_population']}")
    print(f"Max Population: {stats['max_population']}")
    print(f"Total Births: {stats['total_births']}")
    print(f"Total Deaths: {stats['total_deaths']}")
    print(f"Average Coherence: {stats['avg_coherence']:.3f}")
    print(f"Final Coherence: {stats['final_coherence']:.3f}")
    print(f"Energy Equilibrium: {stats['energy_equilibrium_final']:.3f}")

    # Get sample agent
    sample_agent = ecosystem.get_agent_details(0)
    if sample_agent:
        print(f"\nSample Agent #0:")
        print(f"  Age: {sample_agent['age']}")
        print(f"  Coherence: {sample_agent['coherence']:.3f}")
        print(f"  Energy: {sample_agent['energy']:.3f}")
        print(f"  Journey Quality: {sample_agent['journey_quality']:.3f}")

    print("\n" + "=" * 70)
    print("DEMO COMPLETE")
    print("=" * 70 + "\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
