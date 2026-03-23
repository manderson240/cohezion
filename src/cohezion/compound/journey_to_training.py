"""Journey to Training Bridge - Convert journey trajectories to LLM training formats.

Bridges JourneyTracker trajectories to LLMTrainingBridge formats:
- Journey.points → AgentTrajectory.steps
- Journey.phi_score → AgentTrajectory.total_reward
- Journey.12D dims → AgentTrajectory.state_12d

Exports:
- DPO preference pairs (chosen vs rejected trajectories)
- RLHF reward data (scalar rewards per trajectory)
- Judgment fine-tuning (decision assessments)

Architecture:
    JourneyToTrainingBridge
        ├── journey_to_agent_trajectory() → AgentTrajectory
        ├── export_journeys_as_training() → dict[str, Path]
        └── validate_training_data() → ValidationResult

Integration:
    - Reads data/universe/*.json journey files
    - Converts to llm_training_bridge.py AgentTrajectory format
    - Calls ExperienceDataset.export_all()
    - Outputs to data/training/
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


@dataclass
class ValidationResult:
    """Validation result for exported training data."""

    is_valid: bool
    n_preferences: int
    n_rewards: int
    n_judgments: int
    reward_distribution: dict[str, float]
    preference_margin_stats: dict[str, float]
    issues: list[str]


class JourneyToTrainingBridge:
    """Convert JourneyTracker trajectories to LLM training formats.

    Bridges the gap between journey capture (JourneyTracker) and
    training export (LLMTrainingBridge) by converting formats:

    Journey format:
    - id, agent_name, intent, status
    - trajectory: [{dimensions, coherence, phi_score, ...}]
    - final_coherence, final_phi_score

    AgentTrajectory format (LLMTrainingBridge):
    - agent_id, task_description, steps
    - steps: [{state_12d, action, coherence, spin_coherence, ...}]
    - final_coherence, total_reward, precipitation_achieved

    Example:
        ```python
        bridge = JourneyToTrainingBridge()

        # Load journeys
        journeys = bridge.load_journeys("data/universe")

        # Export as training data
        outputs = bridge.export_journeys_as_training(
            journeys,
            output_dir="data/training",
            prefix="anthropic",
        )

        # Validate
        validation = bridge.validate_training_data("data/training")
        print(f"Valid: {validation.is_valid}")
        print(f"Preferences: {validation.n_preferences}")
        ```
    """

    def __init__(self, output_dir: str | Path = "data/training"):
        """Initialize Journey to Training Bridge.

        Args:
            output_dir: Output directory for training data
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

        # Initialize LLM training bridge components
        try:
            from cohezion.universe.llm_training_bridge import (
                AgentTrajectory,
                ExperienceDataset,
                TrajectoryStep,
            )

            self.AgentTrajectory = AgentTrajectory
            self.ExperienceDataset = ExperienceDataset()
            self.TrajectoryStep = TrajectoryStep

            logger.debug("Initialized LLM training bridge components")
        except ImportError as e:
            logger.warning("Failed to import LLM training bridge: %s", e)
            self.AgentTrajectory = None
            self.ExperienceDataset = None
            self.TrajectoryStep = None

    def load_journeys(self, journey_dir: str | Path) -> list[dict[str, Any]]:
        """Load journeys from JSON files.

        Args:
            journey_dir: Directory containing journey_*.json files

        Returns:
            List of journey dictionaries
        """
        journey_path = Path(journey_dir)
        if not journey_path.exists():
            logger.warning("Journey directory does not exist: %s", journey_path)
            return []

        journeys = []
        for json_file in journey_path.glob("journey_*.json"):
            try:
                with open(json_file) as f:
                    journey = json.load(f)
                    journeys.append(journey)
            except Exception as e:
                logger.error("Failed to load journey %s: %s", json_file.name, e)

        logger.info("Loaded %d journeys from %s", len(journeys), journey_path)
        return journeys

    def journey_to_agent_trajectory(
        self,
        journey: dict[str, Any],
    ) -> Any | None:
        """Convert Journey format to AgentTrajectory format.

        Maps:
        - Journey.id → AgentTrajectory.agent_id
        - Journey.intent → AgentTrajectory.task_description
        - Journey.trajectory → AgentTrajectory.steps
        - Journey.final_phi_score → AgentTrajectory.total_reward
        - Journey.trajectory[i].dimensions → AgentTrajectory.steps[i].state_12d

        Args:
            journey: Journey dictionary

        Returns:
            AgentTrajectory or None if conversion fails
        """
        if not self.AgentTrajectory:
            logger.error("AgentTrajectory class not available")
            return None

        try:
            # Extract trajectory points
            trajectory = journey.get("trajectory", [])
            if not trajectory:
                logger.warning("Journey %s has no trajectory", journey.get("id", "unknown"))
                return None

            # Convert trajectory points to steps
            steps = []
            for point in trajectory:
                step = self.TrajectoryStep(
                    state_12d=point.get("dimensions", [0.5] * 12),
                    action=point.get("operation_type", "unknown"),
                    coherence=point.get("coherence", 0.5),
                    spin_coherence=point.get("spin_coherence", 0.5),
                    tempic_field=point.get("tempic_field", 0.0),
                    reward=point.get("phi_score", 0.5),
                    timestamp=point.get("timestamp", 0.0),
                )
                steps.append(step)

            # Build AgentTrajectory
            agent_traj = self.AgentTrajectory(
                agent_id=journey.get("agent_name", journey.get("id", "unknown")),
                task_description=journey.get("intent", "unknown task"),
                steps=steps,
                final_coherence=journey.get("final_coherence", 0.5),
                total_reward=journey.get("final_phi_score", 0.5),
                precipitation_achieved=journey.get("status") == "completed",
                metadata={
                    "journey_id": journey.get("id"),
                    "original_status": journey.get("status"),
                },
            )

            logger.debug(
                "Converted journey %s → AgentTrajectory with %d steps",
                journey.get("id", "unknown"),
                len(steps),
            )

            return agent_traj

        except Exception as e:
            logger.error("Failed to convert journey: %s", e)
            return None

    def export_journeys_as_training(
        self,
        journeys: list[dict[str, Any]],
        output_dir: str | Path | None = None,
        prefix: str = "anthropic",
    ) -> dict[str, Path]:
        """Export all journeys as training data.

        Output:
        - preferences.jsonl (DPO pairs)
        - rewards.jsonl (RLHF rewards)
        - judgments.jsonl (decision assessments)

        Args:
            journeys: List of journey dictionaries
            output_dir: Output directory (default: self.output_dir)
            prefix: Filename prefix

        Returns:
            Dict with paths to exported files
        """
        if not self.ExperienceDataset:
            logger.error("ExperienceDataset not available")
            return {}

        out_dir = Path(output_dir) if output_dir else self.output_dir
        out_dir.mkdir(parents=True, exist_ok=True)

        # Convert all journeys to AgentTrajectory format
        agent_trajectories = []
        for journey in journeys:
            traj = self.journey_to_agent_trajectory(journey)
            if traj is not None:
                agent_trajectories.append(traj)

        if not agent_trajectories:
            logger.warning("No trajectories to export")
            return {}

        logger.info("Exporting %d trajectories as training data", len(agent_trajectories))

        # Export using ExperienceDataset
        outputs = self.ExperienceDataset.export_all(
            agent_trajectories,
            prefix=prefix,
        )

        logger.info(
            "Exported training data: %d preferences, %d rewards, %d judgments",
            outputs["preferences"].exists(),
            outputs["rewards"].exists(),
            outputs["judgments"].exists(),
        )

        return outputs

    def validate_training_data(self, output_dir: str | Path) -> ValidationResult:
        """Validate exported training data quality.

        Checks:
        - Reward distribution (mean, std, min, max)
        - Preference margins (should be > 0.05)
        - Judgment balance (chosen vs rejected)

        Args:
            output_dir: Directory with exported training data

        Returns:
            ValidationResult with stats and issues
        """
        data_path = Path(output_dir)
        issues = []

        # Count files
        pref_file = data_path / "anthropic_preferences.jsonl"
        reward_file = data_path / "anthropic_rewards.jsonl"
        judgment_file = data_path / "anthropic_judgments.jsonl"

        n_preferences = sum(1 for _ in pref_file.glob("*")) if pref_file.exists() else 0
        n_rewards = sum(1 for _ in reward_file.glob("*")) if reward_file.exists() else 0
        n_judgments = sum(1 for _ in judgment_file.glob("*")) if judgment_file.exists() else 0

        # Load and analyze rewards
        reward_dist = {"mean": 0.0, "std": 0.0, "min": 0.0, "max": 0.0}
        if reward_file.exists():
            rewards = []
            with open(reward_file) as f:
                for line in f:
                    record = json.loads(line)
                    rewards.append(record.get("reward", 0.0))

            if rewards:
                reward_dist = {
                    "mean": float(np.mean(rewards)),
                    "std": float(np.std(rewards)),
                    "min": float(np.min(rewards)),
                    "max": float(np.max(rewards)),
                }

                # Check for reward collapse
                if reward_dist["std"] < 0.01:
                    issues.append("Reward collapse: std < 0.01")
                if reward_dist["mean"] < 0.3:
                    issues.append("Low mean reward: < 0.3")

        # Analyze preference margins
        margin_stats = {"mean": 0.0, "min": 0.0, "max": 0.0, "n_valid": 0}
        if pref_file.exists():
            margins = []
            with open(pref_file) as f:
                for line in f:
                    record = json.loads(line)
                    margin = record.get("margin", 0.0)
                    margins.append(margin)
                    if margin > 0.05:
                        margin_stats["n_valid"] += 1

            if margins:
                margin_stats = {
                    "mean": float(np.mean(margins)),
                    "min": float(np.min(margins)),
                    "max": float(np.max(margins)),
                    "n_valid": margin_stats["n_valid"],
                }

                # Check for margin collapse
                if margin_stats["mean"] < 0.05:
                    issues.append("Preference margin collapse: mean < 0.05")

        # Determine validity
        is_valid = len(issues) == 0 and n_rewards > 0

        return ValidationResult(
            is_valid=is_valid,
            n_preferences=n_preferences,
            n_rewards=n_rewards,
            n_judgments=n_judgments,
            reward_distribution=reward_dist,
            preference_margin_stats=margin_stats,
            issues=issues,
        )

    def generate_training_summary(
        self,
        journeys: list[dict[str, Any]],
        validation: ValidationResult,
    ) -> dict[str, Any]:
        """Generate training data summary for Anthropic.

        Args:
            journeys: Original journey list
            validation: Validation result

        Returns:
            Summary dictionary
        """
        # Compute journey statistics
        coherences = [j.get("final_coherence", 0.5) for j in journeys]
        phi_scores = [j.get("final_phi_score", 0.5) for j in journeys]

        summary = {
            "n_journeys": len(journeys),
            "n_agent_trajectories": validation.n_rewards,
            "n_dpo_pairs": validation.n_preferences,
            "n_judgment_records": validation.n_judgments,
            "coherence_stats": {
                "mean": float(np.mean(coherences)),
                "std": float(np.std(coherences)),
                "min": float(np.min(coherences)),
                "max": float(np.max(coherences)),
            },
            "phi_score_stats": {
                "mean": float(np.mean(phi_scores)),
                "std": float(np.std(phi_scores)),
                "min": float(np.min(phi_scores)),
                "max": float(np.max(phi_scores)),
            },
            "reward_stats": validation.reward_distribution,
            "preference_margin_stats": validation.preference_margin_stats,
            "validation_issues": validation.issues,
            "is_production_ready": validation.is_valid,
        }

        return summary

    def save_summary(
        self,
        summary: dict[str, Any],
        output_path: str | Path,
    ) -> Path:
        """Save training summary to JSON file.

        Args:
            summary: Training summary dictionary
            output_path: Output file path

        Returns:
            Path to saved file
        """
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w") as f:
            json.dump(summary, f, indent=2)

        logger.info("Saved training summary to %s", output_path)
        return output_path
