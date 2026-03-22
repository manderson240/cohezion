"""LLM Training Bridge: Universe Simulation → Language Model Training Signals.

Converts 12D universe trajectories into training data for language models:
- Reward signals for RLHF (coherence → scalar reward)
- Preference pairs for DPO (compare trajectories by HIHO proximity)
- Judgment evaluation (assess whether agent decisions match HIHO optimality)
- Experience datasets for offline RL (trajectory → token-level rewards)

This bridges the gap between Cohezion's universe simulations and actual
LLM training pipelines, making the 12D manifold directly useful for
model improvement.

Architecture:
    TrajectoryToReward
        └── Maps 12D coherence + SPIN alignment → scalar reward

    PreferencePairGenerator
        └── Compares trajectory pairs → DPO training data

    JudgmentEvaluator
        └── Assesses whether agent chose the HIHO-optimal action

    ExperienceDataset
        └── Packages trajectories → training-ready format

References:
    - Smith's HIHO: reward = proximity to 0.5 coherence
    - Smith's SPIN: bonus for rotation/precession alignment
    - Shoulders' EVOs: multi-agent consensus as quality signal
    - Matsumoto's precipitation: threshold for "genuine capability"
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)

HIHO = 0.5


@dataclass
class TrajectoryStep:
    """A single step in an agent trajectory."""

    state_12d: list[float]
    action: str
    coherence: float
    spin_coherence: float
    tempic_field: float
    reward: float
    timestamp: float = 0.0


@dataclass
class AgentTrajectory:
    """Complete agent trajectory through the 12D manifold."""

    agent_id: str
    task_description: str
    steps: list[TrajectoryStep]
    final_coherence: float
    total_reward: float
    precipitation_achieved: bool = False
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class PreferencePair:
    """A preference pair for DPO/RLHF training.

    The 'chosen' trajectory is the one with higher HIHO-alignment score.
    The 'rejected' trajectory is the alternative.
    """

    prompt: str
    chosen_response: str
    rejected_response: str
    chosen_reward: float
    rejected_reward: float
    margin: float  # How much better chosen is than rejected


@dataclass
class JudgmentAssessment:
    """Assessment of an agent's judgment quality at a decision point."""

    context: str
    decision_made: str
    optimal_decision: str
    alignment_score: float  # 0-1, how close to optimal
    spin_alignment: float  # Did SPIN physics predict the right action?
    reasoning: str


@dataclass
class TokenReward:
    """Per-token reward for RLHF training."""

    token: str
    reward: float
    position: int
    coherence_at_position: float


class TrajectoryToReward:
    """Converts 12D universe trajectories into scalar reward signals.

    Reward components:
    1. HIHO proximity (primary): How close brane dims are to 0.5
    2. SPIN alignment bonus: Rotation/precession in phase
    3. Tempic stability: Low rate-of-change = stable agent
    4. Precipitation bonus: Did the agent produce useful output?
    5. Journey consistency: Low coherence variance across trajectory
    """

    def __init__(
        self,
        hiho_weight: float = 0.4,
        spin_weight: float = 0.2,
        tempic_weight: float = 0.1,
        precipitation_weight: float = 0.2,
        consistency_weight: float = 0.1,
    ):
        self.hiho_weight = hiho_weight
        self.spin_weight = spin_weight
        self.tempic_weight = tempic_weight
        self.precipitation_weight = precipitation_weight
        self.consistency_weight = consistency_weight

    def compute_step_reward(self, step: TrajectoryStep) -> float:
        """Compute reward for a single trajectory step."""
        # 1. HIHO proximity
        brane_dims = step.state_12d[4:11] if len(step.state_12d) >= 11 else step.state_12d
        hiho_score = 1.0 - float(np.mean([(d - HIHO) ** 2 for d in brane_dims])) * 4.0
        hiho_score = max(0.0, hiho_score)

        # 2. SPIN coherence
        spin_score = step.spin_coherence

        # 3. Tempic stability (low change = stable)
        tempic_score = max(0.0, 1.0 - step.tempic_field * 2.0)

        return self.hiho_weight * hiho_score + self.spin_weight * spin_score + self.tempic_weight * tempic_score

    def compute_trajectory_reward(self, trajectory: AgentTrajectory) -> float:
        """Compute aggregate reward for a complete trajectory."""
        if not trajectory.steps:
            return 0.0

        # Per-step rewards
        step_rewards = [self.compute_step_reward(s) for s in trajectory.steps]
        avg_step_reward = float(np.mean(step_rewards))

        # Consistency bonus: low coherence variance = stable journey
        coherences = [s.coherence for s in trajectory.steps]
        consistency = (
            max(0.0, 1.0 - float(np.std(coherences)) * 4.0) if len(coherences) > 1 else 0.5
        )

        # Precipitation bonus
        precipitation = 1.0 if trajectory.precipitation_achieved else 0.0

        total = avg_step_reward + self.consistency_weight * consistency + self.precipitation_weight * precipitation

        return min(1.0, max(0.0, total))


class PreferencePairGenerator:
    """Generates DPO preference pairs from trajectory comparisons.

    Given two trajectories for the same task, the one with higher HIHO
    alignment becomes 'chosen' and the other becomes 'rejected'.
    This produces training data for Direct Preference Optimization.
    """

    def __init__(
        self,
        reward_computer: TrajectoryToReward | None = None,
        min_margin: float = 0.05,
    ):
        self.reward_computer = reward_computer or TrajectoryToReward()
        self.min_margin = min_margin

    def generate_pair(
        self,
        trajectory_a: AgentTrajectory,
        trajectory_b: AgentTrajectory,
    ) -> PreferencePair | None:
        """Generate a preference pair from two trajectories.

        Returns None if the trajectories are too similar (margin < min_margin).
        """
        reward_a = self.reward_computer.compute_trajectory_reward(trajectory_a)
        reward_b = self.reward_computer.compute_trajectory_reward(trajectory_b)

        margin = abs(reward_a - reward_b)
        if margin < self.min_margin:
            return None

        if reward_a >= reward_b:
            chosen, rejected = trajectory_a, trajectory_b
            chosen_reward, rejected_reward = reward_a, reward_b
        else:
            chosen, rejected = trajectory_b, trajectory_a
            chosen_reward, rejected_reward = reward_b, reward_a

        return PreferencePair(
            prompt=chosen.task_description,
            chosen_response=self._trajectory_to_text(chosen),
            rejected_response=self._trajectory_to_text(rejected),
            chosen_reward=chosen_reward,
            rejected_reward=rejected_reward,
            margin=margin,
        )

    def generate_pairs_from_population(
        self,
        trajectories: list[AgentTrajectory],
        max_pairs: int = 1000,
    ) -> list[PreferencePair]:
        """Generate preference pairs from a population of trajectories.

        Pairs trajectories that attempted the same or similar tasks,
        then ranks by HIHO alignment to create chosen/rejected pairs.
        """
        pairs: list[PreferencePair] = []

        # Score all trajectories
        scored = [(t, self.reward_computer.compute_trajectory_reward(t)) for t in trajectories]
        scored.sort(key=lambda x: x[1], reverse=True)

        # Pair top-half (chosen) with bottom-half (rejected)
        n = len(scored)
        for i in range(min(n // 2, max_pairs)):
            top_idx = i
            bottom_idx = n - 1 - i
            if top_idx >= bottom_idx:
                break

            pair = self.generate_pair(scored[top_idx][0], scored[bottom_idx][0])
            if pair is not None:
                pairs.append(pair)

        return pairs

    def _trajectory_to_text(self, trajectory: AgentTrajectory) -> str:
        """Convert trajectory to text representation for DPO training."""
        lines = [f"Task: {trajectory.task_description}"]
        for i, step in enumerate(trajectory.steps[:20]):  # Cap at 20 steps
            lines.append(
                f"Step {i}: action={step.action}, coherence={step.coherence:.3f}, spin={step.spin_coherence:.2f}"
            )
        lines.append(f"Final coherence: {trajectory.final_coherence:.3f}")
        lines.append(f"Precipitated: {trajectory.precipitation_achieved}")
        return "\n".join(lines)


class JudgmentEvaluator:
    """Evaluates agent judgment quality at decision points.

    For each decision in a trajectory, computes how close the agent's
    choice was to the HIHO-optimal action. This produces labeled data
    for training judgment capabilities in LLMs.
    """

    def evaluate_decision(
        self,
        state_before: list[float],
        action_taken: str,
        state_after: list[float],
        available_actions: list[str] | None = None,
    ) -> JudgmentAssessment:
        """Evaluate a single decision for HIHO optimality."""
        brane_before = state_before[4:11] if len(state_before) >= 11 else state_before
        brane_after = state_after[4:11] if len(state_after) >= 11 else state_after

        # Did the action move toward or away from HIHO?
        dist_before = float(np.mean([(d - HIHO) ** 2 for d in brane_before]))
        dist_after = float(np.mean([(d - HIHO) ** 2 for d in brane_after]))

        improved = dist_after < dist_before
        alignment = max(0.0, 1.0 - dist_after * 4.0)

        # SPIN prediction: did the action maintain spin alignment?
        if len(state_after) >= 8:
            rot = state_after[6]
            prec = state_after[7]
            spin_aligned = (rot >= 0.5) == (prec >= 0.5)
            spin_score = 1.0 if spin_aligned else 0.0
        else:
            spin_score = 0.5

        optimal = "maintain_hiho" if improved else "move_toward_hiho"
        reasoning = (
            f"Action {'improved' if improved else 'degraded'} HIHO alignment "
            f"(dist: {dist_before:.4f} → {dist_after:.4f}). "
            f"SPIN {'aligned' if spin_score > 0.5 else 'misaligned'}."
        )

        return JudgmentAssessment(
            context=f"State: {[f'{d:.2f}' for d in state_before[:6]]}...",
            decision_made=action_taken,
            optimal_decision=optimal,
            alignment_score=alignment,
            spin_alignment=spin_score,
            reasoning=reasoning,
        )

    def evaluate_trajectory(self, trajectory: AgentTrajectory) -> list[JudgmentAssessment]:
        """Evaluate all decisions in a trajectory."""
        assessments = []
        for i in range(len(trajectory.steps) - 1):
            step = trajectory.steps[i]
            next_step = trajectory.steps[i + 1]
            assessment = self.evaluate_decision(
                state_before=step.state_12d,
                action_taken=step.action,
                state_after=next_step.state_12d,
            )
            assessments.append(assessment)
        return assessments


class ExperienceDataset:
    """Packages universe trajectories into LLM training-ready format.

    Output formats:
    - JSONL for preference data (DPO)
    - JSONL for reward model training (scalar rewards)
    - JSONL for judgment fine-tuning (decision assessment)
    """

    def __init__(self, output_dir: str | Path = "data/training"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self._reward_computer = TrajectoryToReward()
        self._pair_generator = PreferencePairGenerator(self._reward_computer)
        self._judgment_evaluator = JudgmentEvaluator()

    def export_preference_data(
        self,
        trajectories: list[AgentTrajectory],
        filename: str = "preferences.jsonl",
    ) -> Path:
        """Export DPO preference pairs as JSONL."""
        pairs = self._pair_generator.generate_pairs_from_population(trajectories)
        output_path = self.output_dir / filename

        with open(output_path, "w") as f:
            for pair in pairs:
                record = {
                    "prompt": pair.prompt,
                    "chosen": pair.chosen_response,
                    "rejected": pair.rejected_response,
                    "chosen_reward": pair.chosen_reward,
                    "rejected_reward": pair.rejected_reward,
                    "margin": pair.margin,
                }
                f.write(json.dumps(record) + "\n")

        logger.info("Exported %d preference pairs to %s", len(pairs), output_path)
        return output_path

    def export_reward_data(
        self,
        trajectories: list[AgentTrajectory],
        filename: str = "rewards.jsonl",
    ) -> Path:
        """Export reward model training data as JSONL."""
        output_path = self.output_dir / filename

        with open(output_path, "w") as f:
            for traj in trajectories:
                reward = self._reward_computer.compute_trajectory_reward(traj)
                record = {
                    "task": traj.task_description,
                    "agent_id": traj.agent_id,
                    "reward": reward,
                    "final_coherence": traj.final_coherence,
                    "num_steps": len(traj.steps),
                    "precipitation": traj.precipitation_achieved,
                    "step_rewards": [self._reward_computer.compute_step_reward(s) for s in traj.steps],
                }
                f.write(json.dumps(record) + "\n")

        logger.info("Exported %d reward records to %s", len(trajectories), output_path)
        return output_path

    def export_judgment_data(
        self,
        trajectories: list[AgentTrajectory],
        filename: str = "judgments.jsonl",
    ) -> Path:
        """Export judgment evaluation data for LLM fine-tuning."""
        output_path = self.output_dir / filename

        count = 0
        with open(output_path, "w") as f:
            for traj in trajectories:
                assessments = self._judgment_evaluator.evaluate_trajectory(traj)
                for assessment in assessments:
                    record = {
                        "context": assessment.context,
                        "decision_made": assessment.decision_made,
                        "optimal_decision": assessment.optimal_decision,
                        "alignment_score": assessment.alignment_score,
                        "spin_alignment": assessment.spin_alignment,
                        "reasoning": assessment.reasoning,
                        "agent_id": traj.agent_id,
                        "task": traj.task_description,
                    }
                    f.write(json.dumps(record) + "\n")
                    count += 1

        logger.info("Exported %d judgment records to %s", count, output_path)
        return output_path

    def export_all(self, trajectories: list[AgentTrajectory], prefix: str = "") -> dict[str, Path]:
        """Export all training data formats."""
        p = f"{prefix}_" if prefix else ""
        return {
            "preferences": self.export_preference_data(trajectories, f"{p}preferences.jsonl"),
            "rewards": self.export_reward_data(trajectories, f"{p}rewards.jsonl"),
            "judgments": self.export_judgment_data(trajectories, f"{p}judgments.jsonl"),
        }
