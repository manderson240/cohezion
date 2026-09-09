import pytest
from cohezion.physics.my_big_toe_entropy_engine import (
    MyBigTOEEntropyEngine,
    EntropyState,
    NegentropyTransitionResult,
)


def test_empty_points_entropy():
    engine = MyBigTOEEntropyEngine()
    s = engine.calculate_state_entropy([])
    assert s.total_system_entropy == 0.0


def test_clustering_reduces_entropy():
    engine = MyBigTOEEntropyEngine()

    # Pre-state: Highly scattered noisy points far from centroid with turbulent coherences (High Entropy)
    pre_points = [
        [0.8, -0.7, 0.5],
        [-0.8, 0.7, -0.5],
        [0.6, 0.6, 0.6],
        [-0.6, -0.6, -0.6],
    ]
    pre_coherences = [0.10, 0.95, 0.20, 0.85]  # High dispersion from 0.50

    # Post-state: Highly coherent points tightly clustered around centroid with 0.50 HIHO equilibrium (Low Entropy)
    post_points = [
        [0.10, 0.10, 0.10],
        [0.11, 0.10, 0.10],
        [0.10, 0.11, 0.10],
        [0.10, 0.10, 0.11],
    ]
    post_coherences = [0.500, 0.500, 0.500, 0.500]  # Perfect HIHO stability

    res = engine.evaluate_transition(
        pre_points=pre_points,
        post_points=post_points,
        pre_coherences=pre_coherences,
        post_coherences=post_coherences,
    )

    assert isinstance(res, NegentropyTransitionResult)
    assert res.delta_entropy < 0.0, f"Entropy must decrease: Delta S = {res.delta_entropy}"
    assert res.is_entropy_reduced is True
    assert res.entropy_reduction_rate_pct > 0.0
    assert res.autoharness_verified is True
    assert res.execution_latency_ms < 25.0


def test_divergent_transition_rejected_by_autoharness():
    engine = MyBigTOEEntropyEngine()

    # Transitioning from organized to disorganized (increasing entropy)
    pre_points = [[0.1, 0.1], [0.1, 0.12]]
    pre_cohs = [0.50, 0.50]

    post_points = [[0.8, -0.8], [-0.8, 0.8]]
    post_cohs = [0.05, 0.95]

    res = engine.evaluate_transition(
        pre_points=pre_points,
        post_points=post_points,
        pre_coherences=pre_cohs,
        post_coherences=post_cohs,
    )

    assert res.delta_entropy > 0.0
    assert res.is_entropy_reduced is False
    # AutoHarness must reject entropy-increasing transition!
    assert res.autoharness_verified is False
