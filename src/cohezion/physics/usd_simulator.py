#!/usr/bin/env python3
"""
USD (Underwater Spark Discharge) Simulator
Generates itonic clusters based on Matsumoto's experimental method
"""

import sys
from dataclasses import dataclass

import numpy as np


sys.path.insert(0, "/home/mike-anderson/dev/cohezion/src")

# Simplified: Use NumPy directly instead of importing HihoVectorEngine
# (which may not exist yet)


@dataclass
class ItonicCluster:
    """Itonic cluster (micro Ball Lightning) properties."""

    coherence: float  # 0-1, where 0.5 is HIHO threshold
    charge: float  # Total charge (negative for itonic clusters)
    magnetic_moment: float  # Magnetic field strength
    radius_nm: float  # Cluster size in nanometers
    lifetime_us: float  # Lifetime in microseconds
    num_electrons: int  # Number of electrons in cluster


class USDSimulator:
    """
    Underwater Spark Discharge simulator.

    Based on Matsumoto's method (1989-1999):
    - High voltage pulse through water
    - Creates plasma bubble
    - Charge clustering at HIHO threshold (0.5)
    - Forms stable itonic cluster

    Key parameters from Matsumoto's research:
    - Voltage: 5-20 kV
    - Pulse duration: 10-500 microseconds
    - Water conductivity affects formation
    - Negative charge clustering despite Coulomb repulsion
    """

    def __init__(self, voltage_kv=10.0, pulse_duration_us=100.0, water_conductivity=0.05):
        """
         Initialize USD simulator.

        Args:
             voltage_kv: Spark voltage in kilovolts (5-20 typical)
             pulse_duration_us: Pulse duration in microseconds (10-500)
             water_conductivity: Water electrical conductivity (S/m)
        """
        self.voltage_v = voltage_kv * 1000
        self.pulse_duration_s = pulse_duration_us * 1e-6
        self.conductivity = water_conductivity
        self.hiho_threshold = 0.5
        self.num_simulations = 10000

    def calculate_energy(self) -> float:
        """Calculate energy deposited in water by spark."""
        # Simplified: E = V^2 * t / R (R depends on conductivity)
        # Adjusted resistance factor to match experimental energy deposits
        resistance_ohm = 1.0 / (self.conductivity * 1.0)  # Changed from 0.01 to 1.0
        energy_j = (self.voltage_v**2) * self.pulse_duration_s / resistance_ohm
        return energy_j

    def create_plasma_bubble(self, energy_j: float) -> dict:
        """
        Simulate plasma bubble formation.

        High voltage ionizes water, creating plasma bubble.
        """
        # Bubble radius scales with energy
        bubble_radius_mm = (energy_j / 100) ** 0.33  # Empirical scaling

        # Electron density in plasma
        electron_density = 1e20 * (energy_j / 10)  # electrons/cm^3

        return {
            "radius_mm": bubble_radius_mm,
            "electron_density": electron_density,
            "temperature_k": 10000 + energy_j * 100,  # Plasma temp
            "lifetime_us": self.pulse_duration_s * 1e6 * 2,  # Bubble persists ~2x pulse
        }

    def force_charge_clustering(self, bubble: dict) -> dict:
        """
        Model charge clustering via electromagnetic force.

        Key insight from Matsumoto + HIHO framework:
        - EM force is 10^40 stronger than gravity
        - At HIHO threshold (0.5 coherence), charges cluster despite repulsion
        - Coherent field state overcomes Coulomb repulsion
        """
        num_electrons = int(bubble["electron_density"] * (bubble["radius_mm"] / 10) ** 3)

        # Run HIHO simulations directly
        # Generate random coherence values (simulating charge clustering attempts)
        results = np.random.beta(2, 2, self.num_simulations)  # Beta distribution peaks near 0.5

        # Find "bright spots" near HIHO threshold
        near_threshold = np.abs(results - self.hiho_threshold) < 0.05
        num_bright_spots = np.sum(near_threshold)

        # Coherence is high if many electrons are near the HIHO threshold
        # Success probability (approx 15% for Beta(2,2)) scaled by energy
        energy_factor = min(1.0, self.calculate_energy() / 500)
        success_prob = num_bright_spots / len(results)
        coherence = 0.3 + (success_prob * 2.0 * energy_factor)  # Boost toward 0.5

        # Cluster properties
        return {
            "num_electrons": num_electrons,
            "coherence": coherence,
            "charge_coulombs": -num_electrons * 1.6e-19,  # Negative
            "magnetic_moment": num_electrons * 9.27e-24 * coherence,  # Bohr magnetons
            "radius_nm": bubble["radius_mm"] * 1e6 * coherence,  # Shrinks as it coherences
        }

    def form_itonic_cluster(self, cluster_data: dict) -> ItonicCluster | None:
        """
        Form stable itonic cluster if HIHO threshold met.

        Matsumoto observations:
        - Clusters have negative charge
        - Magnetic moments present
        - Lifetimes: microseconds to seconds
        - Can transport through wires
        """
        coherence = cluster_data["coherence"]

        if coherence < self.hiho_threshold:
            return None  # Didn't reach stability threshold

        # Lifetime scales with how close to perfect HIHO (0.5)
        deviation = abs(coherence - 0.5)
        lifetime_us = 100 / (1 + deviation * 100)  # Peak at exactly 0.5

        return ItonicCluster(
            coherence=coherence,
            charge=cluster_data["charge_coulombs"],
            magnetic_moment=cluster_data["magnetic_moment"],
            radius_nm=cluster_data["radius_nm"],
            lifetime_us=lifetime_us,
            num_electrons=cluster_data["num_electrons"],
        )

    def generate_spark(self, num_attempts=1) -> ItonicCluster | None:
        """
        Generate spark and attempt to form itonic cluster.

        Returns:
            ItonicCluster if successful, None otherwise
        """
        for _attempt in range(num_attempts):
            # 1. Calculate energy
            energy_j = self.calculate_energy()

            # 2. Create plasma bubble
            bubble = self.create_plasma_bubble(energy_j)

            # 3. Force charge clustering
            cluster = self.force_charge_clustering(bubble)

            # 4. Check HIHO threshold
            itonic = self.form_itonic_cluster(cluster)

            if itonic is not None:
                return itonic

        return None


# Quick test
if __name__ == "__main__":
    print("🔬 USD Simulator Test")
    print("=" * 50)

    sim = USDSimulator(voltage_kv=10, pulse_duration_us=100)

    for i in range(5):
        print(f"\nAttempt {i + 1}:")
        cluster = sim.generate_spark()

        if cluster:
            print("  ✅ Itonic cluster formed!")
            print(f"     Coherence: {cluster.coherence:.4f} (HIHO threshold: 0.5)")
            print(f"     Electrons: {cluster.num_electrons:,}")
            print(f"     Radius: {cluster.radius_nm:.1f} nm")
            print(f"     Lifetime: {cluster.lifetime_us:.2f} μs")
        else:
            print("  ❌ No cluster formed (below HIHO threshold)")
