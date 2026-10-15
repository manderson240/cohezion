import numpy as np

from cohezion.kaggle.convex_ensemble_optimizer import ConvexEnsembleOptimizer


def test_simplex_projection():
    optimizer = ConvexEnsembleOptimizer()
    v = np.array([0.5, 0.8, -0.2])
    proj = optimizer.project_simplex(v)
    assert np.isclose(np.sum(proj), 1.0, atol=1e-7)
    assert np.all(proj >= 0.0)


def test_convex_optimization_monotonic_reduction():
    np.random.seed(42)
    n, c = 200, 3

    # Ground truth targets
    y = np.random.binomial(1, 0.3, size=(n, c)).astype(np.float64)

    # Model 1: Good model (close to targets with some noise)
    p1 = np.clip(y * 0.8 + 0.1 + np.random.normal(0, 0.1, size=(n, c)), 0.01, 0.99)
    # Model 2: Poor random model
    p2 = np.random.uniform(0.1, 0.9, size=(n, c))
    # Model 3: Inverse model (bad)
    p3 = 1.0 - p1

    optimizer = ConvexEnsembleOptimizer()
    res = optimizer.optimize_multi_label_log_loss(
        predictions=[p1, p2, p3],
        targets=y,
        max_iter=50,
    )

    assert res.converged is True
    assert res.optimal_loss <= res.initial_loss
    assert np.isclose(np.sum(res.weights), 1.0, atol=1e-5)
    assert np.all(res.weights >= 0.0)
    # Model 1 should receive majority weight
    assert res.weights[0] > res.weights[1]
    assert res.weights[0] > res.weights[2]


def test_convex_optimization_single_model():
    y = np.array([[1.0, 0.0], [0.0, 1.0]])
    p1 = np.array([[0.9, 0.1], [0.1, 0.9]])
    optimizer = ConvexEnsembleOptimizer()
    res = optimizer.optimize_multi_label_log_loss([p1], y)
    assert res.weights[0] == 1.0
    assert res.iterations == 0
