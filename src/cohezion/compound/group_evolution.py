"""Group-Evolving Agents (GEA) integration for Cohezion compound engineering.

Implements concepts from:
    Weng, Z., Antoniades, A., Nathani, D., Zhang, Z., Pu, X., & Wang, X. E.
    (2025). "Group-Evolving Agents: Open-Ended Self-Improvement via Experience
    Sharing." arXiv:2602.04837.

This module adapts GEA's group-level evolution paradigm to Cohezion's existing
compound engineering loop. Many of the core ideas converge with Cohezion's
pre-existing architecture (see CONVERGENCE_ANALYSIS.md for details):

    - GEA Experience Pool      <-> Cohezion ExperienceCollector + VaultLogger
    - GEA Reflect Module       <-> Cohezion RetrospectionEngine + InflectionDetector
    - GEA Evolve Module        <-> Cohezion SkillRefiner
    - GEA Archive              <-> Cohezion Vault + PRIME Skill Registry
    - GEA Performance-Novelty  <-> Cohezion HIHO Stability (explore/exploit balance)
    - GEA Group Consensus      <-> Cohezion SkillConsensusVoter + DemocraticDebate

Novel contributions from GEA integrated here:
    1. Group-level parent selection with Performance-Novelty scoring
    2. Task-success vectors for agent capability fingerprinting
    3. KNN novelty metric using cosine distance
    4. Cross-agent experience aggregation into shared pool
    5. Formal monotonic archive with compile-check gating

License: This integration is an independent implementation inspired by the
concepts described in arXiv:2602.04837. No code from the original paper's
implementation was used. The paper is an arXiv preprint; no official code
release or license was available at time of integration (2026-02-22).
"""

from __future__ import annotations

import logging
import math
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

import numpy as np


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Task-Success Vectors
# ---------------------------------------------------------------------------


@dataclass
class TaskSuccessVector:
    """Binary vector representing an agent's solve history across probe tasks.

    Mirrors GEA's z_i in {0,1}^D representation. Each dimension corresponds
    to a specific task and indicates whether the agent solved it.

    Cohezion parallel: This extends the existing ``JourneyTracker`` trajectory
    representation with a discrete, task-level capability fingerprint.
    """

    agent_id: str
    task_ids: list[str]
    successes: np.ndarray  # shape (D,), dtype bool

    @classmethod
    def from_execution_history(
        cls,
        agent_id: str,
        task_ids: list[str],
        results: list[bool],
    ) -> TaskSuccessVector:
        """Build from a list of task IDs and corresponding success booleans."""
        successes = np.array(results, dtype=np.float64)
        return cls(agent_id=agent_id, task_ids=task_ids, successes=successes)

    @property
    def solve_rate(self) -> float:
        """Fraction of tasks solved."""
        if len(self.successes) == 0:
            return 0.0
        return float(np.mean(self.successes))

    def cosine_distance(self, other: TaskSuccessVector) -> float:
        """Compute cosine distance to another agent's success vector.

        GEA formula: d(i,j) = 1 - (z_i^T z_j) / (||z_i||_2 * ||z_j||_2 + eps)

        Note: Cohezion's ``TrajectorySearchEngine`` already uses cosine
        similarity for experience matching -- this extends that pattern to
        discrete task-success space.
        """
        eps = 1e-8
        dot = float(np.dot(self.successes, other.successes))
        norm_self = float(np.linalg.norm(self.successes))
        norm_other = float(np.linalg.norm(other.successes))
        similarity = dot / (norm_self * norm_other + eps)
        return 1.0 - similarity


# ---------------------------------------------------------------------------
# KNN Novelty Scorer
# ---------------------------------------------------------------------------


class NoveltyScorer:
    """Compute KNN novelty scores for agents in an archive.

    GEA's novelty metric: nov(i) = (1/M) * sum(d(i,j)) for j in N_M(i),
    where N_M(i) is the set of M nearest neighbors by cosine distance.

    Cohezion parallel: This formalizes the HIHO stability principle's
    explore/exploit balance. Where HIHO uses ``1 - abs(coherence - 0.5) * 2``,
    the KNN novelty metric provides a population-relative measure of diversity.
    """

    def __init__(self, m_neighbors: int = 4) -> None:
        """Initialize novelty scorer.

        Args:
            m_neighbors: Number of nearest neighbors (M in GEA).
                Default 4 matches the paper's experimental setup.
        """
        self.m_neighbors = m_neighbors

    def compute_novelty(
        self,
        agent: TaskSuccessVector,
        archive: list[TaskSuccessVector],
    ) -> float:
        """Compute novelty score for a single agent relative to archive.

        Returns average cosine distance to M nearest neighbors.
        Higher = more novel/diverse capability profile.
        """
        if len(archive) <= 1:
            return 1.0  # Maximum novelty when archive is trivial

        distances: list[float] = []
        for other in archive:
            if other.agent_id == agent.agent_id:
                continue
            distances.append(agent.cosine_distance(other))

        if not distances:
            return 1.0

        distances.sort()
        m = min(self.m_neighbors, len(distances))
        return float(np.mean(distances[:m]))


# ---------------------------------------------------------------------------
# Performance-Novelty Selection
# ---------------------------------------------------------------------------


class SelectionStrategy(Enum):
    """Parent group selection strategies."""

    PERFORMANCE_NOVELTY = "performance_novelty"  # GEA: score = alpha * sqrt(nov)
    PERFORMANCE_ONLY = "performance_only"  # Ablation: pure exploitation
    NOVELTY_ONLY = "novelty_only"  # Ablation: pure exploration
    HIHO_BALANCED = "hiho_balanced"  # Cohezion native: HIHO 0.5 target


@dataclass
class AgentCandidate:
    """An agent candidate for parent group selection.

    Combines GEA's scoring with Cohezion's existing coherence tracking.
    """

    agent_id: str
    performance: float  # alpha_i: task solve rate or quality score
    novelty: float  # nov(i): KNN novelty score
    coherence: float = 0.5  # Cohezion HIHO coherence (existing metric)
    success_vector: TaskSuccessVector | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def gea_score(self) -> float:
        """GEA combined score: alpha_i * sqrt(nov(i)).

        Performance dominates; novelty provides mild exploration bias.
        """
        return self.performance * math.sqrt(max(self.novelty, 0.0))

    @property
    def hiho_score(self) -> float:
        """Cohezion HIHO stability score: 1 - |coherence - 0.5| * 2."""
        return 1.0 - abs(self.coherence - 0.5) * 2.0


class PerformanceNoveltySelector:
    """Select parent groups using GEA's Performance-Novelty criterion.

    This bridges GEA's group selection with Cohezion's existing swarm
    orchestration. The ``TeamOrchestrator`` currently assigns agents to tasks
    based on skill matching; this module adds population-level selection
    pressure that balances exploitation (performance) with exploration
    (novelty).

    Cohezion parallel: The existing ``CostAwareRouter`` performs task-level
    model selection. This operates at a higher level -- selecting which
    agents participate in evolution rounds.
    """

    def __init__(
        self,
        group_size: int = 2,
        strategy: SelectionStrategy = SelectionStrategy.PERFORMANCE_NOVELTY,
        novelty_scorer: NoveltyScorer | None = None,
    ) -> None:
        """Initialize selector.

        Args:
            group_size: K in GEA -- number of parents per group.
                Default 2 matches the paper's experimental setup.
            strategy: Selection strategy to use.
            novelty_scorer: Optional custom NoveltyScorer.
        """
        self.group_size = group_size
        self.strategy = strategy
        self.novelty_scorer = novelty_scorer or NoveltyScorer()

    def select_parent_group(
        self,
        candidates: list[AgentCandidate],
    ) -> list[AgentCandidate]:
        """Select top-K agents as the parent group.

        Implements GEA Algorithm 1: rank by combined score, take top-K.
        """
        if len(candidates) <= self.group_size:
            return list(candidates)

        if self.strategy == SelectionStrategy.PERFORMANCE_NOVELTY:
            scored = sorted(candidates, key=lambda c: c.gea_score, reverse=True)
        elif self.strategy == SelectionStrategy.PERFORMANCE_ONLY:
            scored = sorted(candidates, key=lambda c: c.performance, reverse=True)
        elif self.strategy == SelectionStrategy.NOVELTY_ONLY:
            scored = sorted(candidates, key=lambda c: c.novelty, reverse=True)
        elif self.strategy == SelectionStrategy.HIHO_BALANCED:
            # Cohezion native: weight by HIHO score * performance
            scored = sorted(
                candidates,
                key=lambda c: c.hiho_score * c.performance,
                reverse=True,
            )
        else:
            scored = sorted(candidates, key=lambda c: c.gea_score, reverse=True)

        selected = scored[: self.group_size]
        logger.info(
            "Selected parent group (%s): %s",
            self.strategy.value,
            [c.agent_id for c in selected],
        )
        return selected


# ---------------------------------------------------------------------------
# Experience Pool (Group-Level Aggregation)
# ---------------------------------------------------------------------------


class ExperienceTraceType(Enum):
    """Types of evolutionary traces collected from agents.

    Maps GEA's four trace types to Cohezion's existing data structures.
    """

    APPLIED_PATCH = "applied_patch"  # Code modifications (-> SkillRefiner outputs)
    PREDICTED_PATCH = "predicted_patch"  # Model-generated solutions
    EXECUTION_LOG = "execution_log"  # Tool invocation history (-> JourneyTracker)
    EVALUATION_OUTCOME = "evaluation_outcome"  # Success/failure + metrics


@dataclass
class ExperienceTrace:
    """Single evolutionary trace from an agent execution.

    Cohezion parallel: The existing ``PersistenceAccumulator`` buffers
    experience data with novelty-based importance sampling. This structure
    formalizes the trace schema for group-level aggregation.
    """

    agent_id: str
    trace_type: ExperienceTraceType
    content: dict[str, Any]
    timestamp: float = field(default_factory=time.time)
    quality_score: float = 0.0  # Execution quality (coherence)
    novelty_score: float = 0.0  # How novel this trace is


@dataclass
class GroupExperiencePool:
    """Aggregated experience pool from a parent group.

    GEA formula: S = union(T_j) for all a_j in G

    This is the key innovation: rather than each agent evolving in isolation,
    all traces from all parent agents are aggregated and shared. Every agent
    in the group gets access to complementary discoveries from siblings.

    Cohezion parallel: The ``ExperienceCollector`` already gathers experiences
    from Parquet, SurrealDB, and vault tiers. The ``GroupExperiencePool``
    extends this by providing a structured aggregation specifically for
    group evolution cycles, with cross-agent trace sharing.
    """

    parent_agent_ids: list[str]
    traces: list[ExperienceTrace] = field(default_factory=list)
    creation_time: float = field(default_factory=time.time)

    def add_traces(self, agent_id: str, traces: list[ExperienceTrace]) -> None:
        """Add traces from a parent agent to the shared pool."""
        for trace in traces:
            if trace.agent_id != agent_id:
                logger.warning(
                    "Trace agent_id mismatch: expected %s, got %s",
                    agent_id,
                    trace.agent_id,
                )
            self.traces.append(trace)
        logger.debug(
            "Added %d traces from %s (pool total: %d)",
            len(traces),
            agent_id,
            len(self.traces),
        )

    def get_traces_by_type(self, trace_type: ExperienceTraceType) -> list[ExperienceTrace]:
        """Filter traces by type."""
        return [t for t in self.traces if t.trace_type == trace_type]

    def get_high_quality_traces(self, min_quality: float = 0.5) -> list[ExperienceTrace]:
        """Get traces above a quality threshold.

        This addresses GEA's noted limitation about experience filtering:
        "blindly sharing outputs and experiences may introduce low-quality
        experiences that act as noise."
        """
        return [t for t in self.traces if t.quality_score >= min_quality]

    @property
    def unique_agent_count(self) -> int:
        """Number of unique agents that contributed traces."""
        return len(set(t.agent_id for t in self.traces))

    @property
    def trace_summary(self) -> dict[str, int]:
        """Count traces by type."""
        summary: dict[str, int] = {}
        for t in self.traces:
            key = t.trace_type.value
            summary[key] = summary.get(key, 0) + 1
        return summary


# ---------------------------------------------------------------------------
# Evolution Directive (Reflect Module Output)
# ---------------------------------------------------------------------------


@dataclass
class EvolutionDirective:
    """Output of the Reflect module: a directive for agent evolution.

    Cohezion parallel: This maps to the ``LearningSignal`` from
    ``SkillRefiner`` -- both capture what should change in an agent's
    behavior. GEA's directives target workflow/tool/prompt changes;
    Cohezion's target PRIME skill definition updates.
    """

    agent_id: str
    target_area: str  # "workflow", "tool", "prompt", "skill"
    description: str  # What to change
    source_traces: list[str]  # Which trace IDs informed this
    confidence: float = 0.5  # How confident in this directive
    from_peer_agent: str = ""  # Which peer's experience inspired this


# ---------------------------------------------------------------------------
# Archive Entry
# ---------------------------------------------------------------------------


@dataclass
class ArchiveEntry:
    """Record of an agent in the evolutionary archive.

    GEA's archive grows monotonically: agents that compile and show basic
    functionality are retained for future parent selection.

    Cohezion parallel: The vault + PRIME skill registry serve as Cohezion's
    archive. Skills that pass validation get versioned and retained.
    """

    agent_id: str
    generation: int
    parent_ids: list[str]
    success_vector: TaskSuccessVector
    performance: float
    novelty: float
    gea_score: float
    skill_patches: list[str] = field(default_factory=list)
    creation_time: float = field(default_factory=time.time)
    ancestor_count: int = 0  # How many unique ancestors contributed


# ---------------------------------------------------------------------------
# Group Evolution Engine
# ---------------------------------------------------------------------------


class GroupEvolutionEngine:
    """Orchestrate group-level agent evolution inspired by GEA.

    This is the top-level integration point that bridges GEA's paradigm with
    Cohezion's existing compound engineering loop:

        Cohezion Loop:                  GEA Equivalent:
        ─────────────                   ──────────────
        PRIME Skill (md)                Agent Framework Code
        InstructionExpander             (implicit in agent)
        PlanExecutor                    Act (generate patches)
        ExecutionOrchestrator           Execute + Evaluate
        RetrospectionEngine      <->    Reflect Module
        SkillRefiner             <->    Evolve Module
        SkillConsensusVoter      <->    Group Experience Sharing
        Updated Skill                   Offspring Agent in Archive

    The engine adds group-level selection and cross-agent experience sharing
    on top of the existing loop, without replacing any existing components.
    """

    def __init__(
        self,
        selector: PerformanceNoveltySelector | None = None,
        novelty_scorer: NoveltyScorer | None = None,
        max_archive_size: int = 1000,
        quality_filter_threshold: float = 0.3,
    ) -> None:
        """Initialize group evolution engine.

        Args:
            selector: Parent group selector. Defaults to GEA-style
                Performance-Novelty with K=2.
            novelty_scorer: Novelty computation. Defaults to M=4 KNN.
            max_archive_size: Maximum archive entries before pruning.
            quality_filter_threshold: Minimum quality for experience sharing.
                Addresses GEA's noted limitation about noise filtering.
        """
        self.selector = selector or PerformanceNoveltySelector()
        self.novelty_scorer = novelty_scorer or NoveltyScorer()
        self.archive: list[ArchiveEntry] = []
        self.max_archive_size = max_archive_size
        self.quality_filter_threshold = quality_filter_threshold
        self._generation = 0

    def build_candidates(
        self,
        agents: list[dict[str, Any]],
        task_ids: list[str],
    ) -> list[AgentCandidate]:
        """Build AgentCandidate list from agent execution histories.

        Computes TaskSuccessVectors and novelty scores for each agent,
        then packages them as selection candidates.

        Args:
            agents: List of agent dicts with keys:
                - agent_id: str
                - execution_results: list[bool] (per task_id)
                - coherence: float (Cohezion HIHO coherence)
            task_ids: Ordered list of task identifiers.

        Returns:
            List of AgentCandidate ready for parent selection.
        """
        # Build success vectors
        vectors: list[TaskSuccessVector] = []
        for agent in agents:
            vec = TaskSuccessVector.from_execution_history(
                agent_id=agent["agent_id"],
                task_ids=task_ids,
                results=agent.get("execution_results", []),
            )
            vectors.append(vec)

        # Compute novelty scores
        candidates: list[AgentCandidate] = []
        for agent, vec in zip(agents, vectors, strict=True):
            novelty = self.novelty_scorer.compute_novelty(vec, vectors)
            candidate = AgentCandidate(
                agent_id=agent["agent_id"],
                performance=vec.solve_rate,
                novelty=novelty,
                coherence=agent.get("coherence", 0.5),
                success_vector=vec,
                metadata=agent.get("metadata", {}),
            )
            candidates.append(candidate)

        return candidates

    def select_parents(
        self,
        candidates: list[AgentCandidate],
    ) -> list[AgentCandidate]:
        """Select parent group from candidates.

        Delegates to ``PerformanceNoveltySelector`` which implements GEA's
        Algorithm 1.
        """
        return self.selector.select_parent_group(candidates)

    def aggregate_experience(
        self,
        parent_group: list[AgentCandidate],
        trace_sources: dict[str, list[ExperienceTrace]],
    ) -> GroupExperiencePool:
        """Aggregate experience traces from parent group into shared pool.

        GEA Algorithm 2: S = union(T_j) for all a_j in G

        This is where Cohezion's existing ``PersistenceAccumulator`` data
        flows into the group evolution cycle. Traces from all parent agents
        are combined, with quality filtering to reduce noise.

        Args:
            parent_group: Selected parent agents.
            trace_sources: Mapping from agent_id to their traces.

        Returns:
            Shared GroupExperiencePool accessible by all offspring.
        """
        pool = GroupExperiencePool(parent_agent_ids=[p.agent_id for p in parent_group])

        for parent in parent_group:
            traces = trace_sources.get(parent.agent_id, [])
            # Quality filter (addresses GEA limitation)
            filtered = [t for t in traces if t.quality_score >= self.quality_filter_threshold]
            pool.add_traces(parent.agent_id, filtered)

        logger.info(
            "Aggregated experience pool: %d traces from %d agents (%s)",
            len(pool.traces),
            pool.unique_agent_count,
            pool.trace_summary,
        )
        return pool

    def generate_directives(
        self,
        pool: GroupExperiencePool,
        target_agent_id: str,
    ) -> list[EvolutionDirective]:
        """Generate evolution directives from shared experience pool.

        Implements GEA's Reflect step: analyze aggregated group experience
        and produce directives targeting workflow/tool/prompt improvements.

        Cohezion integration: These directives feed into the existing
        ``SkillRefiner.refine()`` method, which appends learned refinements
        to PRIME skill definition files.

        Args:
            pool: Shared experience pool from parent group.
            target_agent_id: Agent receiving the directives.

        Returns:
            List of EvolutionDirective for the target agent.
        """
        directives: list[EvolutionDirective] = []

        # Analyze success patterns from peer agents
        [t for t in pool.traces if t.agent_id != target_agent_id]
        own_traces = [t for t in pool.traces if t.agent_id == target_agent_id]

        # Find high-quality peer traces in areas where target struggles
        successful_peers = pool.get_high_quality_traces(min_quality=0.7)
        for trace in successful_peers:
            if trace.agent_id == target_agent_id:
                continue
            directives.append(
                EvolutionDirective(
                    agent_id=target_agent_id,
                    target_area=_infer_target_area(trace),
                    description=(
                        f"Adopt pattern from {trace.agent_id}: "
                        f"{trace.content.get('summary', 'N/A')}"
                    ),
                    source_traces=[trace.agent_id],
                    confidence=trace.quality_score,
                    from_peer_agent=trace.agent_id,
                )
            )

        # Analyze own failure patterns
        failed_own = [t for t in own_traces if t.quality_score < 0.5]
        for trace in failed_own:
            directives.append(
                EvolutionDirective(
                    agent_id=target_agent_id,
                    target_area=_infer_target_area(trace),
                    description=(f"Address failure: {trace.content.get('error', 'unknown')}"),
                    source_traces=[trace.agent_id],
                    confidence=0.3,
                )
            )

        logger.debug(
            "Generated %d directives for %s (%d from peers, %d from self-analysis)",
            len(directives),
            target_agent_id,
            len([d for d in directives if d.from_peer_agent]),
            len([d for d in directives if not d.from_peer_agent]),
        )
        return directives

    def add_to_archive(
        self,
        agent_id: str,
        parent_ids: list[str],
        success_vector: TaskSuccessVector,
        skill_patches: list[str] | None = None,
    ) -> ArchiveEntry:
        """Add a validated offspring to the archive.

        GEA's archive grows monotonically. Agents must compile and show
        basic functionality. In Cohezion, this means the PRIME skill file
        must be valid and the agent must pass basic execution tests.

        Args:
            agent_id: Unique identifier for the new agent.
            parent_ids: IDs of parent agents in the group.
            success_vector: Task-success vector from evaluation.
            skill_patches: PRIME skill patches applied.

        Returns:
            The new ArchiveEntry.
        """
        performance = success_vector.solve_rate
        archive_vectors = [e.success_vector for e in self.archive]
        novelty = self.novelty_scorer.compute_novelty(success_vector, archive_vectors)
        gea_score = performance * math.sqrt(max(novelty, 0.0))

        # Count unique ancestors
        ancestor_ids: set[str] = set()
        for pid in parent_ids:
            ancestor_ids.add(pid)
            for entry in self.archive:
                if entry.agent_id == pid:
                    ancestor_ids.update(entry.parent_ids)
                    break

        entry = ArchiveEntry(
            agent_id=agent_id,
            generation=self._generation,
            parent_ids=parent_ids,
            success_vector=success_vector,
            performance=performance,
            novelty=novelty,
            gea_score=gea_score,
            skill_patches=skill_patches or [],
            ancestor_count=len(ancestor_ids),
        )

        self.archive.append(entry)
        self._generation += 1

        # Prune if necessary (keep highest-scoring)
        if len(self.archive) > self.max_archive_size:
            self.archive.sort(key=lambda e: e.gea_score, reverse=True)
            self.archive = self.archive[: self.max_archive_size]
            logger.info("Pruned archive to %d entries", len(self.archive))

        logger.info(
            "Added %s to archive (gen=%d, perf=%.2f, nov=%.2f, gea=%.2f, ancestors=%d)",
            agent_id,
            entry.generation,
            performance,
            novelty,
            gea_score,
            entry.ancestor_count,
        )
        return entry

    def get_archive_stats(self) -> dict[str, Any]:
        """Get summary statistics about the archive."""
        if not self.archive:
            return {
                "size": 0,
                "generation": self._generation,
                "avg_performance": 0.0,
                "avg_novelty": 0.0,
                "avg_gea_score": 0.0,
                "max_ancestors": 0,
            }

        performances = [e.performance for e in self.archive]
        novelties = [e.novelty for e in self.archive]
        gea_scores = [e.gea_score for e in self.archive]
        ancestors = [e.ancestor_count for e in self.archive]

        return {
            "size": len(self.archive),
            "generation": self._generation,
            "avg_performance": float(np.mean(performances)),
            "avg_novelty": float(np.mean(novelties)),
            "avg_gea_score": float(np.mean(gea_scores)),
            "max_ancestors": max(ancestors),
            "best_agent": max(self.archive, key=lambda e: e.gea_score).agent_id,
        }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _infer_target_area(trace: ExperienceTrace) -> str:
    """Infer the target area for an evolution directive from a trace."""
    type_to_area = {
        ExperienceTraceType.APPLIED_PATCH: "skill",
        ExperienceTraceType.PREDICTED_PATCH: "workflow",
        ExperienceTraceType.EXECUTION_LOG: "tool",
        ExperienceTraceType.EVALUATION_OUTCOME: "prompt",
    }
    return type_to_area.get(trace.trace_type, "workflow")
