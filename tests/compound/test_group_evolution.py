"""Tests for Group-Evolving Agents (GEA) integration.

Tests the core GEA concepts integrated into Cohezion's compound engineering:
- TaskSuccessVector and cosine distance
- KNN NoveltyScorer
- PerformanceNoveltySelector (parent group selection)
- GroupExperiencePool (cross-agent experience aggregation)
- GroupEvolutionEngine (end-to-end evolution cycle)
"""

import pytest

from cohezion.compound.group_evolution import (
    AgentCandidate,
    EvolutionDirective,
    ExperienceTrace,
    ExperienceTraceType,
    GroupEvolutionEngine,
    GroupExperiencePool,
    NoveltyScorer,
    PerformanceNoveltySelector,
    SelectionStrategy,
    TaskSuccessVector,
)


# ---------------------------------------------------------------------------
# TaskSuccessVector tests
# ---------------------------------------------------------------------------


class TestTaskSuccessVector:
    """Test task-success vector representation and cosine distance."""

    def test_from_execution_history(self):
        """Build vector from execution results."""
        vec = TaskSuccessVector.from_execution_history(
            agent_id="agent-1",
            task_ids=["t1", "t2", "t3", "t4"],
            results=[True, False, True, True],
        )
        assert vec.agent_id == "agent-1"
        assert len(vec.task_ids) == 4
        assert vec.successes[0] == 1.0
        assert vec.successes[1] == 0.0

    def test_solve_rate(self):
        """Solve rate is fraction of tasks solved."""
        vec = TaskSuccessVector.from_execution_history(
            agent_id="a",
            task_ids=["t1", "t2", "t3", "t4"],
            results=[True, False, True, True],
        )
        assert vec.solve_rate == pytest.approx(0.75)

    def test_solve_rate_empty(self):
        """Empty vector has zero solve rate."""
        vec = TaskSuccessVector.from_execution_history(
            agent_id="a",
            task_ids=[],
            results=[],
        )
        assert vec.solve_rate == 0.0

    def test_cosine_distance_identical(self):
        """Identical vectors have zero distance."""
        vec_a = TaskSuccessVector.from_execution_history(
            agent_id="a",
            task_ids=["t1", "t2", "t3"],
            results=[True, True, False],
        )
        vec_b = TaskSuccessVector.from_execution_history(
            agent_id="b",
            task_ids=["t1", "t2", "t3"],
            results=[True, True, False],
        )
        dist = vec_a.cosine_distance(vec_b)
        assert dist == pytest.approx(0.0, abs=1e-6)

    def test_cosine_distance_orthogonal(self):
        """Orthogonal vectors have distance 1.0."""
        vec_a = TaskSuccessVector.from_execution_history(
            agent_id="a",
            task_ids=["t1", "t2", "t3", "t4"],
            results=[True, True, False, False],
        )
        vec_b = TaskSuccessVector.from_execution_history(
            agent_id="b",
            task_ids=["t1", "t2", "t3", "t4"],
            results=[False, False, True, True],
        )
        dist = vec_a.cosine_distance(vec_b)
        assert dist == pytest.approx(1.0, abs=1e-6)

    def test_cosine_distance_symmetry(self):
        """Cosine distance is symmetric: d(a,b) == d(b,a)."""
        vec_a = TaskSuccessVector.from_execution_history(
            agent_id="a",
            task_ids=["t1", "t2", "t3"],
            results=[True, False, True],
        )
        vec_b = TaskSuccessVector.from_execution_history(
            agent_id="b",
            task_ids=["t1", "t2", "t3"],
            results=[True, True, False],
        )
        assert vec_a.cosine_distance(vec_b) == pytest.approx(
            vec_b.cosine_distance(vec_a), abs=1e-10
        )

    def test_cosine_distance_range(self):
        """Cosine distance is in [0, 1] for non-negative vectors."""
        vec_a = TaskSuccessVector.from_execution_history(
            agent_id="a",
            task_ids=["t1", "t2", "t3"],
            results=[True, False, True],
        )
        vec_b = TaskSuccessVector.from_execution_history(
            agent_id="b",
            task_ids=["t1", "t2", "t3"],
            results=[False, True, True],
        )
        dist = vec_a.cosine_distance(vec_b)
        assert 0.0 <= dist <= 1.0


# ---------------------------------------------------------------------------
# NoveltyScorer tests
# ---------------------------------------------------------------------------


class TestNoveltyScorer:
    """Test KNN novelty scoring."""

    def test_single_agent_max_novelty(self):
        """Single agent in archive has maximum novelty."""
        scorer = NoveltyScorer(m_neighbors=4)
        agent = TaskSuccessVector.from_execution_history(
            agent_id="a",
            task_ids=["t1"],
            results=[True],
        )
        novelty = scorer.compute_novelty(agent, [agent])
        assert novelty == 1.0

    def test_identical_agents_zero_novelty(self):
        """Agents with identical capability profiles have low novelty."""
        scorer = NoveltyScorer(m_neighbors=2)
        agents = [
            TaskSuccessVector.from_execution_history(
                agent_id=f"a{i}",
                task_ids=["t1", "t2", "t3"],
                results=[True, True, False],
            )
            for i in range(5)
        ]
        novelty = scorer.compute_novelty(agents[0], agents)
        assert novelty == pytest.approx(0.0, abs=1e-6)

    def test_diverse_agents_high_novelty(self):
        """Agents with diverse profiles have higher novelty."""
        scorer = NoveltyScorer(m_neighbors=2)
        agents = [
            TaskSuccessVector.from_execution_history(
                agent_id="a0",
                task_ids=["t1", "t2", "t3", "t4"],
                results=[True, True, False, False],
            ),
            TaskSuccessVector.from_execution_history(
                agent_id="a1",
                task_ids=["t1", "t2", "t3", "t4"],
                results=[False, False, True, True],
            ),
            TaskSuccessVector.from_execution_history(
                agent_id="a2",
                task_ids=["t1", "t2", "t3", "t4"],
                results=[True, False, True, False],
            ),
        ]
        # a0 is orthogonal to a1 -> high novelty
        novelty_a0 = scorer.compute_novelty(agents[0], agents)
        assert novelty_a0 > 0.3

    def test_m_neighbors_clamp(self):
        """M is clamped to available neighbors."""
        scorer = NoveltyScorer(m_neighbors=10)
        agents = [
            TaskSuccessVector.from_execution_history(
                agent_id=f"a{i}",
                task_ids=["t1", "t2"],
                results=[i % 2 == 0, i % 2 != 0],
            )
            for i in range(3)
        ]
        # Should not crash even though M > number of others
        novelty = scorer.compute_novelty(agents[0], agents)
        assert isinstance(novelty, float)


# ---------------------------------------------------------------------------
# PerformanceNoveltySelector tests
# ---------------------------------------------------------------------------


class TestPerformanceNoveltySelector:
    """Test parent group selection with Performance-Novelty criterion."""

    @pytest.fixture
    def candidates(self):
        """Create sample candidates."""
        return [
            AgentCandidate(
                agent_id="high-perf",
                performance=0.9,
                novelty=0.3,
                coherence=0.5,
            ),
            AgentCandidate(
                agent_id="high-novel",
                performance=0.5,
                novelty=0.9,
                coherence=0.5,
            ),
            AgentCandidate(
                agent_id="balanced",
                performance=0.7,
                novelty=0.7,
                coherence=0.5,
            ),
            AgentCandidate(
                agent_id="low",
                performance=0.3,
                novelty=0.2,
                coherence=0.5,
            ),
        ]

    def test_gea_score_formula(self):
        """GEA score = alpha * sqrt(novelty)."""
        c = AgentCandidate(agent_id="x", performance=0.8, novelty=0.64)
        # 0.8 * sqrt(0.64) = 0.8 * 0.8 = 0.64
        assert c.gea_score == pytest.approx(0.64)

    def test_hiho_score_formula(self):
        """HIHO score = 1 - |coherence - 0.5| * 2."""
        c = AgentCandidate(agent_id="x", performance=1.0, novelty=1.0, coherence=0.5)
        assert c.hiho_score == pytest.approx(1.0)

        c2 = AgentCandidate(agent_id="x", performance=1.0, novelty=1.0, coherence=0.0)
        assert c2.hiho_score == pytest.approx(0.0)

    def test_select_top_k(self, candidates):
        """Select top-K by GEA score."""
        selector = PerformanceNoveltySelector(group_size=2)
        parents = selector.select_parent_group(candidates)
        assert len(parents) == 2
        # Both top candidates should have good combined scores
        assert all(p.gea_score > 0.1 for p in parents)

    def test_performance_only_strategy(self, candidates):
        """Performance-only selects highest performers."""
        selector = PerformanceNoveltySelector(
            group_size=2, strategy=SelectionStrategy.PERFORMANCE_ONLY
        )
        parents = selector.select_parent_group(candidates)
        assert parents[0].agent_id == "high-perf"

    def test_novelty_only_strategy(self, candidates):
        """Novelty-only selects most novel agents."""
        selector = PerformanceNoveltySelector(group_size=2, strategy=SelectionStrategy.NOVELTY_ONLY)
        parents = selector.select_parent_group(candidates)
        assert parents[0].agent_id == "high-novel"

    def test_hiho_balanced_strategy(self, candidates):
        """HIHO balanced weights by HIHO score * performance."""
        selector = PerformanceNoveltySelector(
            group_size=2, strategy=SelectionStrategy.HIHO_BALANCED
        )
        parents = selector.select_parent_group(candidates)
        assert len(parents) == 2

    def test_small_candidate_pool(self):
        """When candidates <= group_size, return all."""
        selector = PerformanceNoveltySelector(group_size=3)
        candidates = [
            AgentCandidate(agent_id="a", performance=0.5, novelty=0.5),
        ]
        parents = selector.select_parent_group(candidates)
        assert len(parents) == 1


# ---------------------------------------------------------------------------
# GroupExperiencePool tests
# ---------------------------------------------------------------------------


class TestGroupExperiencePool:
    """Test cross-agent experience aggregation."""

    @pytest.fixture
    def traces(self):
        """Create sample traces from two agents."""
        return {
            "agent-1": [
                ExperienceTrace(
                    agent_id="agent-1",
                    trace_type=ExperienceTraceType.APPLIED_PATCH,
                    content={"summary": "Improved error handling"},
                    quality_score=0.8,
                ),
                ExperienceTrace(
                    agent_id="agent-1",
                    trace_type=ExperienceTraceType.EXECUTION_LOG,
                    content={"tools": ["grep", "edit"]},
                    quality_score=0.6,
                ),
            ],
            "agent-2": [
                ExperienceTrace(
                    agent_id="agent-2",
                    trace_type=ExperienceTraceType.EVALUATION_OUTCOME,
                    content={"summary": "Passed all tests"},
                    quality_score=0.9,
                ),
                ExperienceTrace(
                    agent_id="agent-2",
                    trace_type=ExperienceTraceType.PREDICTED_PATCH,
                    content={"summary": "Add caching"},
                    quality_score=0.2,  # Low quality
                ),
            ],
        }

    def test_pool_aggregation(self, traces):
        """Pool aggregates traces from multiple agents."""
        pool = GroupExperiencePool(parent_agent_ids=["agent-1", "agent-2"])
        pool.add_traces("agent-1", traces["agent-1"])
        pool.add_traces("agent-2", traces["agent-2"])

        assert len(pool.traces) == 4
        assert pool.unique_agent_count == 2

    def test_trace_summary(self, traces):
        """Trace summary counts by type."""
        pool = GroupExperiencePool(parent_agent_ids=["agent-1", "agent-2"])
        pool.add_traces("agent-1", traces["agent-1"])
        pool.add_traces("agent-2", traces["agent-2"])

        summary = pool.trace_summary
        assert summary["applied_patch"] == 1
        assert summary["execution_log"] == 1
        assert summary["evaluation_outcome"] == 1
        assert summary["predicted_patch"] == 1

    def test_quality_filter(self, traces):
        """High-quality filter excludes low-quality traces."""
        pool = GroupExperiencePool(parent_agent_ids=["agent-1", "agent-2"])
        pool.add_traces("agent-1", traces["agent-1"])
        pool.add_traces("agent-2", traces["agent-2"])

        high_quality = pool.get_high_quality_traces(min_quality=0.5)
        assert len(high_quality) == 3  # Excludes the 0.2 quality trace

    def test_filter_by_type(self, traces):
        """Filter traces by type."""
        pool = GroupExperiencePool(parent_agent_ids=["agent-1", "agent-2"])
        pool.add_traces("agent-1", traces["agent-1"])
        pool.add_traces("agent-2", traces["agent-2"])

        patches = pool.get_traces_by_type(ExperienceTraceType.APPLIED_PATCH)
        assert len(patches) == 1
        assert patches[0].agent_id == "agent-1"


# ---------------------------------------------------------------------------
# GroupEvolutionEngine tests
# ---------------------------------------------------------------------------


class TestGroupEvolutionEngine:
    """Test end-to-end group evolution."""

    @pytest.fixture
    def engine(self):
        """Create engine with default settings."""
        return GroupEvolutionEngine(
            selector=PerformanceNoveltySelector(group_size=2),
            novelty_scorer=NoveltyScorer(m_neighbors=2),
            quality_filter_threshold=0.3,
        )

    @pytest.fixture
    def agents(self):
        """Create sample agents with execution histories."""
        return [
            {
                "agent_id": "agent-1",
                "execution_results": [True, True, False, True, False],
                "coherence": 0.5,
            },
            {
                "agent_id": "agent-2",
                "execution_results": [False, True, True, True, True],
                "coherence": 0.45,
            },
            {
                "agent_id": "agent-3",
                "execution_results": [True, False, True, False, True],
                "coherence": 0.55,
            },
        ]

    @pytest.fixture
    def task_ids(self):
        """Task IDs corresponding to execution results."""
        return ["task-1", "task-2", "task-3", "task-4", "task-5"]

    def test_build_candidates(self, engine, agents, task_ids):
        """Build candidates with success vectors and novelty scores."""
        candidates = engine.build_candidates(agents, task_ids)
        assert len(candidates) == 3
        for c in candidates:
            assert isinstance(c.performance, float)
            assert isinstance(c.novelty, float)
            assert c.success_vector is not None

    def test_select_parents(self, engine, agents, task_ids):
        """Select parent group from candidates."""
        candidates = engine.build_candidates(agents, task_ids)
        parents = engine.select_parents(candidates)
        assert len(parents) == 2

    def test_aggregate_experience(self, engine):
        """Aggregate experience with quality filtering."""
        parents = [
            AgentCandidate(agent_id="a1", performance=0.8, novelty=0.5),
            AgentCandidate(agent_id="a2", performance=0.7, novelty=0.6),
        ]
        traces = {
            "a1": [
                ExperienceTrace(
                    agent_id="a1",
                    trace_type=ExperienceTraceType.APPLIED_PATCH,
                    content={"summary": "good"},
                    quality_score=0.8,
                ),
                ExperienceTrace(
                    agent_id="a1",
                    trace_type=ExperienceTraceType.EXECUTION_LOG,
                    content={"summary": "bad"},
                    quality_score=0.1,  # Below threshold
                ),
            ],
            "a2": [
                ExperienceTrace(
                    agent_id="a2",
                    trace_type=ExperienceTraceType.EVALUATION_OUTCOME,
                    content={"summary": "passed"},
                    quality_score=0.9,
                ),
            ],
        }

        pool = engine.aggregate_experience(parents, traces)
        # Low-quality trace (0.1) should be filtered out (threshold 0.3)
        assert len(pool.traces) == 2
        assert pool.unique_agent_count == 2

    def test_generate_directives(self, engine):
        """Generate evolution directives from shared pool."""
        pool = GroupExperiencePool(parent_agent_ids=["a1", "a2"])
        pool.add_traces(
            "a1",
            [
                ExperienceTrace(
                    agent_id="a1",
                    trace_type=ExperienceTraceType.APPLIED_PATCH,
                    content={"summary": "Added retry logic"},
                    quality_score=0.9,
                ),
            ],
        )
        pool.add_traces(
            "a2",
            [
                ExperienceTrace(
                    agent_id="a2",
                    trace_type=ExperienceTraceType.EXECUTION_LOG,
                    content={"error": "timeout", "summary": "Slow response"},
                    quality_score=0.3,
                ),
            ],
        )

        directives = engine.generate_directives(pool, target_agent_id="a2")
        assert len(directives) > 0
        assert all(isinstance(d, EvolutionDirective) for d in directives)
        # Should have a directive from peer a1's high-quality trace
        peer_directives = [d for d in directives if d.from_peer_agent == "a1"]
        assert len(peer_directives) >= 1

    def test_add_to_archive(self, engine):
        """Add validated offspring to archive."""
        vec = TaskSuccessVector.from_execution_history(
            agent_id="offspring-1",
            task_ids=["t1", "t2", "t3"],
            results=[True, True, False],
        )
        entry = engine.add_to_archive(
            agent_id="offspring-1",
            parent_ids=["parent-a", "parent-b"],
            success_vector=vec,
            skill_patches=["patch_1.md"],
        )

        assert entry.agent_id == "offspring-1"
        assert entry.generation == 0
        assert len(entry.parent_ids) == 2
        assert entry.performance == pytest.approx(2 / 3)
        assert len(engine.archive) == 1

    def test_archive_monotonic_growth(self, engine):
        """Archive grows with each generation."""
        for i in range(5):
            vec = TaskSuccessVector.from_execution_history(
                agent_id=f"agent-{i}",
                task_ids=["t1", "t2"],
                results=[i % 2 == 0, i % 3 == 0],
            )
            engine.add_to_archive(
                agent_id=f"agent-{i}",
                parent_ids=[f"parent-{i}"],
                success_vector=vec,
            )

        assert len(engine.archive) == 5
        assert engine._generation == 5

    def test_archive_pruning(self):
        """Archive prunes to max size when exceeded."""
        engine = GroupEvolutionEngine(max_archive_size=3)
        for i in range(5):
            vec = TaskSuccessVector.from_execution_history(
                agent_id=f"agent-{i}",
                task_ids=["t1", "t2", "t3"],
                results=[True] * (i + 1) + [False] * (2 - i) if i < 3 else [True, True, True],
            )
            engine.add_to_archive(
                agent_id=f"agent-{i}",
                parent_ids=[],
                success_vector=vec,
            )

        assert len(engine.archive) <= 3

    def test_archive_stats(self, engine, agents, task_ids):
        """Get archive summary statistics."""
        # Empty archive
        stats = engine.get_archive_stats()
        assert stats["size"] == 0

        # Add some entries
        candidates = engine.build_candidates(agents, task_ids)
        for c in candidates:
            engine.add_to_archive(
                agent_id=c.agent_id,
                parent_ids=[],
                success_vector=c.success_vector,
            )

        stats = engine.get_archive_stats()
        assert stats["size"] == 3
        assert "avg_performance" in stats
        assert "best_agent" in stats

    def test_ancestor_tracking(self, engine):
        """Track unique ancestor count across generations."""
        # Generation 0: two parents
        for pid in ["p1", "p2"]:
            vec = TaskSuccessVector.from_execution_history(
                agent_id=pid,
                task_ids=["t1", "t2"],
                results=[True, True],
            )
            engine.add_to_archive(
                agent_id=pid,
                parent_ids=[],
                success_vector=vec,
            )

        # Generation 1: offspring of p1 and p2
        vec = TaskSuccessVector.from_execution_history(
            agent_id="child-1",
            task_ids=["t1", "t2"],
            results=[True, True],
        )
        entry = engine.add_to_archive(
            agent_id="child-1",
            parent_ids=["p1", "p2"],
            success_vector=vec,
        )
        assert entry.ancestor_count == 2  # p1 and p2


class TestEndToEndEvolution:
    """Test a complete evolution cycle matching GEA's Algorithm 2."""

    def test_full_evolution_cycle(self):
        """Run one complete evolution iteration."""
        engine = GroupEvolutionEngine(
            selector=PerformanceNoveltySelector(group_size=2),
        )

        # 1. Build initial population
        task_ids = [f"task-{i}" for i in range(10)]
        agents = [
            {
                "agent_id": f"agent-{i}",
                "execution_results": [(i + j) % 3 != 0 for j in range(10)],
                "coherence": 0.5,
            }
            for i in range(4)
        ]

        # 2. Build candidates
        candidates = engine.build_candidates(agents, task_ids)
        assert len(candidates) == 4

        # 3. Select parent group (GEA Algorithm 1)
        parents = engine.select_parents(candidates)
        assert len(parents) == 2

        # 4. Collect traces from parents
        trace_sources = {}
        for parent in parents:
            trace_sources[parent.agent_id] = [
                ExperienceTrace(
                    agent_id=parent.agent_id,
                    trace_type=ExperienceTraceType.APPLIED_PATCH,
                    content={"summary": f"Patch from {parent.agent_id}"},
                    quality_score=parent.performance,
                ),
                ExperienceTrace(
                    agent_id=parent.agent_id,
                    trace_type=ExperienceTraceType.EXECUTION_LOG,
                    content={"tools": ["tool1", "tool2"]},
                    quality_score=0.5,
                ),
            ]

        # 5. Aggregate experience (GEA Algorithm 2: S = union(T_j))
        pool = engine.aggregate_experience(parents, trace_sources)
        assert pool.unique_agent_count == 2

        # 6. Generate directives for each parent (Reflect step)
        all_directives = {}
        for parent in parents:
            directives = engine.generate_directives(pool, parent.agent_id)
            all_directives[parent.agent_id] = directives
            assert isinstance(directives, list)

        # 7. Simulate offspring evaluation and archive
        for i, parent in enumerate(parents):
            offspring_id = f"offspring-{i}"
            # Offspring might solve different tasks than parent
            offspring_results = [
                not r if j % 4 == 0 else r for j, r in enumerate(agents[i]["execution_results"])
            ]
            vec = TaskSuccessVector.from_execution_history(
                agent_id=offspring_id,
                task_ids=task_ids,
                results=offspring_results,
            )
            entry = engine.add_to_archive(
                agent_id=offspring_id,
                parent_ids=[parent.agent_id],
                success_vector=vec,
            )
            assert entry.generation >= 0

        # 8. Verify archive state
        stats = engine.get_archive_stats()
        assert stats["size"] == 2
        assert stats["avg_performance"] > 0
