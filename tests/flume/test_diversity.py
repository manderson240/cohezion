import numpy as np

from cohezion.flume.diversity import gvendi_diversity_filter


def _mean_pairwise_cosine_dist(vecs: list[np.ndarray]) -> float:
    mat = np.stack([v / max(np.linalg.norm(v), 1e-9) for v in vecs])
    sim = mat @ mat.T
    n = len(vecs)
    # exclude diagonal
    mask = ~np.eye(n, dtype=bool)
    return float((1.0 - sim[mask]).mean())


def test_returns_correct_count():
    rng = np.random.default_rng(0)
    vectors = [rng.standard_normal(256) for _ in range(500)]
    result = gvendi_diversity_filter(vectors, target_n=50)
    assert len(result) == 50
    assert len(set(result)) == 50  # no duplicates
    assert all(0 <= i < 500 for i in result)


def test_maximizes_spread():
    rng = np.random.default_rng(1)
    # Two tight clusters + sparse outliers — diverse selection should pick outliers
    cluster_a = [rng.standard_normal(256) * 0.01 + np.array([1.0] + [0.0] * 255) for _ in range(200)]
    cluster_b = [rng.standard_normal(256) * 0.01 + np.array([-1.0] + [0.0] * 255) for _ in range(200)]
    outliers = [rng.standard_normal(256) for _ in range(100)]
    vectors = cluster_a + cluster_b + outliers

    selected_idx = gvendi_diversity_filter(vectors, target_n=30, seed=42)
    selected_vecs = [vectors[i] for i in selected_idx]

    # Random baseline
    rng2 = np.random.default_rng(42)
    random_idx = rng2.choice(len(vectors), size=30, replace=False).tolist()
    random_vecs = [vectors[i] for i in random_idx]

    diverse_dist = _mean_pairwise_cosine_dist(selected_vecs)
    random_dist = _mean_pairwise_cosine_dist(random_vecs)
    assert diverse_dist > random_dist, (
        f"Expected diverse selection ({diverse_dist:.4f}) > random ({random_dist:.4f})"
    )


def test_fallback_on_small_input():
    rng = np.random.default_rng(2)
    vectors = [rng.standard_normal(256) for _ in range(10)]
    result = gvendi_diversity_filter(vectors, target_n=10)
    assert sorted(result) == list(range(10))

    result_larger = gvendi_diversity_filter(vectors, target_n=50)
    assert sorted(result_larger) == list(range(10))
