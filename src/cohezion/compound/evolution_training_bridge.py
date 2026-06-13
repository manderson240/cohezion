"""Bridge: Group Evolution -> FLUME VAE -> Local Open-Weight Model Training.

Closes the loop between agent evolution and local model improvement:

    GEA GroupEvolutionEngine
        |  (archive entries, experience pools)
        v
    JourneyTracker 12D trajectories
        |  (encode execution quality as 12D axiomatic vectors)
        v
    ExperienceEncoder 256D vectors
        |  (trajectory + metrics + operation type + semantic fingerprint)
        v
    FLUME VAE latent space
        |  (compress to learned manifold, measure latent novelty)
        v
    LLM Training Bridge
        |  (DPO preference pairs, reward signals, judgment data)
        v
    Local Open-Weight Model (QLoRA fine-tuning via llamafactory)
        |  (qwen3.5, phi4, gemma3 on Strix Halo)
        v
    Probe task evaluation -> fitness score -> next GEA generation
        |
        +-----> back to GroupEvolutionEngine (closed loop)

The key insight: evolution produces *diverse* agent experiences via
performance-novelty selection. These experiences, encoded through the
FLUME VAE, create a rich training signal that teaches local models
not just what works (exploitation) but what novel strategies exist
(exploration). The VAE's latent manifold provides continuous novelty
measurement that's smoother than GEA's discrete cosine distance.
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from cohezion.compound.group_evolution import (
    AgentCandidate,
    ArchiveEntry,
    ExperienceTrace,
    GroupEvolutionEngine,
    GroupExperiencePool,
    TaskSuccessVector,
)
from cohezion.flume.experience_encoder import ExperienceEncoder


logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

HIHO = 0.5
MIN_PHI_FOR_TRAINING = 0.6  # Lower than journey_finetune (0.7) to capture
# diverse evolutionary strategies, not just top performers
MAX_TRAINING_SAMPLES = 5000
DPO_MIN_MARGIN = 0.05  # Minimum reward gap for meaningful preference pairs


@dataclass
class EvolutionTrainingConfig:
    """Configuration for the evolution-to-training pipeline."""

    min_phi_score: float = MIN_PHI_FOR_TRAINING
    max_training_samples: int = MAX_TRAINING_SAMPLES
    dpo_min_margin: float = DPO_MIN_MARGIN
    output_dir: Path = field(default_factory=lambda: Path("data/training/evolution"))
    include_dpo: bool = True
    include_rewards: bool = True
    include_judgments: bool = True
    vae_checkpoint_dir: Path = field(default_factory=lambda: Path("data/flume/checkpoints"))
    seed: int = 42


# ---------------------------------------------------------------------------
# Trace-to-Trajectory Converter
# ---------------------------------------------------------------------------


@dataclass
class EvolutionTrajectory:
    """A trajectory derived from GEA evolution, ready for training signal
    extraction.

    Carries both the GEA-level metadata (generation, parent lineage,
    gea_score) and the 12D/256D representations needed for FLUME encoding.
    """

    agent_id: str
    generation: int
    parent_ids: list[str]
    trajectory_12d: np.ndarray  # 12D axiomatic position
    embedding_256d: np.ndarray  # 256D FLUME encoding
    phi_score: float
    coherence: float
    performance: float  # GEA solve rate
    novelty: float  # GEA KNN novelty
    gea_score: float  # performance * sqrt(novelty)
    operation_type: str = "generate"
    task_description: str = ""
    traces: list[ExperienceTrace] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


class TraceToTrajectoryConverter:
    """Convert GEA archive entries and experience traces into 12D/256D
    trajectories suitable for FLUME VAE training and LLM training signal
    generation.

    This is the first stage of the bridge: raw evolutionary data becomes
    structured trajectories in the FLUME manifold.
    """

    def __init__(self, encoder: ExperienceEncoder | None = None) -> None:
        self.encoder = encoder or ExperienceEncoder()

    def archive_entry_to_trajectory(
        self,
        entry: ArchiveEntry,
        traces: list[ExperienceTrace] | None = None,
    ) -> EvolutionTrajectory:
        """Convert a single archive entry into an EvolutionTrajectory.

        The entry's TaskSuccessVector is projected into 12D space by treating
        task-solve dimensions as a capability fingerprint. The 256D FLUME
        encoding adds metrics and semantic context.
        """
        # Project success vector into 12D (pad/truncate to 12 dims)
        sv = entry.success_vector.successes
        traj_12d = np.zeros(12, dtype=np.float64)
        n = min(len(sv), 12)
        traj_12d[:n] = sv[:n]

        # Build experience dict for 256D encoding
        experience_dict = {
            "trajectory": traj_12d.tolist(),
            "phi_score": entry.performance,
            "mission_id": f"gea_gen{entry.generation}_{entry.agent_id}",
            "agent_id": entry.agent_id,
            "skill_name": "evolution",
            "operation_type": "generate",
            "cache_hit_rate": 0.0,
            "success": float(entry.performance > 0.5),
            "tokens_used": 0.0,
            "duration_s": 0.0,
        }

        embedding_256d = self.encoder.encode(experience_dict)

        return EvolutionTrajectory(
            agent_id=entry.agent_id,
            generation=entry.generation,
            parent_ids=entry.parent_ids,
            trajectory_12d=traj_12d,
            embedding_256d=embedding_256d,
            phi_score=entry.performance,
            coherence=_hiho_coherence(entry.performance),
            performance=entry.performance,
            novelty=entry.novelty,
            gea_score=entry.gea_score,
            traces=traces or [],
            metadata={
                "ancestor_count": entry.ancestor_count,
                "skill_patches": entry.skill_patches,
            },
        )

    def pool_to_trajectories(
        self,
        pool: GroupExperiencePool,
        candidates: list[AgentCandidate],
    ) -> list[EvolutionTrajectory]:
        """Convert a GroupExperiencePool into per-agent trajectories.

        Each candidate gets their own trajectory built from the shared pool's
        traces, enriched with their performance-novelty scores.
        """
        trajectories: list[EvolutionTrajectory] = []

        for candidate in candidates:
            agent_traces = [t for t in pool.traces if t.agent_id == candidate.agent_id]

            # Aggregate trace quality scores into a phi-like metric
            quality_scores = [t.quality_score for t in agent_traces]
            avg_quality = float(np.mean(quality_scores)) if quality_scores else 0.0

            # Build 12D from success vector if available, else from quality
            if candidate.success_vector is not None:
                sv = candidate.success_vector.successes
                traj_12d = np.zeros(12, dtype=np.float64)
                n = min(len(sv), 12)
                traj_12d[:n] = sv[:n]
            else:
                traj_12d = np.full(12, candidate.coherence, dtype=np.float64)

            experience_dict = {
                "trajectory": traj_12d.tolist(),
                "phi_score": avg_quality,
                "mission_id": f"pool_{candidate.agent_id}",
                "agent_id": candidate.agent_id,
                "skill_name": "evolution",
                "operation_type": "generate",
                "success": float(candidate.performance > 0.5),
            }

            embedding_256d = self.encoder.encode(experience_dict)

            trajectories.append(
                EvolutionTrajectory(
                    agent_id=candidate.agent_id,
                    generation=0,
                    parent_ids=[],
                    trajectory_12d=traj_12d,
                    embedding_256d=embedding_256d,
                    phi_score=avg_quality,
                    coherence=candidate.coherence,
                    performance=candidate.performance,
                    novelty=candidate.novelty,
                    gea_score=candidate.gea_score,
                    traces=agent_traces,
                )
            )

        return trajectories


# ---------------------------------------------------------------------------
# Latent Novelty Scorer (VAE-based)
# ---------------------------------------------------------------------------


class LatentNoveltyScorer:
    """Compute novelty in the 256D FLUME latent space.

    This provides a smoother novelty signal than GEA's discrete cosine
    distance on binary task-success vectors. The VAE learns a compressed
    manifold where similar capability profiles cluster together, so
    distance in latent space = behavioral novelty.
    """

    def __init__(self, m_neighbors: int = 4) -> None:
        self.m_neighbors = m_neighbors

    def compute_latent_novelty(
        self,
        agent: EvolutionTrajectory,
        population: list[EvolutionTrajectory],
    ) -> float:
        """KNN novelty using cosine distance in 256D FLUME space."""
        if len(population) <= 1:
            return 1.0

        agent_vec = agent.embedding_256d
        distances: list[float] = []

        for other in population:
            if other.agent_id == agent.agent_id:
                continue
            dist = _cosine_distance(agent_vec, other.embedding_256d)
            distances.append(dist)

        if not distances:
            return 1.0

        distances.sort()
        m = min(self.m_neighbors, len(distances))
        return float(np.mean(distances[:m]))


# ---------------------------------------------------------------------------
# Training Signal Generator
# ---------------------------------------------------------------------------


@dataclass
class TrainingSignals:
    """Complete set of training signals generated from one evolution round."""

    dpo_pairs: list[dict[str, Any]]
    reward_records: list[dict[str, Any]]
    judgment_records: list[dict[str, Any]]
    instruction_tuning: list[dict[str, Any]]
    generation: int
    n_agents: int
    avg_reward: float
    latent_novelty_mean: float


class EvolutionTrainingSignalGenerator:
    """Generate multi-format LLM training signals from evolution trajectories.

    Produces four types of training data:
    1. DPO preference pairs (chosen/rejected by HIHO alignment)
    2. Reward model data (scalar rewards from trajectory quality)
    3. Judgment data (decision-level HIHO optimality assessments)
    4. Instruction-tuning data (high-quality traces as exemplars)
    """

    def __init__(self, config: EvolutionTrainingConfig | None = None) -> None:
        self.config = config or EvolutionTrainingConfig()
        self.latent_scorer = LatentNoveltyScorer()

    def generate_signals(
        self,
        trajectories: list[EvolutionTrajectory],
        generation: int = 0,
    ) -> TrainingSignals:
        """Generate all training signal types from a set of trajectories."""
        if not trajectories:
            return TrainingSignals(
                dpo_pairs=[],
                reward_records=[],
                judgment_records=[],
                instruction_tuning=[],
                generation=generation,
                n_agents=0,
                avg_reward=0.0,
                latent_novelty_mean=0.0,
            )

        # Compute rewards
        rewards = [_trajectory_reward(t) for t in trajectories]

        # Compute latent novelty
        novelties = [
            self.latent_scorer.compute_latent_novelty(t, trajectories) for t in trajectories
        ]

        # DPO preference pairs
        dpo_pairs = self._generate_dpo_pairs(trajectories, rewards)

        # Reward records
        reward_records = self._generate_reward_records(trajectories, rewards)

        # Judgment records
        judgment_records = self._generate_judgment_records(trajectories)

        # Instruction-tuning (high-quality only)
        instruction_tuning = self._generate_instruction_data(trajectories)

        return TrainingSignals(
            dpo_pairs=dpo_pairs,
            reward_records=reward_records,
            judgment_records=judgment_records,
            instruction_tuning=instruction_tuning,
            generation=generation,
            n_agents=len(trajectories),
            avg_reward=float(np.mean(rewards)),
            latent_novelty_mean=float(np.mean(novelties)),
        )

    def _generate_dpo_pairs(
        self,
        trajectories: list[EvolutionTrajectory],
        rewards: list[float],
    ) -> list[dict[str, Any]]:
        """Generate DPO preference pairs by comparing agents.

        Pairs high-reward (chosen) with low-reward (rejected) trajectories.
        The margin must exceed dpo_min_margin for the pair to be useful.
        """
        pairs: list[dict[str, Any]] = []
        scored = sorted(zip(trajectories, rewards, strict=True), key=lambda x: x[1], reverse=True)
        n = len(scored)

        for i in range(n // 2):
            top_traj, top_reward = scored[i]
            bottom_traj, bottom_reward = scored[n - 1 - i]

            margin = top_reward - bottom_reward
            if margin < self.config.dpo_min_margin:
                continue

            pairs.append(
                {
                    "prompt": _build_evolution_prompt(top_traj),
                    "chosen": _trajectory_to_response(top_traj),
                    "rejected": _trajectory_to_response(bottom_traj),
                    "chosen_reward": top_reward,
                    "rejected_reward": bottom_reward,
                    "margin": margin,
                    "chosen_agent": top_traj.agent_id,
                    "rejected_agent": bottom_traj.agent_id,
                    "generation": top_traj.generation,
                }
            )

        return pairs

    def _generate_reward_records(
        self,
        trajectories: list[EvolutionTrajectory],
        rewards: list[float],
    ) -> list[dict[str, Any]]:
        """Generate reward model training records."""
        records: list[dict[str, Any]] = []
        for traj, reward in zip(trajectories, rewards, strict=True):
            records.append(
                {
                    "task": _build_evolution_prompt(traj),
                    "response": _trajectory_to_response(traj),
                    "reward": reward,
                    "agent_id": traj.agent_id,
                    "generation": traj.generation,
                    "phi_score": traj.phi_score,
                    "coherence": traj.coherence,
                    "gea_score": traj.gea_score,
                    "novelty": traj.novelty,
                }
            )
        return records

    def _generate_judgment_records(
        self,
        trajectories: list[EvolutionTrajectory],
    ) -> list[dict[str, Any]]:
        """Generate judgment training data from trajectory 12D positions.

        Each record assesses whether an agent's state is HIHO-optimal.
        """
        records: list[dict[str, Any]] = []
        for traj in trajectories:
            brane_dims = traj.trajectory_12d[4:11]
            hiho_dist = float(np.mean((brane_dims - HIHO) ** 2))
            alignment = max(0.0, 1.0 - hiho_dist * 4.0)

            # SPIN check: rotation (idx 6) and precession (idx 7) alignment
            if len(traj.trajectory_12d) >= 8:
                rot = traj.trajectory_12d[6]
                prec = traj.trajectory_12d[7]
                spin_aligned = (rot >= 0.5) == (prec >= 0.5)
                spin_score = 1.0 if spin_aligned else 0.0
            else:
                spin_score = 0.5

            improved = alignment > 0.5
            records.append(
                {
                    "context": f"Agent {traj.agent_id} at generation {traj.generation}",
                    "state_12d": traj.trajectory_12d[:6].tolist(),
                    "decision": "evolve" if improved else "refine",
                    "optimal_decision": "maintain" if alignment > 0.8 else "adjust",
                    "alignment_score": alignment,
                    "spin_alignment": spin_score,
                    "reasoning": (
                        f"HIHO distance {hiho_dist:.4f}, "
                        f"alignment {alignment:.3f}, "
                        f"SPIN {'aligned' if spin_score > 0.5 else 'misaligned'}"
                    ),
                    "agent_id": traj.agent_id,
                    "generation": traj.generation,
                }
            )
        return records

    def _generate_instruction_data(
        self,
        trajectories: list[EvolutionTrajectory],
    ) -> list[dict[str, Any]]:
        """Generate instruction-tuning data from high-quality trajectories.

        Only includes agents that exceed the phi threshold. Each record
        shows the reasoning and outcome of a successful evolution step.
        """
        records: list[dict[str, Any]] = []
        for traj in trajectories:
            if traj.phi_score < self.config.min_phi_score:
                continue

            records.append(
                {
                    "instruction": _build_evolution_prompt(traj),
                    "output": _trajectory_to_response(traj),
                    "metadata": {
                        "agent_id": traj.agent_id,
                        "generation": traj.generation,
                        "phi_score": traj.phi_score,
                        "gea_score": traj.gea_score,
                        "novelty": traj.novelty,
                        "trajectory_12d": traj.trajectory_12d[:6].tolist(),
                    },
                }
            )
        return records


# ---------------------------------------------------------------------------
# Training Data Exporter
# ---------------------------------------------------------------------------


class EvolutionTrainingExporter:
    """Export training signals to JSONL files for local model fine-tuning."""

    def __init__(self, output_dir: Path | None = None) -> None:
        self.output_dir = output_dir or Path("data/training/evolution")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def export(
        self,
        signals: TrainingSignals,
        prefix: str = "",
    ) -> dict[str, Path]:
        """Export all training signal types to JSONL files."""
        p = f"{prefix}_" if prefix else ""
        paths: dict[str, Path] = {}

        if signals.dpo_pairs:
            path = self._write_jsonl(signals.dpo_pairs, f"{p}dpo_pairs.jsonl")
            paths["dpo"] = path

        if signals.reward_records:
            path = self._write_jsonl(signals.reward_records, f"{p}rewards.jsonl")
            paths["rewards"] = path

        if signals.judgment_records:
            path = self._write_jsonl(signals.judgment_records, f"{p}judgments.jsonl")
            paths["judgments"] = path

        if signals.instruction_tuning:
            path = self._write_jsonl(signals.instruction_tuning, f"{p}instructions.jsonl")
            paths["instructions"] = path

        logger.info(
            "Exported training data for generation %d: %d DPO pairs, %d rewards, %d judgments, %d instructions",
            signals.generation,
            len(signals.dpo_pairs),
            len(signals.reward_records),
            len(signals.judgment_records),
            len(signals.instruction_tuning),
        )
        return paths

    def _write_jsonl(self, records: list[dict], filename: str) -> Path:
        """Write records to a JSONL file."""
        path = self.output_dir / filename
        with open(path, "w") as f:
            for record in records:
                f.write(json.dumps(record, default=_json_default) + "\n")
        return path


# ---------------------------------------------------------------------------
# Full Pipeline Orchestrator
# ---------------------------------------------------------------------------


@dataclass
class EvolutionRoundResult:
    """Result of one complete evolution-to-training round."""

    generation: int
    n_candidates: int
    n_parents_selected: int
    n_offspring_archived: int
    training_signals: TrainingSignals
    exported_paths: dict[str, Path]
    latent_novelty_scores: list[float]
    archive_stats: dict[str, Any]
    elapsed_seconds: float


class EvolutionTrainingPipeline:
    """Orchestrate the full GEA -> FLUME VAE -> Training pipeline.

    This is the top-level entry point that:
    1. Takes a GroupEvolutionEngine with its archive
    2. Converts archive entries to FLUME trajectories (12D + 256D)
    3. Computes latent novelty in 256D space
    4. Generates multi-format training signals (DPO, rewards, judgments)
    5. Exports to JSONL for local model fine-tuning
    6. Returns metrics for the next evolution generation's fitness

    Usage::

        engine = GroupEvolutionEngine()
        # ... run evolution generations, build archive ...

        pipeline = EvolutionTrainingPipeline()
        result = pipeline.run_round(
            engine=engine,
            trace_sources=agent_traces,
            task_ids=probe_tasks,
            agents=agent_configs,
        )

        # Training data now at data/training/evolution/
        # Fine-tune with: python -m llamafactory.cli.train config.yaml
    """

    def __init__(
        self,
        config: EvolutionTrainingConfig | None = None,
    ) -> None:
        self.config = config or EvolutionTrainingConfig()
        self.converter = TraceToTrajectoryConverter()
        self.signal_generator = EvolutionTrainingSignalGenerator(self.config)
        self.exporter = EvolutionTrainingExporter(self.config.output_dir)
        self.latent_scorer = LatentNoveltyScorer()

    def run_round(
        self,
        engine: GroupEvolutionEngine,
        trace_sources: dict[str, list[ExperienceTrace]],
        task_ids: list[str],
        agents: list[dict[str, Any]],
    ) -> EvolutionRoundResult:
        """Execute one complete evolution-to-training round.

        Parameters
        ----------
        engine : GroupEvolutionEngine
            The GEA engine with current archive state.
        trace_sources : dict
            Mapping of agent_id -> list of ExperienceTrace.
        task_ids : list[str]
            Probe task identifiers for candidate evaluation.
        agents : list[dict]
            Agent configurations with execution_results, coherence, etc.

        Returns
        -------
        EvolutionRoundResult
            Complete metrics and exported file paths.
        """
        start = time.time()

        # --- Stage 1: Build candidates and select parents ---
        candidates = engine.build_candidates(agents, task_ids)
        parents = engine.select_parents(candidates)

        # --- Stage 2: Aggregate experience ---
        pool = engine.aggregate_experience(parents, trace_sources)

        # --- Stage 3: Convert to FLUME trajectories ---
        # From the experience pool (current generation)
        pool_trajectories = self.converter.pool_to_trajectories(pool, candidates)

        # From archive entries (accumulated generations)
        archive_trajectories = [
            self.converter.archive_entry_to_trajectory(entry, trace_sources.get(entry.agent_id, []))
            for entry in engine.archive
        ]

        all_trajectories = pool_trajectories + archive_trajectories

        # --- Stage 4: Compute latent novelty ---
        latent_novelties = [
            self.latent_scorer.compute_latent_novelty(t, all_trajectories) for t in all_trajectories
        ]

        # --- Stage 5: Generate training signals ---
        signals = self.signal_generator.generate_signals(
            all_trajectories,
            generation=engine._generation,
        )

        # --- Stage 6: Export ---
        prefix = f"gen{engine._generation:04d}"
        exported = self.exporter.export(signals, prefix=prefix)

        # --- Stage 7: Add new offspring to archive ---
        # Capture generation BEFORE the loop: add_to_archive() increments
        # engine._generation once per call, so reading it after the loop
        # would report a stale count (off by n_archived).
        generation = engine._generation
        n_archived = 0
        for parent in parents:
            if parent.success_vector is not None:
                offspring_id = f"{parent.agent_id}_gen{engine._generation}"
                engine.add_to_archive(
                    agent_id=offspring_id,
                    parent_ids=[parent.agent_id],
                    success_vector=parent.success_vector,
                )
                n_archived += 1

        elapsed = time.time() - start

        result = EvolutionRoundResult(
            generation=generation,
            n_candidates=len(candidates),
            n_parents_selected=len(parents),
            n_offspring_archived=n_archived,
            training_signals=signals,
            exported_paths=exported,
            latent_novelty_scores=latent_novelties,
            archive_stats=engine.get_archive_stats(),
            elapsed_seconds=elapsed,
        )

        logger.info(
            "Evolution round %d complete: %d candidates, %d parents, "
            "%d archived, %.1fs | Training: %d DPO, %d rewards, "
            "%d judgments, %d instructions | Latent novelty mean: %.3f",
            result.generation,
            result.n_candidates,
            result.n_parents_selected,
            result.n_offspring_archived,
            result.elapsed_seconds,
            len(signals.dpo_pairs),
            len(signals.reward_records),
            len(signals.judgment_records),
            len(signals.instruction_tuning),
            float(np.mean(latent_novelties)) if latent_novelties else 0.0,
        )

        return result

    def run_multi_generation(
        self,
        engine: GroupEvolutionEngine,
        trace_sources: dict[str, list[ExperienceTrace]],
        task_ids: list[str],
        agents: list[dict[str, Any]],
        n_generations: int = 5,
    ) -> list[EvolutionRoundResult]:
        """Run multiple evolution-to-training generations.

        Each generation builds on the previous archive, accumulating
        training data across generations for the local model.
        """
        results: list[EvolutionRoundResult] = []
        for gen in range(n_generations):
            logger.info("=== Generation %d/%d ===", gen + 1, n_generations)
            result = self.run_round(engine, trace_sources, task_ids, agents)
            results.append(result)

        # Summarize
        total_dpo = sum(len(r.training_signals.dpo_pairs) for r in results)
        total_rewards = sum(len(r.training_signals.reward_records) for r in results)
        total_instructions = sum(len(r.training_signals.instruction_tuning) for r in results)

        logger.info(
            "Multi-generation complete (%d rounds): %d total DPO pairs, %d reward records, %d instructions",
            n_generations,
            total_dpo,
            total_rewards,
            total_instructions,
        )
        return results


# ---------------------------------------------------------------------------
# Feedback: Fine-tuned Model -> GEA Fitness
# ---------------------------------------------------------------------------


@dataclass
class ModelEvaluationResult:
    """Result of evaluating a fine-tuned model on probe tasks."""

    model_name: str
    task_results: dict[str, bool]  # task_id -> success
    avg_coherence: float
    avg_phi_score: float
    latent_novelty: float  # Novelty of model's behavior in FLUME space


class FitnessEvaluator:
    """Evaluate fine-tuned local model and convert to GEA fitness scores.

    This closes the feedback loop: the model trained on evolutionary
    experience is evaluated on probe tasks, and its performance becomes
    the fitness signal for the next evolution generation.
    """

    def __init__(self, encoder: ExperienceEncoder | None = None) -> None:
        self.encoder = encoder or ExperienceEncoder()

    def evaluation_to_candidate(
        self,
        eval_result: ModelEvaluationResult,
        task_ids: list[str],
    ) -> AgentCandidate:
        """Convert model evaluation into a GEA AgentCandidate.

        The fine-tuned model becomes a candidate in the next evolution
        round, competing with and learning from other agents.
        """
        results = [eval_result.task_results.get(tid, False) for tid in task_ids]
        success_vector = TaskSuccessVector.from_execution_history(
            agent_id=eval_result.model_name,
            task_ids=task_ids,
            results=results,
        )

        return AgentCandidate(
            agent_id=eval_result.model_name,
            performance=success_vector.solve_rate,
            novelty=eval_result.latent_novelty,
            coherence=eval_result.avg_coherence,
            success_vector=success_vector,
            metadata={
                "avg_phi_score": eval_result.avg_phi_score,
                "source": "finetuned_local_model",
            },
        )

    def evaluation_to_experience_dict(
        self,
        eval_result: ModelEvaluationResult,
    ) -> dict[str, Any]:
        """Convert evaluation into an experience dict for 256D encoding.

        This feeds the fine-tuned model's behavior back into the FLUME
        VAE's training set, enriching the latent manifold with data from
        models that were themselves trained on evolutionary experience.
        """
        # Build 12D trajectory from task results
        task_successes = list(eval_result.task_results.values())
        traj_12d = np.zeros(12, dtype=np.float64)
        n = min(len(task_successes), 12)
        for i in range(n):
            traj_12d[i] = 1.0 if task_successes[i] else 0.0

        return {
            "trajectory": traj_12d.tolist(),
            "phi_score": eval_result.avg_phi_score,
            "mission_id": f"eval_{eval_result.model_name}",
            "agent_id": eval_result.model_name,
            "skill_name": "finetuned_eval",
            "operation_type": "generate",
            "success": float(eval_result.avg_phi_score > 0.5),
            "cache_hit_rate": 0.0,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hiho_coherence(performance: float) -> float:
    """Map performance to HIHO coherence: optimal at 0.5."""
    return 1.0 - abs(performance - HIHO) * 2.0


def _cosine_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Cosine distance between two vectors."""
    eps = 1e-8
    dot = float(np.dot(a, b))
    norm_a = float(np.linalg.norm(a))
    norm_b = float(np.linalg.norm(b))
    similarity = dot / (norm_a * norm_b + eps)
    return 1.0 - similarity


def _trajectory_reward(traj: EvolutionTrajectory) -> float:
    """Compute HIHO-aligned reward from an evolution trajectory.

    Components:
    1. HIHO proximity of brane dimensions (dims 4-10)
    2. SPIN alignment (rotation dim 6 vs precession dim 7)
    3. Performance score (direct from GEA)
    4. Novelty bonus (exploration reward)
    """
    dims = traj.trajectory_12d

    # HIHO proximity
    brane = dims[4:11] if len(dims) >= 11 else dims
    hiho_score = max(0.0, 1.0 - float(np.mean((brane - HIHO) ** 2)) * 4.0)

    # SPIN alignment
    if len(dims) >= 8:
        rot = dims[6]
        prec = dims[7]
        spin = 1.0 if (rot >= 0.5) == (prec >= 0.5) else 0.0
    else:
        spin = 0.5

    # Combine
    reward = 0.3 * hiho_score + 0.1 * spin + 0.4 * traj.performance + 0.2 * min(traj.novelty, 1.0)
    return float(np.clip(reward, 0.0, 1.0))


def _build_evolution_prompt(traj: EvolutionTrajectory) -> str:
    """Build a training prompt from an evolution trajectory."""
    return (
        f"Agent {traj.agent_id} (generation {traj.generation}): "
        f"Execute evolution step with performance target {traj.performance:.2f}, "
        f"novelty target {traj.novelty:.2f}. "
        f"Maintain HIHO coherence near 0.5."
    )


def _trajectory_to_response(traj: EvolutionTrajectory) -> str:
    """Convert trajectory to a training response string."""
    traj_str = ", ".join(f"{d:.3f}" for d in traj.trajectory_12d[:6])
    trace_summary = {}
    for t in traj.traces:
        key = t.trace_type.value
        trace_summary[key] = trace_summary.get(key, 0) + 1

    return (
        f"## Evolution Result\n\n"
        f"**Performance:** {traj.performance:.3f}\n"
        f"**Novelty:** {traj.novelty:.3f}\n"
        f"**GEA Score:** {traj.gea_score:.3f}\n"
        f"**Coherence:** {traj.coherence:.3f}\n"
        f"**Phi Score:** {traj.phi_score:.3f}\n\n"
        f"**12D Position (first 6):** [{traj_str}]\n\n"
        f"**Trace Summary:** {trace_summary}\n\n"
        f"**Analysis:**\n"
        f"- Agent achieved {'target' if traj.performance > 0.5 else 'partial'} "
        f"performance through generation {traj.generation}\n"
        f"- Novelty score indicates "
        f"{'diverse' if traj.novelty > 0.5 else 'convergent'} behavior\n"
        f"- HIHO coherence {'stable' if abs(traj.coherence - 0.5) < 0.2 else 'drifted'}"
    )


def _json_default(obj: Any) -> Any:
    """JSON serializer for numpy types."""
    if isinstance(obj, (np.integer,)):
        return int(obj)
    if isinstance(obj, (np.floating,)):
        return float(obj)
    if isinstance(obj, np.ndarray):
        return obj.tolist()
    if isinstance(obj, Path):
        return str(obj)
    raise TypeError(f"Not JSON serializable: {type(obj)}")
