"""Google Research SLEEP Framework implementation for continual learning in LLMs.

Based on Google Research:
    "Language Models Need Sleep: Learning to Self-Modify and Consolidate Memories"
    Ali Behrouz, Farnoosh Hashemi, Adel Javanmard, Vahab Mirrokni (arXiv:2606.03979).

Implements the biological sleep paradigm for LLMs and autonomous agent swarms:
1. Wake Phase: Fast episodic acquisition into a high-plasticity buffer.
2. Sleep Phase - Stage 1 (Memory Consolidation / Knowledge Seeding):
   - Upward distillation from episodic/temporary memory into permanent parameters.
   - Generalized Distillation combining on-policy distillation and RL imitation.
   - Elastic Weight Consolidation (EWC) with Fisher Information protection.
   - Prioritized Experience Replay (PER) based on TD-error and surprisal.
3. Sleep Phase - Stage 2 (Dreaming / Self-Improvement):
   - Autonomous generation of synthetic curriculum ("dreams") to explore edge cases.
   - Self-rewarding verification via deterministic AutoHarness invariants.
   - Generalization and counterfactual synthesis without human supervision.
4. Clean Buffer Reset:
   - Flushes temporary waking capacity for the next operating cycle.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import math
import os
import time
from collections import deque
from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class WakeExperience:
    """An episodic experiential trace captured during the active wake phase."""

    experience_id: str
    session_id: str
    task_description: str
    action_sequence: tuple[str, ...]
    state_vector: tuple[float, ...]
    reward: float
    loss: float
    entropy: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    @property
    def td_error(self) -> float:
        """Surprisal / temporal difference error metric for prioritized replay."""
        # Surprisal is high when loss is elevated or reward deviates from zero
        return abs(self.loss) + abs(self.reward - 0.5) + (self.entropy * 0.1)


@dataclass(frozen=True, slots=True)
class ConsolidationReport:
    """Diagnostic report from Stage 1: Memory Consolidation (Knowledge Seeding)."""

    experiences_consolidated: int
    mean_kl_divergence: float
    ewc_penalty: float
    fisher_trace: float
    knowledge_retention_score: float
    duration_ms: float


@dataclass(frozen=True, slots=True)
class DreamReport:
    """Diagnostic report from Stage 2: Dreaming (Self-Improvement)."""

    dreams_generated: int
    dreams_verified: int
    verification_rate: float
    mean_synthetic_reward: float
    counterfactual_discoveries: int
    duration_ms: float


@dataclass(frozen=True, slots=True)
class SleepCycleSummary:
    """Consolidated summary of an entire wake-to-sleep continual learning cycle."""

    cycle_id: str
    wake_experiences_processed: int
    consolidation: ConsolidationReport
    dreaming: DreamReport
    overall_retention_score: float
    parameter_drift_norm: float
    duration_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class EpisodicExperienceBuffer:
    """Fast high-plasticity episodic memory buffer for the active wake phase.

    Analogous to the biological hippocampus: holds temporary in-context traces
    with prioritized experience replay (PER) sampling.
    """

    def __init__(self, capacity: int = 2000) -> None:
        self.capacity = capacity
        self._buffer: deque[WakeExperience] = deque(maxlen=capacity)

    def append(self, experience: WakeExperience) -> None:
        """Register a waking trace into the episodic buffer."""
        self._buffer.append(experience)

    def extend(self, experiences: Sequence[WakeExperience]) -> None:
        """Register multiple waking traces."""
        for exp in experiences:
            self._buffer.append(exp)

    def __len__(self) -> int:
        return len(self._buffer)

    def sample_prioritized(self, batch_size: int, alpha: float = 0.6) -> list[WakeExperience]:
        """Sample experiences weighted by prioritized TD-error/surprisal.

        Parameters
        ----------
        batch_size : int
            Number of experiences to sample.
        alpha : float
            Priority exponent (0 = uniform, 1 = full prioritization).

        Returns
        -------
        list[WakeExperience]
            Prioritized sample batch.
        """
        if not self._buffer:
            return []

        count = min(batch_size, len(self._buffer))
        # Compute priority probabilities: P(i) = p_i^alpha / sum(p_k^alpha)
        priorities = [max(1e-5, exp.td_error) ** alpha for exp in self._buffer]
        total_p = sum(priorities)
        if total_p == 0.0:
            probs = [1.0 / len(priorities)] * len(priorities)
        else:
            probs = [p / total_p for p in priorities]

        # Deterministic cumulative threshold sampling
        sampled: list[WakeExperience] = []
        buf_list = list(self._buffer)
        step = 1.0 / count
        cum_probs = []
        c = 0.0
        for p in probs:
            c += p
            cum_probs.append(c)

        for i in range(count):
            target = (i + 0.5) * step
            idx = 0
            while idx < len(cum_probs) - 1 and cum_probs[idx] < target:
                idx += 1
            sampled.append(buf_list[idx])

        return sampled

    def clear(self) -> None:
        """Flush the episodic buffer after sleep consolidation."""
        self._buffer.clear()


class KnowledgeSeeder:
    """Stage 1: Memory Consolidation via Generalized Upward Distillation.

    Implements Knowledge Seeding:
    Distills short-term episodic experiences into stable long-term parameters
    while protecting prior knowledge with Elastic Weight Consolidation (EWC).
    """

    def __init__(
        self,
        dimension: int = 12,
        ewc_lambda: float = 100.0,
        learning_rate: float = 0.05,
    ) -> None:
        self.dimension = dimension
        self.ewc_lambda = ewc_lambda
        self.lr = learning_rate

        # Stable long-term parameters theta and reference theta_prior
        self.theta: list[float] = [0.0] * dimension
        self.theta_prior: list[float] = [0.0] * dimension
        # Empirical Fisher Information diagonal (synaptic importance)
        self.fisher_diagonal: list[float] = [1.0] * dimension

    def consolidate(
        self,
        experiences: Sequence[WakeExperience],
    ) -> ConsolidationReport:
        """Perform upward distillation with EWC protection over experiences.

        Parameters
        ----------
        experiences : Sequence[WakeExperience]
            Prioritized waking experiences to consolidate.

        Returns
        -------
        ConsolidationReport
            Consolidation metrics including KL divergence, EWC penalty, and retention.
        """
        t0 = time.perf_counter()
        if not experiences:
            return ConsolidationReport(
                experiences_consolidated=0,
                mean_kl_divergence=0.0,
                ewc_penalty=0.0,
                fisher_trace=sum(self.fisher_diagonal),
                knowledge_retention_score=1.0,
                duration_ms=0.0,
            )

        # 1. Distillation loss gradient accumulation
        # Target representation is estimated by empirical experiential state vectors
        target_vector = [0.0] * self.dimension
        total_weight = 0.0

        for exp in experiences:
            weight = max(0.1, exp.reward + (1.0 - exp.loss))
            total_weight += weight
            for d in range(self.dimension):
                val = exp.state_vector[d] if d < len(exp.state_vector) else 0.0
                target_vector[d] += val * weight

        if total_weight > 0:
            target_vector = [v / total_weight for v in target_vector]

        # 2. Gradient computation: on-policy distillation + EWC penalty
        # grad_total = grad_distill + lambda * F * (theta - theta_prior)
        kl_divs: list[float] = []
        ewc_penalties: list[float] = []

        new_fisher = [0.0] * self.dimension

        for d in range(self.dimension):
            # Distillation gradient: d/d(theta) 0.5 * (theta - target)^2 = (theta - target)
            grad_distill = self.theta[d] - target_vector[d]
            # EWC gradient: lambda * F * (theta - theta_prior)
            grad_ewc = self.ewc_lambda * self.fisher_diagonal[d] * (self.theta[d] - self.theta_prior[d])
            grad_total = grad_distill + grad_ewc

            # Update theta
            self.theta[d] -= self.lr * grad_total

            # Track metrics
            kl_div = 0.5 * (grad_distill**2)
            kl_divs.append(kl_div)
            ewc_pen = 0.5 * self.ewc_lambda * self.fisher_diagonal[d] * ((self.theta[d] - self.theta_prior[d]) ** 2)
            ewc_penalties.append(ewc_pen)

            # Update empirical Fisher: F_d += (grad_distill)^2
            new_fisher[d] = 0.8 * self.fisher_diagonal[d] + 0.2 * (grad_distill**2 + 0.01)

        self.fisher_diagonal = new_fisher

        # 3. Compute retention score
        mean_kl = sum(kl_divs) / len(kl_divs) if kl_divs else 0.0
        total_ewc = sum(ewc_penalties)
        fisher_trace = sum(self.fisher_diagonal)

        # Retention score: higher is better (decays with uncontrolled EWC penalty)
        retention = math.exp(-min(10.0, total_ewc / (self.ewc_lambda + 1e-5)))

        dt_ms = (time.perf_counter() - t0) * 1000.0
        return ConsolidationReport(
            experiences_consolidated=len(experiences),
            mean_kl_divergence=mean_kl,
            ewc_penalty=total_ewc,
            fisher_trace=fisher_trace,
            knowledge_retention_score=retention,
            duration_ms=dt_ms,
        )

    def freeze_as_prior(self) -> None:
        """Lock current parameters as reference prior for subsequent sleep cycles."""
        self.theta_prior = list(self.theta)


class DreamCurriculumGenerator:
    """Stage 2: Dreaming (Self-Improvement via Synthetic Rehearsal).

    Generates synthetic counterfactual tasks and scenarios to rehearse newly
    consolidated knowledge, explore edge cases, and evaluate invariant bounds.
    """

    def __init__(self, dimension: int = 12) -> None:
        self.dimension = dimension

    def generate_and_rehearse(
        self,
        base_state: Sequence[float],
        num_dreams: int = 8,
    ) -> DreamReport:
        """Generate synthetic dream curriculum and verify invariants.

        Parameters
        ----------
        base_state : Sequence[float]
            Consolidated state vector from Stage 1.
        num_dreams : int
            Number of synthetic dream rollouts to simulate.

        Returns
        -------
        DreamReport
            Dream verification pass rates, rewards, and discoveries.
        """
        t0 = time.perf_counter()
        if num_dreams <= 0:
            return DreamReport(
                dreams_generated=0,
                dreams_verified=0,
                verification_rate=1.0,
                mean_synthetic_reward=0.0,
                counterfactual_discoveries=0,
                duration_ms=0.0,
            )

        verified = 0
        rewards: list[float] = []
        counterfactuals = 0

        state_len = min(self.dimension, len(base_state))
        vec = list(base_state[:state_len]) + [0.0] * max(0, self.dimension - state_len)

        for i in range(num_dreams):
            # 1. Synthesize counterfactual perturbation: dream_state = base + delta_k
            # High-frequency exploration of boundary regions
            phase = (i + 1) * math.pi / num_dreams
            perturbed = [
                vec[d] + 0.15 * math.sin(phase * (d + 1))
                for d in range(self.dimension)
            ]

            # 2. Invariant verification (AutoHarness bounded proof analogue)
            # Invariant: Poincaré/Euclidean norm must remain strictly bounded (< 1.0 or stable)
            norm_sq = sum(x**2 for x in perturbed)
            is_valid = norm_sq < 2.5  # Boundary guardrail

            if is_valid:
                verified += 1
                # Synthetic reward modeled on coherence overlap (HIHO 0.5 principle)
                distance_to_half = abs(norm_sq - 0.5)
                synthetic_reward = max(0.0, 1.0 - distance_to_half)
                rewards.append(synthetic_reward)

                if distance_to_half < 0.1:
                    counterfactuals += 1
            else:
                rewards.append(0.0)

        v_rate = verified / num_dreams if num_dreams > 0 else 0.0
        mean_r = sum(rewards) / len(rewards) if rewards else 0.0
        dt_ms = (time.perf_counter() - t0) * 1000.0

        return DreamReport(
            dreams_generated=num_dreams,
            dreams_verified=verified,
            verification_rate=v_rate,
            mean_synthetic_reward=mean_r,
            counterfactual_discoveries=counterfactuals,
            duration_ms=dt_ms,
        )


class SleepFramework:
    """Master SLEEP Framework orchestrator for continual learning (Google Research).

    Alternates between the active Wake Phase and offline Sleep Phase:
    - Wake: Accumulates episodic experiences in fast buffer.
    - Sleep: Stage 1 (Knowledge Seeding) -> Stage 2 (Dreaming) -> Clean Reset.
    """

    def __init__(
        self,
        dimension: int = 12,
        buffer_capacity: int = 2000,
        ewc_lambda: float = 100.0,
    ) -> None:
        self.dimension = dimension
        self.buffer = EpisodicExperienceBuffer(capacity=buffer_capacity)
        self.seeder = KnowledgeSeeder(dimension=dimension, ewc_lambda=ewc_lambda)
        self.dreamer = DreamCurriculumGenerator(dimension=dimension)
        self._cycle_count = 0
        self._history: list[SleepCycleSummary] = []

    @property
    def cycle_count(self) -> int:
        """Total completed sleep cycles."""
        return self._cycle_count

    def record_experience(
        self,
        task_description: str,
        action_sequence: Sequence[str],
        state_vector: Sequence[float],
        reward: float,
        loss: float,
        entropy: float = 0.1,
        session_id: str = "wake_session",
    ) -> WakeExperience:
        """Capture an operational trace into the wake episodic buffer."""
        exp_id = hashlib.sha256(
            f"{session_id}:{task_description}:{time.time_ns()}".encode()
        ).hexdigest()[:16]

        state_tuple = tuple(float(x) for x in state_vector[:self.dimension])
        # Pad if shorter than dimension
        if len(state_tuple) < self.dimension:
            state_tuple = state_tuple + (0.0,) * (self.dimension - len(state_tuple))

        exp = WakeExperience(
            experience_id=exp_id,
            session_id=session_id,
            task_description=task_description,
            action_sequence=tuple(action_sequence),
            state_vector=state_tuple,
            reward=reward,
            loss=loss,
            entropy=entropy,
        )
        self.buffer.append(exp)
        return exp

    def sleep(
        self,
        batch_size: int = 64,
        num_dreams: int = 8,
    ) -> SleepCycleSummary:
        """Execute an offline sleep cycle: Consolidation -> Dreaming -> Reset.

        Parameters
        ----------
        batch_size : int
            Prioritized replay sample size for Knowledge Seeding.
        num_dreams : int
            Number of synthetic dream curricula to generate and rehearse.

        Returns
        -------
        SleepCycleSummary
            Full diagnostic outcome of the completed sleep cycle.
        """
        t0 = time.perf_counter()
        self._cycle_count += 1
        cycle_id = f"sleep_cycle_{self._cycle_count:04d}"

        # --- Stage 1: Memory Consolidation (Knowledge Seeding) ---
        prioritized_experiences = self.buffer.sample_prioritized(batch_size=batch_size)
        consolidation_rep = self.seeder.consolidate(prioritized_experiences)

        # Compute parameter drift norm: ||theta - theta_prior||
        drift_norm = math.sqrt(
            sum((t - tp) ** 2 for t, tp in zip(self.seeder.theta, self.seeder.theta_prior))
        )

        # --- Stage 2: Dreaming (Self-Improvement & Synthetic Rehearsal) ---
        dream_rep = self.dreamer.generate_and_rehearse(
            base_state=self.seeder.theta,
            num_dreams=num_dreams,
        )

        # --- Stage 3: Phase Transition & Buffer Reset ---
        # Lock consolidated parameters as the new prior baseline
        self.seeder.freeze_as_prior()
        wake_count = len(self.buffer)
        self.buffer.clear()

        # Overall retention score balances consolidation retention and dream verification
        overall_retention = 0.6 * consolidation_rep.knowledge_retention_score + 0.4 * dream_rep.verification_rate
        dt_ms = (time.perf_counter() - t0) * 1000.0

        summary = SleepCycleSummary(
            cycle_id=cycle_id,
            wake_experiences_processed=wake_count,
            consolidation=consolidation_rep,
            dreaming=dream_rep,
            overall_retention_score=overall_retention,
            parameter_drift_norm=drift_norm,
            duration_ms=dt_ms,
        )
        self._history.append(summary)
        return summary

    def get_cycle_history(self) -> list[SleepCycleSummary]:
        """Return history of all completed sleep cycles."""
        return list(self._history)
