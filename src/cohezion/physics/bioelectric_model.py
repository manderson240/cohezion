"""Bioelectric Network Model — Levin-inspired collective intelligence dynamics.

Implements Michael Levin's bioelectric framework as a computational model:
  - N cells with transmembrane potential V_mem (analogous to agent coherence)
  - Gap junction conductance matrix G_ij (analogous to gauge field coupling)
  - Network diffusion dynamics: C dV/dt = -Σ G_ij(V_i - V_j) + I_ion
  - Cognitive light cone: R_c ∝ √(D × τ) — spatial extent of collective intelligence
  - HIHO percolation threshold: G_c — phase transition from individual to collective

The key insight (Levin 2019, 2022): below the gap junction coupling threshold G_c,
cells act as independent agents. Above G_c, they merge into a collective agent with
a shared cognitive light cone, unified goal states, and emergent morphogenetic memory.

This IS the HIHO phase transition in biological form.

References:
  - Levin, M. (2019). "The Computational Boundary of a 'Self'" Frontiers in Psychology
  - Levin, M. (2022). "Technological Approach to Mind Everywhere" Frontiers in Systems Neuroscience
  - Fields, C. & Levin, M. (2022). "Competency in Navigating Arbitrary Spaces" Entropy
  - Kriegman, S. et al. (2020). "A scalable pipeline for reconfigurable organisms" PNAS
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class CognitiveLightCone:
    """The spatio-temporal horizon of a cognitive agent (Levin 2019).

    R_c = spatial radius within which the agent can detect and correct errors.
    τ = temporal horizon (how far into the future the agent can plan).
    """

    radius: float  # Spatial extent (√(D × τ))
    temporal_horizon: float  # Planning horizon
    agent_ids: list[int] = field(default_factory=list)  # Cells/agents in this cone
    is_collective: bool = False  # True if cone spans multiple cells


@dataclass
class PercolationResult:
    """Result of percolation analysis on the gap junction network."""

    is_percolated: bool  # True if giant connected component exists
    largest_cluster_size: int  # Size of the largest cluster
    cluster_count: int  # Total number of clusters
    critical_conductance: float  # Estimated G_c threshold
    clusters: list[list[int]] = field(default_factory=list)


class BioelectricNetwork:
    """A network of N cells coupled through gap junctions.

    Each cell has a membrane potential V_i (analogous to agent coherence).
    Cells communicate through gap junctions with conductance G_ij.
    The network dynamics follow the cable equation:

        C_i × dV_i/dt = -Σ_j G_ij(V_i - V_j) + I_ion,i(V_i)

    This is formally identical to a resistor-capacitor network — an analog computer.
    """

    def __init__(
        self,
        n_cells: int = 16,
        capacitance: float = 1.0,
        resting_potential: float = -0.5,
    ) -> None:
        self.n_cells = n_cells
        self.capacitance = capacitance
        self.resting_potential = resting_potential

        # Membrane potentials: V_i ∈ [-1, 1] (normalized)
        # Start at resting potential with small noise
        rng = np.random.default_rng(seed=42)
        self.v_mem = np.full(n_cells, resting_potential) + rng.normal(0, 0.05, n_cells)

        # Gap junction conductance matrix: G_ij ≥ 0
        self.conductance = np.zeros((n_cells, n_cells))

        # Autonomous ion channel current per cell (leak current toward resting potential)
        self.leak_conductance = 0.1

    def set_conductance(self, i: int, j: int, g: float) -> None:
        """Set gap junction conductance between cells i and j (symmetric)."""
        self.conductance[i, j] = g
        self.conductance[j, i] = g

    def set_uniform_conductance(self, g: float) -> None:
        """Set all gap junction conductances to the same value (nearest-neighbor)."""
        for i in range(self.n_cells):
            for j in range(i + 1, self.n_cells):
                # Connect nearest neighbors (1D ring topology)
                if abs(i - j) == 1 or (i == 0 and j == self.n_cells - 1):
                    self.set_conductance(i, j, g)

    def set_full_conductance(self, g: float) -> None:
        """Set all-to-all gap junction coupling (complete graph)."""
        for i in range(self.n_cells):
            for j in range(i + 1, self.n_cells):
                self.set_conductance(i, j, g)

    def step(self, dt: float = 0.01) -> np.ndarray:
        """Advance the network by one timestep using the cable equation.

        C_i × dV_i/dt = -Σ_j G_ij(V_i - V_j) + I_leak,i
        """
        # Gap junction currents: I_gj,i = -Σ_j G_ij(V_i - V_j)
        i_gj = -np.sum(self.conductance * (self.v_mem[:, None] - self.v_mem[None, :]), axis=1)

        # Leak current toward resting potential: I_leak = g_leak × (V_rest - V_i)
        i_leak = self.leak_conductance * (self.resting_potential - self.v_mem)

        # Update: C × dV/dt = I_gj + I_leak
        dv_dt = (i_gj + i_leak) / self.capacitance
        self.v_mem += dv_dt * dt

        # Clamp to [-1, 1]
        self.v_mem = np.clip(self.v_mem, -1.0, 1.0)

        return self.v_mem.copy()

    def simulate(self, n_steps: int = 100, dt: float = 0.01) -> np.ndarray:
        """Run the network for n_steps and return the trajectory.

        Returns shape (n_steps + 1, n_cells) — the full V_mem history.
        """
        trajectory = np.zeros((n_steps + 1, self.n_cells))
        trajectory[0] = self.v_mem.copy()
        for t in range(n_steps):
            self.step(dt)
            trajectory[t + 1] = self.v_mem.copy()
        return trajectory

    def coherence(self) -> float:
        """Compute network coherence — how synchronized are the cells?

        Returns a value in [0, 1] where:
          0 = maximum variance (fully independent)
          1 = zero variance (perfect synchronization / collective)

        The HIHO state is at coherence = 0.5 (half-independent, half-collective).
        """
        if self.n_cells <= 1:
            return 1.0
        v_range = np.ptp(self.v_mem)  # peak-to-peak range
        # Normalize: 0 when range = 2 (max), 1 when range = 0 (sync)
        return float(1.0 - min(v_range / 2.0, 1.0))

    def information_capacity(self, v_resolution: float = 0.01) -> float:
        """Compute the information capacity of the network (bits).

        I ~ N × log₂(V_range / δV)

        For N=10⁶ cells, 60 mV range, 1 mV resolution: ~6 Mbit
        (sufficient for anatomical target morphology).
        """
        v_dynamic_range = 2.0  # [-1, 1] normalized
        bits_per_cell = np.log2(v_dynamic_range / v_resolution)
        return float(self.n_cells * bits_per_cell)

    def cognitive_light_cone(self) -> CognitiveLightCone:
        """Compute the cognitive light cone from network properties.

        R_c ∝ √(D × τ) where:
          D = effective diffusion coefficient (from average gap junction conductance)
          τ = pattern memory timescale (from leak conductance inverse)
        """
        # Average gap junction conductance (effective diffusion coefficient)
        total_conductance = np.sum(self.conductance)
        n_connections = np.count_nonzero(self.conductance) / 2  # symmetric
        if n_connections == 0:
            return CognitiveLightCone(
                radius=0.0,
                temporal_horizon=0.0,
                agent_ids=list(range(self.n_cells)),
                is_collective=False,
            )

        d_eff = total_conductance / max(n_connections, 1)

        # Pattern memory timescale: inverse of leak rate
        tau = 1.0 / max(self.leak_conductance, 1e-10)

        # Cognitive light cone radius
        radius = float(np.sqrt(d_eff * tau))

        # Determine which cells are in the collective
        percolation = self.percolation_analysis()
        is_collective = percolation.is_percolated

        return CognitiveLightCone(
            radius=radius,
            temporal_horizon=tau,
            agent_ids=list(range(self.n_cells)),
            is_collective=is_collective,
        )

    def percolation_analysis(self, threshold: float = 0.01) -> PercolationResult:
        """Analyze the gap junction network for percolation (HIHO threshold).

        When gap junction conductance exceeds G_c (the percolation threshold),
        a giant connected component emerges — the cells merge into a collective
        agent. This IS the HIHO phase transition in biological form.
        """
        # Build adjacency from conductance matrix
        connected = self.conductance > threshold

        # Find connected components via union-find
        parent = list(range(self.n_cells))

        def find(x: int) -> int:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(a: int, b: int) -> None:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[ra] = rb

        for i in range(self.n_cells):
            for j in range(i + 1, self.n_cells):
                if connected[i, j]:
                    union(i, j)

        # Identify clusters
        cluster_map: dict[int, list[int]] = {}
        for i in range(self.n_cells):
            root = find(i)
            cluster_map.setdefault(root, []).append(i)

        clusters = list(cluster_map.values())
        largest = max(len(c) for c in clusters) if clusters else 0

        # Percolated if largest cluster > 50% of cells
        is_percolated = largest > self.n_cells / 2

        # Estimate critical conductance (mean conductance of connected edges)
        connected_conductances = self.conductance[connected]
        g_c = float(np.mean(connected_conductances)) if len(connected_conductances) > 0 else 0.0

        return PercolationResult(
            is_percolated=is_percolated,
            largest_cluster_size=largest,
            cluster_count=len(clusters),
            critical_conductance=g_c,
            clusters=clusters,
        )

    def hiho_deviation(self) -> float:
        """Compute how far the network is from the HIHO state.

        HIHO = coherence at 0.5 (half-independent, half-collective).
        Returns δ = |coherence - 0.5|.
        """
        return abs(self.coherence() - 0.5)

    def to_dict(self) -> dict:
        """Serialize for API and SurrealDB persistence."""
        cone = self.cognitive_light_cone()
        perc = self.percolation_analysis()
        return {
            "n_cells": self.n_cells,
            "v_mem": self.v_mem.tolist(),
            "coherence": self.coherence(),
            "hiho_deviation": self.hiho_deviation(),
            "information_capacity_bits": self.information_capacity(),
            "cognitive_light_cone": {
                "radius": cone.radius,
                "temporal_horizon": cone.temporal_horizon,
                "is_collective": cone.is_collective,
            },
            "percolation": {
                "is_percolated": perc.is_percolated,
                "largest_cluster_size": perc.largest_cluster_size,
                "cluster_count": perc.cluster_count,
                "critical_conductance": perc.critical_conductance,
            },
        }


__all__ = [
    "BioelectricNetwork",
    "CognitiveLightCone",
    "PercolationResult",
]
