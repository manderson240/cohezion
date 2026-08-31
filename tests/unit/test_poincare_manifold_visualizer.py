"""Unit tests for Poincaré 2048D Hyperbolic Manifold Visualizer."""

import math

import numpy as np
import plotly.graph_objects as go
import pytest

from cohezion.flume.poincare_manifold_visualizer import (
    PoincareManifoldVisualizer,
    compute_hyperbolic_distance,
    figure_to_html,
    figure_to_json,
    generate_poincare_figure,
    project_2048d_to_poincare_3d,
)


def test_hyperbolic_distance_math():
    u = np.full(2048, 0.01)
    v = np.full(2048, 0.02)

    # Self distance is 0
    d_self = compute_hyperbolic_distance(u, u)
    assert abs(d_self) < 1e-5

    # Positive distance
    d_uv = compute_hyperbolic_distance(u, v)
    assert d_uv > 0.0
    assert math.isfinite(d_uv)

    # Symmetry
    d_vu = compute_hyperbolic_distance(v, u)
    assert pytest.approx(d_uv, abs=1e-6) == d_vu


def test_project_2048d_to_poincare_3d():
    # 1D vector
    v1d = np.random.default_rng(42).normal(size=2048)
    p3d = project_2048d_to_poincare_3d(v1d)
    assert p3d.shape == (3,)
    assert np.linalg.norm(p3d) < 1.0

    # 2D batch
    v2d = np.random.default_rng(42).normal(size=(50, 2048))
    p3d_batch = project_2048d_to_poincare_3d(v2d)
    assert p3d_batch.shape == (50, 3)
    assert np.all(np.linalg.norm(p3d_batch, axis=1) < 1.0)


def test_visualizer_skills_and_retros_loading():
    viz = PoincareManifoldVisualizer(seed=42)
    skills = viz.load_cohezion_skills(max_skills=71)
    retros = viz.load_surreal_retrospectives(count=15)

    assert len(skills) >= 71
    assert len(retros) == 15

    for s in skills:
        assert s["vector_2048d"].shape == (2048,)
        assert s["coords_3d"].shape == (3,)
        assert np.linalg.norm(s["coords_3d"]) < 1.0
        assert s["hyp_dist_origin"] >= 0.0

    for r in retros:
        assert r["vector_2048d"].shape == (2048,)
        assert r["coords_3d"].shape == (3,)
        assert np.linalg.norm(r["coords_3d"]) < 1.0


def test_generate_poincare_figure():
    viz = PoincareManifoldVisualizer()
    skills = viz.load_cohezion_skills(max_skills=71)
    retros = viz.load_surreal_retrospectives(count=15)

    fig = generate_poincare_figure(skills, retros)
    assert isinstance(fig, go.Figure)
    assert len(fig.data) > 0

    html_out = figure_to_html(fig)
    json_out = figure_to_json(fig)
    assert isinstance(html_out, str)
    assert isinstance(json_out, str)
    assert len(html_out) > 0
    assert len(json_out) > 0
