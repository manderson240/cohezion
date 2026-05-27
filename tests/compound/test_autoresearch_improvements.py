"""Tests for AutoresearchEngine improvements: dedup + generate_next_experiments."""

import asyncio

from cohezion.compound.autoresearch import AutoresearchEngine, ImprovementOpportunity


class TestAutoResearchDeduplication:
    """Verify duplicate pattern logging is suppressed within a session."""

    def test_log_opportunity_deduplicates_same_content(self):
        engine = AutoresearchEngine()
        opp = ImprovementOpportunity(
            category="cache",
            priority=9,
            current_value=0.5,
            target_value=0.8,
            potential_impact="60% reduction",
            implementation_effort="low",
            recommendation="Increase cache size",
        )
        h = engine._opportunity_hash(opp)
        assert h not in engine._logged_opportunity_hashes

        engine._mark_logged(opp)
        assert h in engine._logged_opportunity_hashes

        # Second mark should be a no-op (no exception)
        engine._mark_logged(opp)
        assert len(engine._logged_opportunity_hashes) == 1

    def test_is_duplicate(self):
        engine = AutoresearchEngine()
        opp = ImprovementOpportunity(
            category="token_efficiency",
            priority=8,
            current_value=6000,
            target_value=5000,
            potential_impact="12x efficiency",
            implementation_effort="low",
            recommendation="Enable LOCAL_OFFLOAD",
        )
        assert not engine._is_duplicate(opp)
        engine._mark_logged(opp)
        assert engine._is_duplicate(opp)

    def test_different_opportunities_not_duplicate(self):
        engine = AutoresearchEngine()
        opp1 = ImprovementOpportunity(
            category="cache",
            priority=9,
            current_value=0.5,
            target_value=0.8,
            potential_impact="A",
            implementation_effort="low",
            recommendation="Fix A",
        )
        opp2 = ImprovementOpportunity(
            category="cache",
            priority=9,
            current_value=0.5,
            target_value=0.8,
            potential_impact="A",
            implementation_effort="low",
            recommendation="Fix B",  # different
        )
        engine._mark_logged(opp1)
        assert not engine._is_duplicate(opp2)


class TestGenerateNextExperiments:
    """Verify HIHO-balanced experiment generation."""

    def test_exploit_when_high_coherence(self):
        engine = AutoresearchEngine()
        metrics = {"avg_coherence": 0.8, "avg_tokens_per_request": 3000, "cache_hit_rate": 0.85}
        exps = asyncio.run(engine.generate_next_experiments(n=3, session_metrics=metrics))
        assert len(exps) == 3
        # High coherence → exploit: should tune existing parameters
        modes = [e["mode"] for e in exps]
        assert all(m == "exploit" for m in modes)
        assert all("parameter" in e for e in exps)

    def test_explore_when_low_coherence(self):
        engine = AutoresearchEngine()
        metrics = {"avg_coherence": 0.3, "avg_tokens_per_request": 3000, "cache_hit_rate": 0.5}
        exps = asyncio.run(engine.generate_next_experiments(n=3, session_metrics=metrics))
        assert len(exps) == 3
        modes = [e["mode"] for e in exps]
        assert all(m == "explore" for m in modes)
        assert all("hypothesis" in e for e in exps)

    def test_balanced_at_threshold(self):
        engine = AutoresearchEngine()
        metrics = {"avg_coherence": 0.5}  # exactly at threshold
        exps = asyncio.run(engine.generate_next_experiments(n=4, session_metrics=metrics))
        assert len(exps) == 4
        # At threshold, should produce mix or all exploit (exploit on >=)
        modes = {e["mode"] for e in exps}
        assert modes <= {"exploit", "explore"}

    def test_returns_n_experiments(self):
        engine = AutoresearchEngine()
        for n in [1, 3, 5, 10]:
            exps = asyncio.run(engine.generate_next_experiments(n=n, session_metrics={}))
            assert len(exps) == n, f"Expected {n} experiments, got {len(exps)}"

    def test_retired_label_triggers_replacement(self):
        engine = AutoresearchEngine()
        exps = asyncio.run(
            engine.generate_next_experiments(
                n=2, session_metrics={}, retired_labels=["E63_mycelium", "E12_persist"]
            )
        )
        assert len(exps) == 2
        # Should reference the retired experiments in new proposals
        labels = [e.get("replaces") for e in exps]
        assert any(lbl in ("E63_mycelium", "E12_persist") for lbl in labels)
