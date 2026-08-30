"""Unit tests for Palimpsa Bayesian Metaplasticity Continual Memory Engine (arXiv:2602.09075)."""

from __future__ import annotations

import numpy as np

from cohezion.flume.bayesian_metaplasticity_engine import BayesianMetaplasticityEngine


def test_bayesian_metaplasticity_initialization() -> None:
    engine = BayesianMetaplasticityEngine(d_k=8, d_v=8, I_prior=1.0)
    assert engine.state.S.shape == (8, 8)
    assert np.allclose(engine.state.I_diag, 1.0)


def test_associative_memory_and_metaplastic_growth() -> None:
    engine = BayesianMetaplasticityEngine(d_k=4, d_v=4, I_prior=1.0, A_decay=0.001, lr=2.0)
    k1 = np.array([1.0, 0.0, 0.0, 0.0])
    v1 = np.array([0.5, 0.5, 0.5, 0.5])

    # First step learns pattern
    _, ratio0 = engine.step(k1, v1)
    assert ratio0 >= 0.0

    # Recall on subsequent steps converges toward v1
    for _ in range(5):
        y_recall, ratio = engine.step(k1, v1)

    assert np.allclose(y_recall, v1, atol=0.1)
    assert ratio > 0.0


def test_stability_plasticity_no_catastrophic_forgetting() -> None:
    engine = BayesianMetaplasticityEngine(d_k=4, d_v=4, I_prior=1.0, A_decay=0.001, lr=2.0)
    k1 = np.array([1.0, 0.0, 0.0, 0.0])
    v1 = np.array([1.0, 0.0, 0.0, 0.0])

    k2 = np.array([0.0, 1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0, 0.0])

    # Consolidate k1, v1
    for _ in range(6):
        engine.step(k1, v1)

    # Learn k2, v2
    for _ in range(6):
        engine.step(k2, v2)

    # Recall k1 without forgetting
    y1, _ = engine.step(k1, v1)
    assert np.allclose(y1, v1, atol=0.2)
