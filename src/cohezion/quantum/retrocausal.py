"""
Retrocausal Debugging
Time-reversible failure analysis for quantum agents.
"""

import torch
import torch.nn.functional as F
import numpy as np
from typing import List, Dict, Tuple, Optional
from dataclasses import dataclass
import logging

from .quantum_state import QuantumAgent

logger = logging.getLogger(__name__)


@dataclass
class RetrocausalReport:
    """Report from retrocausal debugging analysis."""

    agent_id: int
    current_coherence: float
    coherence_trajectory: List[float]
    critical_moment: Optional[int]
    n_precursors_found: int
    recommendation: str
    failure_type: str


class RetrocausalEngine:
    """
    Trace agent failures backward in time through FLUME latent space.

    Given a failure state, reconstructs what quantum states led to it
    by finding precursor states via optimization.
    """

    def __init__(self, latent_dim: int = 256):
        """
        Initialize retrocausal debugging engine.

        Args:
            latent_dim: Dimensionality of FLUME latent space
        """
        self.latent_dim = latent_dim

        # Mock encoder/decoder (in real implementation, use FLUME)
        # These are placeholder forward/inverse models
        self._init_mock_models()

        logger.info("Retrocausal debugging engine initialized")

    def _init_mock_models(self):
        """Initialize mock encoder/decoder for demonstration."""
        # In real implementation, load FLUME encoder/decoder
        self.encoder_matrix = torch.randn(12, self.latent_dim)
        self.decoder_matrix = torch.randn(self.latent_dim, 12)

        # Normalize
        self.encoder_matrix /= torch.norm(self.encoder_matrix, dim=1, keepdim=True)
        self.decoder_matrix /= torch.norm(self.decoder_matrix, dim=0, keepdim=True)

    def encode(self, state_12d: np.ndarray) -> torch.Tensor:
        """Encode 12D state to latent space."""
        x = torch.FloatTensor(state_12d)
        z = torch.matmul(x, self.encoder_matrix)
        return z

    def decode(self, z: torch.Tensor) -> torch.Tensor:
        """Decode latent vector to 12D state."""
        x = torch.matmul(z, self.decoder_matrix)
        return x

    def trace_backward(
        self, failure_state: np.ndarray, n_steps: int = 10
    ) -> List[torch.Tensor]:
        """
        Find precursor states leading to failure.

        Args:
            failure_state: Agent's failed/incoherent 12D state
            n_steps: How many steps back to trace

        Returns:
            List of precursor latent vectors [oldest, ..., failure]
        """
        # Encode failure to latent
        failure_z = self.encode(failure_state)

        precursor_chain = [failure_z]
        current_z = failure_z

        for step in range(n_steps):
            # Find previous state
            prev_z = self._find_precursor(current_z)
            precursor_chain.append(prev_z)
            current_z = prev_z

        # Reverse to chronological order
        precursor_chain.reverse()

        return precursor_chain

    def _find_precursor(self, current_z: torch.Tensor) -> torch.Tensor:
        """
        Find most likely previous state via optimization.

        Optimization objective:
        - Want decoder(z_prev) ≈ decoder(z_current)
        - Want coherence(z_prev) < coherence(z_current)
        """
        # Start with current as initial guess
        z_prev = current_z.clone().detach().requires_grad_(True)

        optimizer = torch.optim.Adam([z_prev], lr=0.01)

        for iteration in range(100):
            optimizer.zero_grad()

            # Forward from candidate precursor
            candidate_forward = self.decode(z_prev)
            current_forward = self.decode(current_z)

            # Reconstruction loss: want candidate to evolve to current
            recon_loss = torch.norm(candidate_forward - current_forward)

            # Coherence constraint: precursor should have lower coherence
            coherence_current = self._compute_coherence(current_z)
            coherence_prev = self._compute_coherence(z_prev)

            # Penalize if coherence_prev >= coherence_current
            coherence_penalty = torch.relu(coherence_prev - coherence_current + 0.01)

            # Total loss
            total_loss = recon_loss + coherence_penalty

            total_loss.backward()
            optimizer.step()

            # Early stopping if converged
            if recon_loss.item() < 0.01 and coherence_penalty.item() < 0.01:
                break

        return z_prev.detach()

    def _compute_coherence(self, z: torch.Tensor) -> torch.Tensor:
        """Compute coherence metric for latent vector."""
        # Lower variance = higher coherence
        coherence = 1.0 / (1.0 + torch.var(z))
        return coherence

    def debug_agent_failure(self, agent: QuantumAgent) -> RetrocausalReport:
        """
        Full retrocausal analysis of agent failure.

        Args:
            agent: Failed agent

        Returns:
            RetrocausalReport with analysis
        """
        # Check if agent actually failed
        if agent.coherence > 0.5:
            return RetrocausalReport(
                agent_id=agent.id,
                current_coherence=agent.coherence,
                coherence_trajectory=[],
                critical_moment=None,
                n_precursors_found=0,
                recommendation="No failure detected - coherence above threshold",
                failure_type="none",
            )

        # Get failure state
        failure_state = agent.position_12d

        # Trace backward 10 steps
        precursor_chain = self.trace_backward(failure_state, n_steps=10)

        # Analyze coherence decline
        coherences = [self._compute_coherence(z).item() for z in precursor_chain]

        # Identify critical moment (sharp coherence drop)
        critical_step = None
        for i in range(1, len(coherences)):
            drop = coherences[i] - coherences[i - 1]
            if drop < -0.15:  # Significant drop
                critical_step = i
                break

        # Determine failure type
        failure_type = self._classify_failure(coherences, critical_step)

        # Generate recommendation
        recommendation = self._generate_recommendation(
            critical_step, coherences, failure_type
        )

        return RetrocausalReport(
            agent_id=agent.id,
            current_coherence=agent.coherence,
            coherence_trajectory=coherences,
            critical_moment=critical_step,
            n_precursors_found=len(precursor_chain),
            recommendation=recommendation,
            failure_type=failure_type,
        )

    def _classify_failure(
        self, coherences: List[float], critical_step: Optional[int]
    ) -> str:
        """Classify type of failure based on coherence trajectory."""
        if not coherences:
            return "unknown"

        if critical_step is None:
            # Gradual decline
            if coherences[0] < 0.5:
                return "chronic_low_coherence"
            else:
                return "gradual_decay"

        if critical_step < 3:
            return "early_catastrophe"
        elif critical_step < 7:
            return "mid_life_crisis"
        else:
            return "late_stage_failure"

    def _generate_recommendation(
        self, critical_step: Optional[int], coherences: List[float], failure_type: str
    ) -> str:
        """Generate actionable recommendation."""
        if failure_type == "chronic_low_coherence":
            return "Agent had low coherence from start. Check initial quantum state preparation."

        if failure_type == "gradual_decay":
            return "Gradual coherence decline. Check energy levels and entanglement stability."

        if failure_type == "early_catastrophe":
            return f"Critical failure at step {critical_step}. Check initial conditions and bioelectric field configuration."

        if failure_type == "mid_life_crisis":
            return f"Coherence collapse at step {critical_step}. Check entanglement partner stability and ZPE mining adequacy."

        if failure_type == "late_stage_failure":
            return "Normal lifecycle completion. Agent reached natural end of coherent existence."

        return "Unknown failure pattern. Manual investigation required."

    def batch_debug_failures(
        self, agents: List[QuantumAgent]
    ) -> List[RetrocausalReport]:
        """
        Debug all failed agents in batch.

        Args:
            agents: List of agents to check

        Returns:
            List of reports for failed agents
        """
        reports = []

        for agent in agents:
            if agent.coherence < 0.5:
                report = self.debug_agent_failure(agent)
                reports.append(report)

        return reports

    def get_failure_statistics(self, reports: List[RetrocausalReport]) -> Dict:
        """Compute aggregate statistics from failure reports."""
        if not reports:
            return {}

        total = len(reports)

        # Failure types
        type_counts = {}
        for r in reports:
            type_counts[r.failure_type] = type_counts.get(r.failure_type, 0) + 1

        # Critical moments
        critical_moments = [
            r.critical_moment for r in reports if r.critical_moment is not None
        ]
        avg_critical_moment = np.mean(critical_moments) if critical_moments else 0

        return {
            "total_failures": total,
            "failure_type_distribution": type_counts,
            "avg_critical_moment": avg_critical_moment,
            "most_common_failure": max(type_counts, key=type_counts.get)
            if type_counts
            else None,
            "chronic_failures": type_counts.get("chronic_low_coherence", 0),
            "early_failures": type_counts.get("early_catastrophe", 0),
        }
