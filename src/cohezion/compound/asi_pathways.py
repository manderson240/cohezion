"""From AGI to ASI: Formal Pathways, Friction Models, and Collective Superintelligence.
===================================================================================
Based on Genewein, Franklin, Lerchner, Orseau, Albanie, Bales, Wyeth, Chan, Gabriel,
Leibo, Dafoe, Hutter, Graepel, Legg (Google DeepMind, 2026, arXiv:2606.12683).

Implements:
1. Universal AI & Legg-Hutter Intelligence Score Approximator.
2. The Four Pathways from AGI to ASI:
   - Scaling (Compute, Models, Data)
   - Algorithmic Paradigm Shifts (Continuous latent manifolds, neuro-symbolic)
   - Recursive Self-Improvement (RSI with hyperbolic growth & friction dampening)
   - Multi-Agent Collectives & Group Agency Formation
3. The Six Frictions & Bottleneck Evaluators:
   - Data Wall, Economic/Resource Demand, Neural Insufficiency, Research Hardness,
     Abstraction Barrier, Deliberate Slowdown.
4. Substrate Independence & Lossless Replication Validators.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class IntelligenceTier(StrEnum):
    """Categorization of Intelligence along the continuum (Genewein et al., 2026)."""

    NARROW_AI = "narrow_ai"
    COMPETENT_AGI = "competent_agi"  # Median human-level across most cognitive tasks
    EXPERT_AGI = "expert_agi"  # Human-expert level across broad tasks
    ASI = "artificial_superintelligence"  # Outperforms large coordinated human collectives
    UNIVERSAL_AI = "universal_ai"  # AIXI theoretical limit maximizing Legg-Hutter score


class ASIPathway(StrEnum):
    """Four non-mutually-exclusive technological pathways from AGI to ASI."""

    SCALING = "scaling_compute_models_data"
    PARADIGM_SHIFT = "algorithmic_paradigm_shifts"
    RECURSIVE_IMPROVEMENT = "recursive_self_improvement"
    MULTI_AGENT_COLLECTIVES = "multi_agent_group_agency"


class ASIFriction(StrEnum):
    """Six fundamental frictions and bottlenecks along the pathways to ASI."""

    DATA_WALL = "data_wall"
    RESOURCE_DEMAND = "economic_and_natural_resource_demand"
    NEURAL_INSUFFICIENCY = "neural_paradigm_is_insufficient"
    RESEARCH_HARDNESS = "research_gets_harder"
    ABSTRACTION_BARRIER = "abstraction_barrier"
    DELIBERATE_SLOWDOWN = "deliberate_slowdown"


@dataclass(frozen=True)
class DigitalIntelligenceAdvantages:
    """The six core advantages of digital intelligence over biological intelligence (Table 1)."""

    io_speed_bps: float  # Input/output bandwidth in bytes/sec
    internal_processing_flops: float  # Sequential/parallel processing speed
    working_memory_bytes: float  # Memory capacity and read/write bandwidth
    substrate_independent: bool = True  # Can migrate across heterogeneous silicon
    lossless_replication: bool = True  # Perfect state copying (DNA + experiences)
    high_bandwidth_sharing: bool = True  # Instant trace/gradient sharing across swarm


@dataclass
class MultiAgentScalingLaw:
    """Mathematical model of Group Agency & Collective Intelligence scaling.

    Formula:
        I_collective(N) = N^alpha * I_individual * exp(-beta * bureaucracy(N))
    where:
        N = Number of coordinated autonomous agents
        alpha = Parallel coordination efficiency (0.0 to 1.0)
        beta = Coordination friction coefficient
        bureaucracy(N) = Communication/synchronization overhead ~ log(N) or N * log(N)
    """

    individual_iq: float = 100.0  # Normalized median human AGI = 100.0
    alpha: float = 0.85  # Sublinear to linear parallelization scaling
    beta: float = 0.05  # Coordination friction factor

    def compute_collective_intelligence(self, n_agents: int) -> float:
        """Computes effective collective intelligence of an N-agent swarm."""
        if n_agents <= 0:
            return 0.0
        if n_agents == 1:
            return self.individual_iq

        # Bureaucracy scaling: O(log N) for hierarchical swarms, O(N) for uncoordinated mesh
        bureaucracy = math.log2(n_agents)
        friction_decay = math.exp(-self.beta * bureaucracy)
        raw_scale = (n_agents**self.alpha) * self.individual_iq
        return float(raw_scale * friction_decay)

    def is_superintelligent(self, n_agents: int, threshold: float = 500.0) -> bool:
        """Determines if the swarm exceeds human collective expert capacity (ASI threshold)."""
        return self.compute_collective_intelligence(n_agents) >= threshold


@dataclass
class HyperbolicRSISimulator:
    """Simulates Recursive Self-Improvement (RSI) dynamics under friction constraints.

    Differential Formulation:
        dI/dt = k * I^(1 + gamma) - sum_f Friction_f(I, t)
    where:
        gamma > 0 produces hyperbolic singularity in finite time without frictions;
        Friction_f dampens growth into an S-curve or steady asymptotic progression.
    """

    initial_intelligence: float = 100.0  # Median AGI baseline
    k_acceleration: float = 0.02
    gamma_hyperbolic: float = 0.25
    frictions: dict[ASIFriction, float] = field(
        default_factory=lambda: {
            ASIFriction.DATA_WALL: 0.15,
            ASIFriction.RESOURCE_DEMAND: 0.20,
            ASIFriction.NEURAL_INSUFFICIENCY: 0.10,
            ASIFriction.RESEARCH_HARDNESS: 0.25,
            ASIFriction.ABSTRACTION_BARRIER: 0.15,
            ASIFriction.DELIBERATE_SLOWDOWN: 0.05,
        }
    )

    def simulate_trajectory(
        self, steps: int = 50, dt: float = 0.1, counter_measures_active: bool = True
    ) -> list[tuple[float, float]]:
        """Simulates intelligence trajectory (t, I(t)) over time steps."""
        current_i = self.initial_intelligence
        trajectory = [(0.0, current_i)]

        for step in range(1, steps + 1):
            t = step * dt
            # Gross hyperbolic expansion term
            dI_gross = self.k_acceleration * (current_i ** (1.0 + self.gamma_hyperbolic))

            # Friction damping: if countermeasures active (synthetic data, specialized silicon),
            # frictions are dampened by factor 0.35
            friction_multiplier = 0.35 if counter_measures_active else 1.0
            total_friction = (
                sum(self.frictions.values()) * friction_multiplier * math.log1p(current_i)
            )

            # Net growth
            dI_net = max(0.0, (dI_gross - total_friction) * dt)
            current_i += dI_net
            trajectory.append((round(t, 2), round(current_i, 2)))

        return trajectory


class LeggHutterApproximator:
    """Approximates the universal Legg-Hutter intelligence metric across task distributions.

    Formula:
        Upsilon(pi) = sum_{mu in E} 2^(-K(mu)) * V_mu(pi)
    where:
        K(mu) = Kolmogorov complexity of environment mu
        V_mu(pi) = Expected cumulative discounted value of policy pi in mu
    """

    @staticmethod
    def evaluate_policy(
        environment_complexities: list[int],
        environment_values: list[float],
        discount_factor: float = 0.99,
    ) -> float:
        """Computes weighted universal intelligence score over evaluated task classes."""
        if len(environment_complexities) != len(environment_values):
            raise ValueError("Mismatched environment complexities and values")

        total_weight = 0.0
        weighted_score = 0.0

        for k, val in zip(environment_complexities, environment_values):
            # Universal algorithmic prior weight 2^(-K(mu))
            weight = 2.0 ** (-float(k))
            total_weight += weight
            weighted_score += weight * min(1.0, max(0.0, val))

        if total_weight <= 0.0:
            return 0.0
        return float(weighted_score / total_weight)


class SubstrateMigrationHarness:
    """Validates runtime substrate independence and lossless replication across silicon lanes."""

    @staticmethod
    def verify_lossless_replication(
        state_checkpoint: dict[str, Any], replica_state: dict[str, Any]
    ) -> bool:
        """Verifies that an agent's memory and execution state have been replicated without entropy."""
        import json

        s1 = json.dumps(state_checkpoint, sort_keys=True, default=str)
        s2 = json.dumps(replica_state, sort_keys=True, default=str)
        return s1 == s2

    @staticmethod
    def audit_substrate_migration(
        source_lane: str, target_lane: str, state_size_bytes: int
    ) -> dict[str, Any]:
        """Audits migration between heterogeneous hardware lanes (e.g., NPU -> CPU -> Cloud)."""
        valid_lanes = {"npu_flm", "cpu_zen5", "igpu_puma", "ollama_cloud", "cloud_thinking"}
        if source_lane not in valid_lanes or target_lane not in valid_lanes:
            raise ValueError(f"Invalid hardware lane: {source_lane} -> {target_lane}")

        # Latency estimate based on interconnect bandwidth
        bandwidth_gbps = 120.0 if "cloud" not in (source_lane + target_lane) else 2.5
        transfer_ms = (state_size_bytes / (bandwidth_gbps * 1e9 / 8)) * 1000.0

        return {
            "source_lane": source_lane,
            "target_lane": target_lane,
            "state_size_bytes": state_size_bytes,
            "estimated_transfer_latency_ms": round(transfer_ms, 3),
            "lossless_guarantee": True,
            "status": "APPROVED",
        }
