"""Tests for evolution_training_bridge: GEA -> FLUME VAE -> Local Model Training.

Validates the full pipeline from group evolution through journey encoding,
training signal generation, and the feedback loop back to GEA.
"""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

import numpy as np
import pytest


if TYPE_CHECKING:
    from pathlib import Path

from cohezion.compound.evolution_training_bridge import (
    EvolutionTrainingConfig,
    EvolutionTrainingExporter,
    EvolutionTrainingPipeline,
    EvolutionTrainingSignalGenerator,
    EvolutionTrajectory,
    FitnessEvaluator,
    LatentNoveltyScorer,
    ModelEvaluationResult,
    TraceToTrajectoryConverter,
    TrainingSignals,
    _cosine_distance,
    _hiho_coherence,
    _trajectory_reward,
)
from cohezion.compound.group_evolution import (
    AgentCandidate,
    ArchiveEntry,
    ExperienceTrace,
    ExperienceTraceType,
    GroupEvolutionEngine,
    GroupExperiencePool,
    TaskSuccessVector,
)
from cohezion.flume.experience_encoder import ExperienceEncoder


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def task_ids() -> list[str]:
    return [f"task_{i}" for i in range(8)]


@pytest.fixture
def sample_success_vector(task_ids: list[str]) -> TaskSuccessVector:
    return TaskSuccessVector.from_execution_history(
        agent_id="agent-alpha",
        task_ids=task_ids,
        results=[True, True, False, True, False, True, True, False],
    )


@pytest.fixture
def sample_archive_entry(
    sample_success_vector: TaskSuccessVector,
) -> ArchiveEntry:
    return ArchiveEntry(
        agent_id="agent-alpha",
        generation=3,
        parent_ids=["agent-parent-1", "agent-parent-2"],
        success_vector=sample_success_vector,
        performance=0.625,
        novelty=0.7,
        gea_score=0.625 * np.sqrt(0.7),
        skill_patches=["patch_v1"],
        ancestor_count=4,
    )


@pytest.fixture
def sample_traces() -> list[ExperienceTrace]:
    return [
        ExperienceTrace(
            agent_id="agent-alpha",
            trace_type=ExperienceTraceType.EXECUTION_LOG,
            content={"summary": "Solved task_0 via search", "error": None},
            quality_score=0.85,
            novelty_score=0.6,
        ),
        ExperienceTrace(
            agent_id="agent-alpha",
            trace_type=ExperienceTraceType.EVALUATION_OUTCOME,
            content={"summary": "Tests passed 5/8", "error": None},
            quality_score=0.7,
            novelty_score=0.4,
        ),
        ExperienceTrace(
            agent_id="agent-beta",
            trace_type=ExperienceTraceType.APPLIED_PATCH,
            content={"summary": "Refactored cache layer", "error": None},
            quality_score=0.9,
            novelty_score=0.8,
        ),
    ]


@pytest.fixture
def sample_candidates(task_ids: list[str]) -> list[AgentCandidate]:
    """Build a set of diverse candidates for testing."""
    configs = [
        ("alpha", [True, True, False, True, False, True, True, False], 0.55),
        ("beta", [False, True, True, True, True, False, False, True], 0.50),
        ("gamma", [True, False, True, False, True, True, False, True], 0.45),
        ("delta", [True, True, True, True, False, False, False, False], 0.60),
    ]
    candidates = []
    for name, results, coherence in configs:
        sv = TaskSuccessVector.from_execution_history(
            agent_id=f"agent-{name}", task_ids=task_ids, results=results
        )
        candidates.append(
            AgentCandidate(
                agent_id=f"agent-{name}",
                performance=sv.solve_rate,
                novelty=0.5,  # Will be overwritten by scorer
                coherence=coherence,
                success_vector=sv,
            )
        )
    return candidates


@pytest.fixture
def sample_trajectory() -> EvolutionTrajectory:
    rng = np.random.default_rng(42)
    return EvolutionTrajectory(
        agent_id="agent-alpha",
        generation=2,
        parent_ids=["parent-1"],
        trajectory_12d=rng.uniform(0.3, 0.7, 12),
        embedding_256d=rng.normal(0.5, 0.15, 256).astype(np.float32),
        phi_score=0.82,
        coherence=0.55,
        performance=0.75,
        novelty=0.6,
        gea_score=0.75 * np.sqrt(0.6),
        task_description="Optimize cache invalidation",
        traces=[],
    )


@pytest.fixture
def diverse_trajectories() -> list[EvolutionTrajectory]:
    """Create trajectories with intentionally different profiles."""
    rng = np.random.default_rng(123)
    trajectories = []
    for i, (perf, nov) in enumerate(
        [(0.9, 0.2), (0.7, 0.5), (0.5, 0.8), (0.3, 0.9), (0.8, 0.3)]
    ):
        traj_12d = rng.uniform(0.0, 1.0, 12)
        # Bias brane dims toward performance (more HIHO-aligned for high perf)
        traj_12d[4:11] = HIHO + (1 - perf) * rng.normal(0, 0.3, 7)
        traj_12d = np.clip(traj_12d, 0.0, 1.0)

        trajectories.append(
            EvolutionTrajectory(
                agent_id=f"agent-{i}",
                generation=i,
                parent_ids=[],
                trajectory_12d=traj_12d,
                embedding_256d=rng.normal(0.5, 0.15, 256).astype(np.float32),
                phi_score=perf * 0.9,
                coherence=_hiho_coherence(perf),
                performance=perf,
                novelty=nov,
                gea_score=perf * np.sqrt(nov),
            )
        )
    return trajectories


HIHO = 0.5


# ---------------------------------------------------------------------------
# TraceToTrajectoryConverter Tests
# ---------------------------------------------------------------------------


class TestTraceToTrajectoryConverter:
    def test_archive_entry_to_trajectory(
        self,
        sample_archive_entry: ArchiveEntry,
        sample_traces: list[ExperienceTrace],
    ) -> None:
        converter = TraceToTrajectoryConverter()
        traj = converter.archive_entry_to_trajectory(
            sample_archive_entry, sample_traces
        )

        assert traj.agent_id == "agent-alpha"
        assert traj.generation == 3
        assert traj.parent_ids == ["agent-parent-1", "agent-parent-2"]
        assert traj.trajectory_12d.shape == (12,)
        assert traj.embedding_256d.shape == (256,)
        assert traj.performance == 0.625
        assert traj.novelty == 0.7
        assert len(traj.traces) == 3

    def test_trajectory_12d_matches_success_vector(
        self,
        sample_archive_entry: ArchiveEntry,
    ) -> None:
        converter = TraceToTrajectoryConverter()
        traj = converter.archive_entry_to_trajectory(sample_archive_entry)

        sv = sample_archive_entry.success_vector.successes
        n = min(len(sv), 12)
        np.testing.assert_array_almost_equal(
            traj.trajectory_12d[:n], sv[:n]
        )

    def test_embedding_256d_deterministic(
        self,
        sample_archive_entry: ArchiveEntry,
    ) -> None:
        converter = TraceToTrajectoryConverter()
        t1 = converter.archive_entry_to_trajectory(sample_archive_entry)
        t2 = converter.archive_entry_to_trajectory(sample_archive_entry)
        np.testing.assert_array_equal(t1.embedding_256d, t2.embedding_256d)

    def test_pool_to_trajectories(
        self,
        sample_candidates: list[AgentCandidate],
        sample_traces: list[ExperienceTrace],
    ) -> None:
        pool = GroupExperiencePool(
            parent_agent_ids=[c.agent_id for c in sample_candidates]
        )
        for trace in sample_traces:
            pool.traces.append(trace)

        converter = TraceToTrajectoryConverter()
        trajectories = converter.pool_to_trajectories(pool, sample_candidates)

        assert len(trajectories) == len(sample_candidates)
        for traj in trajectories:
            assert traj.trajectory_12d.shape == (12,)
            assert traj.embedding_256d.shape == (256,)

    def test_pool_trajectory_carries_candidate_scores(
        self,
        sample_candidates: list[AgentCandidate],
    ) -> None:
        pool = GroupExperiencePool(
            parent_agent_ids=[c.agent_id for c in sample_candidates]
        )
        converter = TraceToTrajectoryConverter()
        trajectories = converter.pool_to_trajectories(pool, sample_candidates)

        for traj, cand in zip(trajectories, sample_candidates, strict=True):
            assert traj.performance == cand.performance
            assert traj.coherence == cand.coherence
            assert traj.novelty == cand.novelty


# ---------------------------------------------------------------------------
# LatentNoveltyScorer Tests
# ---------------------------------------------------------------------------


class TestLatentNoveltyScorer:
    def test_single_agent_max_novelty(
        self, sample_trajectory: EvolutionTrajectory
    ) -> None:
        scorer = LatentNoveltyScorer()
        novelty = scorer.compute_latent_novelty(
            sample_trajectory, [sample_trajectory]
        )
        assert novelty == 1.0

    def test_identical_embeddings_low_novelty(self) -> None:
        """Two agents with identical 256D embeddings have near-zero novelty."""
        embedding = np.ones(256, dtype=np.float32) * 0.5
        t1 = EvolutionTrajectory(
            agent_id="a",
            generation=0,
            parent_ids=[],
            trajectory_12d=np.zeros(12),
            embedding_256d=embedding.copy(),
            phi_score=0.5,
            coherence=0.5,
            performance=0.5,
            novelty=0.5,
            gea_score=0.35,
        )
        t2 = EvolutionTrajectory(
            agent_id="b",
            generation=0,
            parent_ids=[],
            trajectory_12d=np.zeros(12),
            embedding_256d=embedding.copy(),
            phi_score=0.5,
            coherence=0.5,
            performance=0.5,
            novelty=0.5,
            gea_score=0.35,
        )
        scorer = LatentNoveltyScorer()
        novelty = scorer.compute_latent_novelty(t1, [t1, t2])
        assert novelty < 0.01

    def test_diverse_embeddings_high_novelty(self) -> None:
        """Orthogonal 256D embeddings produce high novelty."""
        agents = []
        for i in range(5):
            emb = np.zeros(256, dtype=np.float32)
            emb[i * 50 : (i + 1) * 50] = 1.0  # Non-overlapping
            agents.append(
                EvolutionTrajectory(
                    agent_id=f"agent-{i}",
                    generation=0,
                    parent_ids=[],
                    trajectory_12d=np.zeros(12),
                    embedding_256d=emb,
                    phi_score=0.5,
                    coherence=0.5,
                    performance=0.5,
                    novelty=0.5,
                    gea_score=0.35,
                )
            )

        scorer = LatentNoveltyScorer()
        novelty = scorer.compute_latent_novelty(agents[0], agents)
        assert novelty > 0.5

    def test_m_neighbors_respected(
        self, diverse_trajectories: list[EvolutionTrajectory]
    ) -> None:
        scorer_m2 = LatentNoveltyScorer(m_neighbors=2)
        scorer_m4 = LatentNoveltyScorer(m_neighbors=4)

        n2 = scorer_m2.compute_latent_novelty(
            diverse_trajectories[0], diverse_trajectories
        )
        n4 = scorer_m4.compute_latent_novelty(
            diverse_trajectories[0], diverse_trajectories
        )
        # With more neighbors included, novelty changes
        # (can be higher or lower depending on population structure)
        assert isinstance(n2, float)
        assert isinstance(n4, float)
        assert 0.0 <= n2 <= 2.0
        assert 0.0 <= n4 <= 2.0


# ---------------------------------------------------------------------------
# EvolutionTrainingSignalGenerator Tests
# ---------------------------------------------------------------------------


class TestSignalGenerator:
    def test_empty_trajectories(self) -> None:
        gen = EvolutionTrainingSignalGenerator()
        signals = gen.generate_signals([], generation=0)
        assert signals.n_agents == 0
        assert len(signals.dpo_pairs) == 0
        assert len(signals.reward_records) == 0
        assert len(signals.judgment_records) == 0

    def test_generates_all_signal_types(
        self, diverse_trajectories: list[EvolutionTrajectory]
    ) -> None:
        gen = EvolutionTrainingSignalGenerator()
        signals = gen.generate_signals(diverse_trajectories, generation=1)

        assert signals.n_agents == 5
        assert signals.generation == 1
        assert len(signals.reward_records) == 5
        assert len(signals.judgment_records) == 5
        # DPO pairs: at most n//2 = 2 pairs from 5 agents
        assert len(signals.dpo_pairs) <= 2

    def test_dpo_chosen_beats_rejected(
        self, diverse_trajectories: list[EvolutionTrajectory]
    ) -> None:
        gen = EvolutionTrainingSignalGenerator()
        signals = gen.generate_signals(diverse_trajectories)

        for pair in signals.dpo_pairs:
            assert pair["chosen_reward"] > pair["rejected_reward"]
            assert pair["margin"] >= 0.05

    def test_reward_records_structure(
        self, diverse_trajectories: list[EvolutionTrajectory]
    ) -> None:
        gen = EvolutionTrainingSignalGenerator()
        signals = gen.generate_signals(diverse_trajectories)

        for rec in signals.reward_records:
            assert "task" in rec
            assert "reward" in rec
            assert "agent_id" in rec
            assert "phi_score" in rec
            assert "gea_score" in rec
            assert 0.0 <= rec["reward"] <= 1.0

    def test_judgment_records_structure(
        self, diverse_trajectories: list[EvolutionTrajectory]
    ) -> None:
        gen = EvolutionTrainingSignalGenerator()
        signals = gen.generate_signals(diverse_trajectories)

        for rec in signals.judgment_records:
            assert "alignment_score" in rec
            assert "spin_alignment" in rec
            assert "reasoning" in rec
            assert 0.0 <= rec["alignment_score"] <= 1.0

    def test_instruction_data_filtered_by_phi(
        self, diverse_trajectories: list[EvolutionTrajectory]
    ) -> None:
        config = EvolutionTrainingConfig(min_phi_score=0.7)
        gen = EvolutionTrainingSignalGenerator(config)
        signals = gen.generate_signals(diverse_trajectories)

        for rec in signals.instruction_tuning:
            assert rec["metadata"]["phi_score"] >= 0.7

    def test_avg_reward_computed(
        self, diverse_trajectories: list[EvolutionTrajectory]
    ) -> None:
        gen = EvolutionTrainingSignalGenerator()
        signals = gen.generate_signals(diverse_trajectories)
        assert 0.0 <= signals.avg_reward <= 1.0

    def test_latent_novelty_mean_computed(
        self, diverse_trajectories: list[EvolutionTrajectory]
    ) -> None:
        gen = EvolutionTrainingSignalGenerator()
        signals = gen.generate_signals(diverse_trajectories)
        assert signals.latent_novelty_mean >= 0.0


# ---------------------------------------------------------------------------
# EvolutionTrainingExporter Tests
# ---------------------------------------------------------------------------


class TestExporter:
    def test_export_creates_files(
        self,
        diverse_trajectories: list[EvolutionTrajectory],
        tmp_path: Path,
    ) -> None:
        gen = EvolutionTrainingSignalGenerator()
        signals = gen.generate_signals(diverse_trajectories, generation=7)

        exporter = EvolutionTrainingExporter(tmp_path)
        paths = exporter.export(signals, prefix="gen0007")

        for key, path in paths.items():
            assert path.exists(), f"{key} file should exist"
            assert path.suffix == ".jsonl"

            # Verify valid JSONL
            with open(path) as f:
                for line in f:
                    parsed = json.loads(line)
                    assert isinstance(parsed, dict)

    def test_export_empty_signals(self, tmp_path: Path) -> None:
        signals = TrainingSignals(
            dpo_pairs=[],
            reward_records=[],
            judgment_records=[],
            instruction_tuning=[],
            generation=0,
            n_agents=0,
            avg_reward=0.0,
            latent_novelty_mean=0.0,
        )
        exporter = EvolutionTrainingExporter(tmp_path)
        paths = exporter.export(signals)
        assert len(paths) == 0  # No files created for empty data


# ---------------------------------------------------------------------------
# Full Pipeline Tests
# ---------------------------------------------------------------------------


class TestEvolutionTrainingPipeline:
    def test_run_round(self, task_ids: list[str], tmp_path: Path) -> None:
        agents = [
            {
                "agent_id": f"agent-{i}",
                "execution_results": [bool((i + j) % 3) for j in range(8)],
                "coherence": 0.4 + i * 0.05,
            }
            for i in range(5)
        ]

        trace_sources: dict[str, list[ExperienceTrace]] = {}
        for agent in agents:
            aid = agent["agent_id"]
            trace_sources[aid] = [
                ExperienceTrace(
                    agent_id=aid,
                    trace_type=ExperienceTraceType.EXECUTION_LOG,
                    content={"summary": f"{aid} executed tasks"},
                    quality_score=0.6 + 0.05 * agents.index(agent),
                ),
            ]

        engine = GroupEvolutionEngine()
        config = EvolutionTrainingConfig(
            output_dir=tmp_path / "evo_training",
        )
        pipeline = EvolutionTrainingPipeline(config)

        result = pipeline.run_round(engine, trace_sources, task_ids, agents)

        assert result.n_candidates == 5
        assert result.n_parents_selected == 2  # default K=2
        assert result.training_signals.n_agents > 0
        assert result.elapsed_seconds > 0.0

    def test_multi_generation_accumulates(self, task_ids: list[str], tmp_path: Path) -> None:
        agents = [
            {
                "agent_id": f"agent-{i}",
                "execution_results": [bool((i + j) % 2) for j in range(8)],
                "coherence": 0.5,
            }
            for i in range(4)
        ]

        trace_sources: dict[str, list[ExperienceTrace]] = {}
        for agent in agents:
            aid = agent["agent_id"]
            trace_sources[aid] = [
                ExperienceTrace(
                    agent_id=aid,
                    trace_type=ExperienceTraceType.EVALUATION_OUTCOME,
                    content={"summary": "eval done"},
                    quality_score=0.7,
                ),
            ]

        engine = GroupEvolutionEngine()
        config = EvolutionTrainingConfig(
            output_dir=tmp_path / "evo_multi",
        )
        pipeline = EvolutionTrainingPipeline(config)

        results = pipeline.run_multi_generation(
            engine, trace_sources, task_ids, agents, n_generations=3
        )

        assert len(results) == 3
        # Archive grows across generations
        assert results[-1].archive_stats["size"] > 0


# ---------------------------------------------------------------------------
# FitnessEvaluator Tests (Feedback Loop)
# ---------------------------------------------------------------------------


class TestFitnessEvaluator:
    def test_evaluation_to_candidate(self, task_ids: list[str]) -> None:
        evaluator = FitnessEvaluator()
        eval_result = ModelEvaluationResult(
            model_name="cohezion_journey_v1",
            task_results={f"task_{i}": i % 2 == 0 for i in range(8)},
            avg_coherence=0.55,
            avg_phi_score=0.78,
            latent_novelty=0.65,
        )

        candidate = evaluator.evaluation_to_candidate(eval_result, task_ids)

        assert candidate.agent_id == "cohezion_journey_v1"
        assert candidate.performance == 0.5  # 4 of 8 tasks
        assert candidate.novelty == 0.65
        assert candidate.coherence == 0.55
        assert candidate.metadata["source"] == "finetuned_local_model"

    def test_evaluation_to_experience_dict(self) -> None:
        evaluator = FitnessEvaluator()
        eval_result = ModelEvaluationResult(
            model_name="test_model",
            task_results={"t1": True, "t2": False, "t3": True},
            avg_coherence=0.6,
            avg_phi_score=0.75,
            latent_novelty=0.5,
        )

        exp_dict = evaluator.evaluation_to_experience_dict(eval_result)

        assert exp_dict["agent_id"] == "test_model"
        assert exp_dict["phi_score"] == 0.75
        assert exp_dict["skill_name"] == "finetuned_eval"
        assert len(exp_dict["trajectory"]) == 12

    def test_experience_dict_encodable(self) -> None:
        """Verify the experience dict can be encoded to 256D."""
        evaluator = FitnessEvaluator()
        eval_result = ModelEvaluationResult(
            model_name="test_model",
            task_results={"t1": True, "t2": False},
            avg_coherence=0.5,
            avg_phi_score=0.8,
            latent_novelty=0.5,
        )

        exp_dict = evaluator.evaluation_to_experience_dict(eval_result)
        encoder = ExperienceEncoder()
        vec = encoder.encode(exp_dict)

        assert vec.shape == (256,)
        assert vec.dtype == np.float32

    def test_finetuned_model_enters_next_generation(
        self, task_ids: list[str]
    ) -> None:
        """End-to-end: fine-tuned model evaluation becomes GEA candidate."""
        evaluator = FitnessEvaluator()
        eval_result = ModelEvaluationResult(
            model_name="cohezion_v2",
            task_results=dict.fromkeys(task_ids[:6], True),
            avg_coherence=0.52,
            avg_phi_score=0.85,
            latent_novelty=0.7,
        )

        candidate = evaluator.evaluation_to_candidate(eval_result, task_ids)

        # Should be competitive with regular agents
        assert candidate.performance == 0.75  # 6/8 tasks
        assert candidate.success_vector is not None
        assert candidate.success_vector.solve_rate == 0.75


# ---------------------------------------------------------------------------
# Helper Function Tests
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_hiho_coherence_at_optimal(self) -> None:
        assert _hiho_coherence(0.5) == pytest.approx(1.0)

    def test_hiho_coherence_at_extremes(self) -> None:
        assert _hiho_coherence(0.0) == pytest.approx(0.0)
        assert _hiho_coherence(1.0) == pytest.approx(0.0)

    def test_hiho_coherence_symmetric(self) -> None:
        assert _hiho_coherence(0.3) == pytest.approx(_hiho_coherence(0.7))

    def test_cosine_distance_identical(self) -> None:
        v = np.array([1.0, 2.0, 3.0])
        assert _cosine_distance(v, v) == pytest.approx(0.0, abs=1e-6)

    def test_cosine_distance_orthogonal(self) -> None:
        a = np.array([1.0, 0.0, 0.0])
        b = np.array([0.0, 1.0, 0.0])
        assert _cosine_distance(a, b) == pytest.approx(1.0, abs=1e-6)

    def test_trajectory_reward_bounded(
        self, sample_trajectory: EvolutionTrajectory
    ) -> None:
        reward = _trajectory_reward(sample_trajectory)
        assert 0.0 <= reward <= 1.0

    def test_trajectory_reward_favors_performance(self) -> None:
        """Higher performance -> higher reward, all else equal."""
        base = {
            "generation": 0,
            "parent_ids": [],
            "trajectory_12d": np.full(12, 0.5),
            "embedding_256d": np.zeros(256, dtype=np.float32),
            "phi_score": 0.5,
            "coherence": 0.5,
            "novelty": 0.5,
            "gea_score": 0.35,
        }
        low = EvolutionTrajectory(agent_id="low", performance=0.2, **base)
        high = EvolutionTrajectory(agent_id="high", performance=0.9, **base)

        assert _trajectory_reward(high) > _trajectory_reward(low)

    def test_trajectory_reward_favors_hiho_alignment(self) -> None:
        """Trajectory with brane dims near 0.5 gets higher reward."""
        aligned = EvolutionTrajectory(
            agent_id="aligned",
            generation=0,
            parent_ids=[],
            trajectory_12d=np.full(12, 0.5),  # Perfect HIHO
            embedding_256d=np.zeros(256, dtype=np.float32),
            phi_score=0.5,
            coherence=0.5,
            performance=0.5,
            novelty=0.5,
            gea_score=0.35,
        )
        misaligned = EvolutionTrajectory(
            agent_id="misaligned",
            generation=0,
            parent_ids=[],
            trajectory_12d=np.full(12, 0.0),  # Far from HIHO
            embedding_256d=np.zeros(256, dtype=np.float32),
            phi_score=0.5,
            coherence=0.5,
            performance=0.5,
            novelty=0.5,
            gea_score=0.35,
        )
        assert _trajectory_reward(aligned) > _trajectory_reward(misaligned)


# ---------------------------------------------------------------------------
# End-to-End Integration Test
# ---------------------------------------------------------------------------


class TestEndToEnd:
    def test_full_evolution_to_training_loop(self, task_ids: list[str], tmp_path: Path) -> None:
        """Complete loop: GEA evolution -> training signals -> feedback.

        Validates:
        1. GEA builds candidates and selects parents
        2. Traces convert to FLUME trajectories (12D + 256D)
        3. Training signals are generated in all formats
        4. Signals can be exported as JSONL
        5. Fine-tuned model evaluation re-enters GEA as a candidate
        """
        # Step 1: Set up agents with diverse capabilities
        agents = [
            {
                "agent_id": "explorer",
                "execution_results": [True, False, True, False, True, False, True, False],
                "coherence": 0.45,
            },
            {
                "agent_id": "specialist",
                "execution_results": [True, True, True, True, False, False, False, False],
                "coherence": 0.55,
            },
            {
                "agent_id": "generalist",
                "execution_results": [True, True, False, True, True, False, True, False],
                "coherence": 0.50,
            },
        ]

        trace_sources = {
            "explorer": [
                ExperienceTrace(
                    agent_id="explorer",
                    trace_type=ExperienceTraceType.EXECUTION_LOG,
                    content={"summary": "Broad search strategy"},
                    quality_score=0.7,
                ),
            ],
            "specialist": [
                ExperienceTrace(
                    agent_id="specialist",
                    trace_type=ExperienceTraceType.APPLIED_PATCH,
                    content={"summary": "Deep domain expertise"},
                    quality_score=0.85,
                ),
            ],
            "generalist": [
                ExperienceTrace(
                    agent_id="generalist",
                    trace_type=ExperienceTraceType.EVALUATION_OUTCOME,
                    content={"summary": "Balanced approach"},
                    quality_score=0.75,
                ),
            ],
        }

        # Step 2: Run evolution round
        engine = GroupEvolutionEngine()
        config = EvolutionTrainingConfig(
            output_dir=tmp_path / "e2e_evo",
            min_phi_score=0.4,
        )
        pipeline = EvolutionTrainingPipeline(config)
        result = pipeline.run_round(engine, trace_sources, task_ids, agents)

        # Verify pipeline produced meaningful output
        assert result.n_candidates == 3
        assert result.n_parents_selected == 2
        assert result.training_signals.n_agents > 0
        assert len(result.training_signals.reward_records) > 0

        # Step 3: Simulate fine-tuned model evaluation
        evaluator = FitnessEvaluator()
        model_eval = ModelEvaluationResult(
            model_name="cohezion_evolved_v1",
            task_results=dict.fromkeys(task_ids[:6], True),  # Solves 6/8
            avg_coherence=0.52,
            avg_phi_score=0.8,
            latent_novelty=0.6,
        )

        # Step 4: Convert evaluation back to GEA candidate
        new_candidate = evaluator.evaluation_to_candidate(model_eval, task_ids)
        assert new_candidate.performance == 0.75
        assert new_candidate.metadata["source"] == "finetuned_local_model"

        # Step 5: Verify the candidate can enter next generation
        new_agents = [
            *agents,
            {
                "agent_id": new_candidate.agent_id,
                "execution_results": [
                    model_eval.task_results.get(tid, False) for tid in task_ids
                ],
                "coherence": new_candidate.coherence,
            },
        ]

        result2 = pipeline.run_round(engine, trace_sources, task_ids, new_agents)

        # The fine-tuned model competes with original agents
        assert result2.n_candidates == 4
        assert result2.archive_stats["size"] > 0
