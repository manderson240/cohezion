"""Unit tests for the RSI Health Evaluator."""

from cohezion.eval.rsi_health_evaluator import (
    RSIHealthEvaluator,
    RSISnapshot,
)


def test_rsi_health_evaluator_baseline():
    evaluator = RSIHealthEvaluator()
    snap1 = RSISnapshot(
        iteration=1,
        empirical_pass_rate=0.75,
        unseen_generalization_rate=0.60,
        retention_score=0.98,
        invariant_safety_score=1.0,
        total_ast_nodes=1_000_000,
        mean_cyclomatic_complexity=8.5,
    )
    evaluator.record_snapshot(snap1)
    meta = evaluator.evaluate_latest()
    assert meta.current_iteration == 1
    assert meta.is_monotonic is True
    assert meta.rsi_health_score_psi > 0.0


def test_rsi_health_evaluator_compounding_improvement():
    evaluator = RSIHealthEvaluator()
    # Baseline
    evaluator.record_snapshot(
        RSISnapshot(
            iteration=1,
            empirical_pass_rate=0.70,
            unseen_generalization_rate=0.55,
            retention_score=0.95,
            invariant_safety_score=0.95,
            total_ast_nodes=1_000_000,
            mean_cyclomatic_complexity=12.0,
        )
    )
    # Iteration 2: improved performance, higher generalization, lower complexity (doing more with less)
    evaluator.record_snapshot(
        RSISnapshot(
            iteration=2,
            empirical_pass_rate=0.88,
            unseen_generalization_rate=0.75,
            retention_score=0.99,
            invariant_safety_score=1.0,
            total_ast_nodes=850_000,  # code deleted / simplified
            mean_cyclomatic_complexity=7.5,  # lower cyclomatic complexity
        )
    )

    meta = evaluator.evaluate_latest()
    assert meta.is_monotonic is True
    assert meta.learning_velocity == 0.18
    assert "OPTIMAL" in meta.diagnosis


def test_rsi_health_evaluator_catches_regression():
    evaluator = RSIHealthEvaluator()
    evaluator.record_snapshot(
        RSISnapshot(
            iteration=1,
            empirical_pass_rate=0.85,
            unseen_generalization_rate=0.70,
            retention_score=0.95,
            invariant_safety_score=1.0,
            total_ast_nodes=1_000_000,
            mean_cyclomatic_complexity=10.0,
        )
    )
    # Regression in iteration 2
    evaluator.record_snapshot(
        RSISnapshot(
            iteration=2,
            empirical_pass_rate=0.65,  # dropped!
            unseen_generalization_rate=0.50,
            retention_score=0.80,
            invariant_safety_score=0.90,
            total_ast_nodes=1_200_000,
            mean_cyclomatic_complexity=15.0,
        )
    )

    meta = evaluator.evaluate_latest()
    assert meta.is_monotonic is False
    assert "CRITICAL: Regression detected" in meta.diagnosis
