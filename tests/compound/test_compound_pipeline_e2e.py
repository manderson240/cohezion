"""End-to-end tests for the compound engineering pipeline.

Tests the full flow: experiment analytics → recommendations →
health check → session metrics — verifying all components integrate.
"""

import asyncio


class TestCompoundPipelineE2E:
    """End-to-end integration tests for the compound engineering pipeline."""

    def test_analytics_to_recommendations_flow(self, tmp_path):
        """Full flow: load records → analytics → recommendations."""
        import json

        from cohezion.compound.experiment_analytics import (
            compute_experiment_stats,
            compute_hiho_balance,
            find_retirement_candidates,
        )
        from cohezion.compound.experiment_recommender import recommend_next_experiments

        # Setup: simulate experiment history
        jsonl = tmp_path / "test.jsonl"
        records = (
            # E50: constant metric → retirement candidate
            [{"metric": 0.125, "status": "keep", "asi": {"experiment": "E50"}} for _ in range(15)]
            +
            # E63: variable metric → not yet retired
            [
                {"metric": 0.15 if i % 2 else 0.125, "status": "keep", "asi": {"experiment": "E63"}}
                for i in range(15)
            ]
        )
        jsonl.write_text("\n".join(json.dumps(r) for r in records))

        # Analytics
        stats = compute_experiment_stats(records)
        hiho = compute_hiho_balance(records)
        retired = find_retirement_candidates(stats, min_keeps=10)

        assert hiho == 1.0  # All keeps
        assert "E50" in retired  # Constant metric → retired
        assert "E63" not in retired  # Variable metric → not retired

        # Recommendations
        recs = recommend_next_experiments(n=2, jsonl_path=jsonl)
        assert len(recs) == 2
        # At least one recommendation replaces E50
        replaces = [r.get("replaces") for r in recs]
        assert "E50" in replaces

    def test_health_monitor_and_analytics_integration(self):
        """Health monitor and analytics report both show healthy state."""
        from cohezion.compound.experiment_analytics import get_analytics_report
        from cohezion.compound.health_monitor import get_health_report

        health = get_health_report()
        analytics = get_analytics_report(n=100)

        assert health["healthy"] is True
        assert analytics["hiho_balance"] >= 0.0
        assert analytics["n_experiments"] >= 0

    def test_session_metrics_with_recommendations(self):
        """SessionMetricsAggregator + ExperimentRecommender pipeline."""
        from cohezion.compound.session_metrics_aggregator import SessionMetricsAggregator

        agg = SessionMetricsAggregator()
        # Simulate a session with high coherence (exploitation mode)
        for i in range(10):
            agg.record(f"E{63 + (i % 3)}", 0.15, 0.8)

        summary = agg.compute_summary()
        assert summary["hiho_balance"] == 1.0
        assert summary["mode"] == "exploit"

        # Get suggestions
        next_exps = asyncio.run(agg.suggest_next(n=3))
        assert len(next_exps) == 3
        assert all(e["mode"] == "exploit" for e in next_exps)

    def test_error_classifier_in_compound_flow(self):
        """Error classification produces correct categories for all error types."""
        from cohezion.compound.error_classifier import classify_error

        test_cases = [
            (ValueError("bad"), "logic", False),
            (TimeoutError("slow"), "transient", True),
            (MemoryError("OOM"), "resource", True),
            (RuntimeError("oops"), "permanent", False),
            (KeyError("missing"), "logic", False),
        ]

        for exc, expected_cat, expected_retryable in test_cases:
            result = classify_error(exc)
            assert result["error_category"] == expected_cat, (
                f"{type(exc).__name__}: expected {expected_cat}"
            )
            assert result["retryable"] == expected_retryable


class TestCompoundAnalyticsPipelineE2E:
    """Full compound analytics pipeline: analytics → schedule → visualize."""

    def test_full_analytics_pipeline(self):
        """End-to-end: load data → stats → retire → recommend → visualize."""
        import json
        import tempfile
        from pathlib import Path

        from cohezion.compound.experiment_analytics import (
            compute_experiment_stats,
            compute_hiho_balance,
            find_retirement_candidates,
            load_experiment_records,
        )
        from cohezion.compound.experiment_recommender import recommend_next_experiments
        from cohezion.compound.loop_visualizer import (
            render_experiment_table,
            render_session_summary,
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            jsonl = Path(tmpdir) / "test.jsonl"
            records = (
                [
                    {"metric": 0.125, "status": "keep", "asi": {"experiment": "E50"}}
                    for _ in range(15)
                ]
                + [
                    {"metric": 0.149, "status": "keep", "asi": {"experiment": "E63"}}
                    for _ in range(15)
                ]
                + [
                    {"metric": 0.0, "status": "discard", "asi": {"experiment": "E99"}}
                    for _ in range(5)
                ]
            )
            jsonl.write_text("\n".join(json.dumps(r) for r in records))

            # Step 1: Analytics
            loaded = load_experiment_records(n=50, jsonl_path=jsonl)
            stats = compute_experiment_stats(loaded)
            hiho = compute_hiho_balance(loaded)
            retired = find_retirement_candidates(stats, min_keeps=10)

            assert hiho > 0.5  # Mostly keeps
            assert "E50" in retired  # Constant → retired
            assert "E99" not in retired  # All discards → not retired

            # Step 2: Recommendations
            recs = recommend_next_experiments(n=2, jsonl_path=jsonl)
            assert len(recs) == 2

            # Step 3: Visualize
            summary = render_session_summary(
                n_experiments=len(loaded),
                hiho_balance=hiho,
                mean_delta=stats.get("E63", {}).get("mean_metric", 0),
                keep_rate=hiho,
                retirement_candidates=retired,
            )
            assert "COMPOUND ENGINEERING" in summary
            assert "EXPLOIT" in summary  # hiho > 0.5

            table = render_experiment_table(stats, retirement_candidates=retired)
            assert "E50" in table
            assert "RETIRE" in table

    def test_compound_engine_full_cycle(self):
        """CompoundEngine integrates all subsystems in one interface."""
        from cohezion.compound.compound_engine import CompoundEngine

        engine = CompoundEngine()

        # Record executions
        for i in range(5):
            engine.record_execution(f"E{63 + i}", 0.15, 0.8)
            engine.record_score(0.75)

        # Get summary
        summary = engine.get_summary()
        assert summary["overall_health"] is True
        assert summary["session"]["n_experiments"] == 5

        # Get next experiments
        exps = engine.get_next_experiments(n=2)
        assert len(exps) == 2

        # Health check
        health = engine.get_health()
        assert health["healthy"] is True
