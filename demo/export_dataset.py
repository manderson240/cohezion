#!/usr/bin/env python3
"""Cohezion Export: Convert trajectories to LLM training data.

Transforms the 12D manifold trajectories from quickstart.py into three
training dataset formats for language model improvement:

  1. preferences.jsonl  - DPO preference pairs (chosen vs rejected by HIHO)
  2. rewards.jsonl      - Scalar reward labels for RLHF reward modeling
  3. judgments.jsonl     - Per-decision judgment assessments for fine-tuning

Uses Cohezion's llm_training_bridge module which maps physics-based
coherence signals to standard LLM training formats.

Why this matters:
  The 12D manifold provides a principled reward signal grounded in
  differential geometry and quantum coherence. Unlike human-labeled
  preferences (expensive, noisy, biased), these rewards are computed
  from first principles: HIHO proximity, SPIN alignment, Tempic stability,
  and gauge field curvature. This makes the training signal reproducible,
  cheap to generate, and physically interpretable.

  The preference pairs compare trajectories that achieve high vs low
  coherence on the same task, creating DPO training data without human
  annotators. The judgment data labels each decision point as
  HIHO-optimal or suboptimal, enabling fine-tuning of decision quality.

Usage:
  uv run python export_dataset.py                        # Default
  uv run python export_dataset.py --input other.json     # Custom input
  uv run python export_dataset.py --output-dir exports/  # Custom output
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np


def load_trajectories(path: Path) -> dict:
    """Load trajectory data from quickstart output."""
    if not path.exists():
        print(f"[ERROR] Trajectory file not found: {path}")
        print("Run quickstart.py first: uv run python quickstart.py")
        sys.exit(1)

    with open(path) as f:
        data = json.load(f)

    print(f"[OK] Loaded {len(data['episodes'])} episodes")
    return data


def build_agent_trajectories(episodes: list[dict]) -> list:
    """Convert raw episode data to AgentTrajectory objects.

    Tries to use the cohezion.universe.llm_training_bridge module directly.
    Falls back to a standalone implementation if imports fail.
    """
    try:
        from cohezion.universe.llm_training_bridge import (
            AgentTrajectory,
            TrajectoryStep,
        )

        trajectories = []
        for ep in episodes:
            steps = []
            for i, s in enumerate(ep["trajectory"]):
                # Compute tempic field (rate of change) between consecutive steps
                tempic = 0.0
                if i > 0:
                    prev = np.array(ep["trajectory"][i - 1]["state_12d"])
                    curr = np.array(s["state_12d"])
                    tempic = float(np.linalg.norm(curr[4:11] - prev[4:11]))

                steps.append(
                    TrajectoryStep(
                        state_12d=s["state_12d"],
                        action=f"velocity_perturbation_step_{s['step']}",
                        coherence=s["coherence"],
                        spin_coherence=min(
                            1.0, abs(s["spin_rotation"]) + abs(s["spin_precession"])
                        ),
                        tempic_field=tempic,
                        reward=s["reward"],
                        timestamp=float(s["step"]),
                    )
                )

            final_coherence = steps[-1].coherence if steps else 0.0
            total_reward = ep["total_reward"]

            trajectories.append(
                AgentTrajectory(
                    agent_id=f"manifold_agent_ep{ep['episode']}",
                    task_description=f"Navigate 12D manifold to HIHO equilibrium (episode {ep['episode']})",
                    steps=steps,
                    final_coherence=final_coherence,
                    total_reward=total_reward,
                    precipitation_achieved=ep["terminated"],
                    metadata={
                        "episode": ep["episode"],
                        "n_steps": ep["steps"],
                        "final_hiho_deviation": ep["final_hiho_deviation"],
                    },
                )
            )

        print(f"[OK] Built {len(trajectories)} AgentTrajectory objects via cohezion bridge")
        return trajectories

    except ImportError as e:
        print(f"[WARN] Cannot import cohezion bridge ({e}), using standalone implementation")
        return _build_standalone(episodes)


def _build_standalone(episodes: list[dict]) -> list:
    """Standalone trajectory builder when cohezion is not importable."""

    class TrajectoryStep:
        def __init__(
            self, state_12d, action, coherence, spin_coherence, tempic_field, reward, timestamp=0.0
        ):
            self.state_12d = state_12d
            self.action = action
            self.coherence = coherence
            self.spin_coherence = spin_coherence
            self.tempic_field = tempic_field
            self.reward = reward
            self.timestamp = timestamp

    class AgentTrajectory:
        def __init__(
            self,
            agent_id,
            task_description,
            steps,
            final_coherence,
            total_reward,
            precipitation_achieved=False,
            metadata=None,
        ):
            self.agent_id = agent_id
            self.task_description = task_description
            self.steps = steps
            self.final_coherence = final_coherence
            self.total_reward = total_reward
            self.precipitation_achieved = precipitation_achieved
            self.metadata = metadata or {}

    trajectories = []
    for ep in episodes:
        steps = []
        for i, s in enumerate(ep["trajectory"]):
            tempic = 0.0
            if i > 0:
                prev = np.array(ep["trajectory"][i - 1]["state_12d"])
                curr = np.array(s["state_12d"])
                tempic = float(np.linalg.norm(curr[4:11] - prev[4:11]))

            steps.append(
                TrajectoryStep(
                    state_12d=s["state_12d"],
                    action=f"velocity_perturbation_step_{s['step']}",
                    coherence=s["coherence"],
                    spin_coherence=min(1.0, abs(s["spin_rotation"]) + abs(s["spin_precession"])),
                    tempic_field=tempic,
                    reward=s["reward"],
                    timestamp=float(s["step"]),
                )
            )

        trajectories.append(
            AgentTrajectory(
                agent_id=f"manifold_agent_ep{ep['episode']}",
                task_description=f"Navigate 12D manifold to HIHO equilibrium (episode {ep['episode']})",
                steps=steps,
                final_coherence=steps[-1].coherence if steps else 0.0,
                total_reward=ep["total_reward"],
                precipitation_achieved=ep["terminated"],
                metadata={"episode": ep["episode"]},
            )
        )

    print(f"[OK] Built {len(trajectories)} trajectories (standalone)")
    return trajectories


def export_with_bridge(trajectories, output_dir: Path) -> dict[str, Path]:
    """Export using cohezion's ExperienceDataset if available."""
    try:
        from cohezion.universe.llm_training_bridge import ExperienceDataset

        dataset = ExperienceDataset(output_dir=output_dir)
        paths = dataset.export_all(trajectories)
        print(f"[OK] Exported via cohezion ExperienceDataset")
        return paths

    except ImportError:
        print("[INFO] Using standalone export")
        return export_standalone(trajectories, output_dir)


def export_standalone(trajectories, output_dir: Path) -> dict[str, Path]:
    """Standalone export when cohezion is not importable."""
    output_dir.mkdir(parents=True, exist_ok=True)
    HIHO = 0.5

    # --- Reward data ---
    rewards_path = output_dir / "rewards.jsonl"
    with open(rewards_path, "w") as f:
        for traj in trajectories:
            step_rewards = []
            for s in traj.steps:
                brane = s.state_12d[4:11] if len(s.state_12d) >= 11 else s.state_12d
                hiho_score = max(0.0, 1.0 - float(np.mean([(d - HIHO) ** 2 for d in brane])) * 4.0)
                step_rewards.append(0.4 * hiho_score + 0.2 * s.spin_coherence)

            record = {
                "task": traj.task_description,
                "agent_id": traj.agent_id,
                "reward": float(np.mean(step_rewards)) if step_rewards else 0.0,
                "final_coherence": traj.final_coherence,
                "num_steps": len(traj.steps),
                "precipitation": traj.precipitation_achieved,
                "step_rewards": step_rewards,
            }
            f.write(json.dumps(record) + "\n")

    # --- Preference pairs ---
    preferences_path = output_dir / "preferences.jsonl"
    scored = []
    for traj in trajectories:
        if traj.steps:
            brane_scores = []
            for s in traj.steps:
                brane = s.state_12d[4:11] if len(s.state_12d) >= 11 else s.state_12d
                brane_scores.append(
                    max(0.0, 1.0 - float(np.mean([(d - HIHO) ** 2 for d in brane])) * 4.0)
                )
            score = float(np.mean(brane_scores))
        else:
            score = 0.0
        scored.append((traj, score))

    scored.sort(key=lambda x: x[1], reverse=True)
    n = len(scored)
    pairs_written = 0

    with open(preferences_path, "w") as f:
        for i in range(min(n // 2, 500)):
            top_idx = i
            bottom_idx = n - 1 - i
            if top_idx >= bottom_idx:
                break

            chosen_traj, chosen_score = scored[top_idx]
            rejected_traj, rejected_score = scored[bottom_idx]
            margin = chosen_score - rejected_score

            if margin < 0.05:
                continue

            def traj_to_text(t):
                lines = [f"Task: {t.task_description}"]
                for j, s in enumerate(t.steps[:20]):
                    lines.append(
                        f"Step {j}: coherence={s.coherence:.3f}, spin={s.spin_coherence:.2f}"
                    )
                lines.append(f"Final coherence: {t.final_coherence:.3f}")
                lines.append(f"Precipitated: {t.precipitation_achieved}")
                return "\n".join(lines)

            record = {
                "prompt": chosen_traj.task_description,
                "chosen": traj_to_text(chosen_traj),
                "rejected": traj_to_text(rejected_traj),
                "chosen_reward": chosen_score,
                "rejected_reward": rejected_score,
                "margin": margin,
            }
            f.write(json.dumps(record) + "\n")
            pairs_written += 1

    # --- Judgment data ---
    judgments_path = output_dir / "judgments.jsonl"
    judgments_written = 0

    with open(judgments_path, "w") as f:
        for traj in trajectories:
            for i in range(len(traj.steps) - 1):
                s = traj.steps[i]
                s_next = traj.steps[i + 1]

                brane_before = s.state_12d[4:11] if len(s.state_12d) >= 11 else s.state_12d
                brane_after = (
                    s_next.state_12d[4:11] if len(s_next.state_12d) >= 11 else s_next.state_12d
                )

                dist_before = float(np.mean([(d - HIHO) ** 2 for d in brane_before]))
                dist_after = float(np.mean([(d - HIHO) ** 2 for d in brane_after]))

                improved = dist_after < dist_before
                alignment = max(0.0, 1.0 - dist_after * 4.0)

                rot = s_next.state_12d[6] if len(s_next.state_12d) > 7 else 0.5
                prec = s_next.state_12d[7] if len(s_next.state_12d) > 7 else 0.5
                spin_aligned = (rot >= 0.5) == (prec >= 0.5)

                record = {
                    "context": f"State: {[f'{d:.2f}' for d in s.state_12d[:6]]}...",
                    "decision_made": s.action,
                    "optimal_decision": "maintain_hiho" if improved else "move_toward_hiho",
                    "alignment_score": alignment,
                    "spin_alignment": 1.0 if spin_aligned else 0.0,
                    "reasoning": (
                        f"Action {'improved' if improved else 'degraded'} HIHO alignment "
                        f"(dist: {dist_before:.4f} -> {dist_after:.4f}). "
                        f"SPIN {'aligned' if spin_aligned else 'misaligned'}."
                    ),
                    "agent_id": traj.agent_id,
                    "task": traj.task_description,
                }
                f.write(json.dumps(record) + "\n")
                judgments_written += 1

    return {
        "preferences": preferences_path,
        "rewards": rewards_path,
        "judgments": judgments_path,
    }


def print_export_summary(paths: dict[str, Path]):
    """Print summary of exported data."""
    print(f"\n{'=' * 70}")
    print(f"  Export Summary")
    print(f"{'=' * 70}\n")

    for name, path in paths.items():
        if not path.exists():
            print(f"  {name:<15} {path} (not created)")
            continue

        # Count lines in JSONL
        with open(path) as f:
            n_records = sum(1 for _ in f)

        size_kb = path.stat().st_size / 1024
        print(f"  {name:<15} {n_records:>6} records  {size_kb:>8.1f} KB  {path}")

        # Show a sample record
        with open(path) as f:
            first = json.loads(f.readline())
        sample_keys = list(first.keys())
        print(f"  {'':>15} fields: {', '.join(sample_keys)}")

    print(f"\n  Format: JSONL (one JSON object per line)")
    print(f"  Compatible with: HuggingFace datasets, TRL, DeepSpeed-Chat")
    print(f"\n  Example usage with HuggingFace datasets:")
    print(f"    from datasets import load_dataset")
    print(f"    ds = load_dataset('json', data_files='preferences.jsonl')")
    print(f"{'=' * 70}")


def main():
    parser = argparse.ArgumentParser(description="Export trajectory data to LLM training formats")
    parser.add_argument(
        "--input",
        type=str,
        default=str(Path(__file__).parent / "data" / "trajectories.json"),
        help="Path to trajectories.json from quickstart.py",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default=str(Path(__file__).parent / "data"),
        help="Output directory for JSONL files",
    )
    args = parser.parse_args()

    data = load_trajectories(Path(args.input))
    episodes = data["episodes"]
    trajectories = build_agent_trajectories(episodes)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    paths = export_with_bridge(trajectories, output_dir)
    print_export_summary(paths)


if __name__ == "__main__":
    main()
