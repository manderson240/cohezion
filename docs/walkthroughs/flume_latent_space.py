"""FLUME Latent Space Explorer — Interactive Walkthrough.

Reactive marimo notebook exploring the FLUME (Fluid Latent Understanding
through Manifold Encoding) 256-dimensional latent space.

Demonstrates:
- Latent vector sampling and 3D PCA projection
- Cyclic β-annealing schedule for KL regularisation
"""

import marimo

__generated_with = "0.23.10"
app = marimo.App(width="medium", app_title="FLUME Latent Space Explorer")


@app.cell
def _():
    import math
    import random

    import marimo as mo
    import plotly.graph_objects as go

    return go, math, mo, random


@app.cell
def _(mo):
    mo.md(
        r"""
        # FLUME Latent Space Explorer

        **FLUME** encodes compound-loop execution traces into a **256-dimensional
        latent manifold** using a β-VAE architecture:

        ```
        Input → Encoder → μ, σ (256D) → z ~ N(μ, σ²) → Decoder → Reconstruction
        ```

        The optimal β (KL weight) is **≤ 0.01** — above β=0.020 the posterior
        collapses (KL → 0, decoder ignores z). Explore the latent geometry below.
        """
    )
    return ()


@app.cell
def _(mo):
    n_points = mo.ui.slider(50, 500, step=50, value=200, label="Sample points")
    n_clusters = mo.ui.slider(2, 8, step=1, value=4, label="Semantic clusters")
    latent_dim = mo.ui.slider(2, 256, step=2, value=256, label="Latent dim (D)")
    beta_val = mo.ui.slider(
        0.001, 0.025, step=0.001, value=0.010,
        label="β (KL weight)", show_value=True,
    )
    mo.vstack([n_points, n_clusters, mo.hstack([latent_dim, beta_val], justify="start")])
    return beta_val, latent_dim, n_clusters, n_points


@app.cell
def _(beta_val, mo):
    _collapse = beta_val.value > 0.015
    collapse_risk = _collapse
    mo.callout(
        mo.md(
            "⚠️ **Posterior collapse risk** — β > 0.015 empirical threshold"
            if _collapse
            else "✅ β is within safe range"
        ),
        kind="warn" if _collapse else "info",
    )
    return (collapse_risk,)


@app.cell
def _(latent_dim, math, n_clusters, n_points, random):
    """Sample synthetic 256D latent vectors with cluster structure."""
    random.seed(7)
    D = latent_dim.value
    K = n_clusters.value
    N = n_points.value

    _centers = [[random.gauss(0, 2.0) for _ in range(D)] for _ in range(K)]
    labels = []
    vectors = []
    for _i in range(N):
        _ci = _i % K
        labels.append(_ci)
        _v = [_centers[_ci][_d] + random.gauss(0, 0.6) for _d in range(D)]
        _norm = math.sqrt(sum(_x ** 2 for _x in _v)) or 1.0
        vectors.append([_x / _norm for _x in _v])

    return D, K, N, labels, vectors


@app.cell
def _(K, go, labels, mo, random, vectors):
    """3D PCA projection via Monte Carlo random-projection approximation."""

    def _rp3(X):
        _n, _d = len(X), len(X[0])
        _mean = [sum(X[_i][_j] for _i in range(_n)) / _n for _j in range(_d)]
        _Xc = [[X[_i][_j] - _mean[_j] for _j in range(_d)] for _i in range(_n)]
        random.seed(0)
        _axes = []
        for _ in range(3):
            _ax = [random.gauss(0, 1) for _ in range(_d)]
            _nm = sum(_x ** 2 for _x in _ax) ** 0.5
            _axes.append([_x / _nm for _x in _ax])
        return [
            [sum(_Xc[_i][_j] * _axes[_k][_j] for _j in range(_d)) for _k in range(3)]
            for _i in range(_n)
        ]

    _coords = _rp3(vectors)
    _x3, _y3, _z3 = zip(*_coords)

    _colours = ["#4C78A8", "#F58518", "#E45756", "#72B7B2",
                "#54A24B", "#EECA3B", "#B279A2", "#FF9DA6"]

    fig_latent = go.Figure()
    for _ci in range(K):
        _idxs = [_i for _i, _lbl in enumerate(labels) if _lbl == _ci]
        fig_latent.add_trace(go.Scatter3d(
            x=[_x3[_i] for _i in _idxs],
            y=[_y3[_i] for _i in _idxs],
            z=[_z3[_i] for _i in _idxs],
            mode="markers",
            marker=dict(size=4, color=_colours[_ci % len(_colours)], opacity=0.8),
            name=f"Cluster {_ci}",
        ))

    fig_latent.update_layout(
        title="FLUME Latent Space (3D random projection)",
        scene=dict(xaxis_title="PC1", yaxis_title="PC2", zaxis_title="PC3"),
        height=500,
        legend_title="Semantic cluster",
    )
    mo.ui.plotly(fig_latent)
    return (fig_latent,)


@app.cell
def _(mo):
    mo.md("## β-Annealing Schedule")
    return ()


@app.cell
def _(beta_val, go, math, mo):
    """Cyclic β schedule: amp*(1 - cos(2π·s/period)) — amp = β_max / 2."""
    _amp = beta_val.value / 2.0
    _period = 50
    _steps = list(range(300))
    _sched = [_amp * (1 - math.cos(2 * math.pi * _s / _period)) for _s in _steps]
    _threshold = [0.020] * len(_steps)

    fig_beta = go.Figure()
    fig_beta.add_trace(go.Scatter(
        x=_steps, y=_sched, mode="lines",
        name=f"β schedule (amp={_amp:.4f})",
        line=dict(color="#4C78A8"),
    ))
    fig_beta.add_trace(go.Scatter(
        x=_steps, y=_threshold, mode="lines",
        name="Collapse threshold (0.020)",
        line=dict(dash="dash", color="#E45756"),
    ))
    fig_beta.update_layout(
        title="Cyclic β-Annealing Schedule",
        xaxis_title="Training step",
        yaxis_title="β (KL weight)",
        height=350,
    )
    mo.ui.plotly(fig_beta)
    return (fig_beta,)


@app.cell
def _(beta_val, latent_dim, mo, n_clusters, n_points):
    mo.md(
        f"""
        ## Configuration Summary

        | Parameter | Value | Constraint |
        |-----------|-------|-----------|
        | Latent dim D | **{latent_dim.value}** | Optimal: 256 (hd=4096 decoder) |
        | β (KL weight) | **{beta_val.value:.3f}** | Must be ≤ 0.010 |
        | Sample points N | **{n_points.value}** | — |
        | Semantic clusters K | **{n_clusters.value}** | — |

        > **Harness invariant A3:** `kl_weight ≤ 0.01` in `flume/training.py`.
        > Exceeding β=0.020 empirically collapses the posterior (KL→0.024 measured
        > 2026-05-19). Cyclic schedule with `amp=0.005` stays within bounds.
        """
    )
    return ()


@app.cell
def _(mo):
    import os
    _default_url = os.getenv("LEMONADE_URL", "http://localhost:13305")
    flume_query = mo.ui.text_area(
        placeholder="Ask about β-VAE KL collapse, latent geometry, HIHO equilibrium in latent space...",
        label="Ask the local agent (AMD silicon, $0)",
        rows=3,
    )
    flume_model = mo.ui.dropdown(
        ["llama3.2-1b-FLM", "Bonsai-8B-gguf", "DeepSeek-Qwen3-8B-GGUF"],
        value="llama3.2-1b-FLM",
        label="Model",
    )
    flume_run = mo.ui.run_button(label="Ask Agent ▶")
    flume_url = mo.ui.text(value=_default_url, label="Lemonade URL")
    mo.vstack([
        mo.md("## Live Agent — Ask About FLUME Latent Space"),
        mo.hstack([flume_url, flume_model], justify="start"),
        flume_query,
        flume_run,
    ])
    return flume_model, flume_query, flume_run, flume_url


@app.cell
def _(flume_model, flume_query, flume_run, flume_url, mo):
    import requests as _req

    mo.stop(not flume_run.value, mo.md("_Configure a query above, then click **Ask Agent ▶**_"))

    def _ask(q: str, model: str, base_url: str) -> str:
        try:
            r = _req.post(
                f"{base_url.rstrip('/')}/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": (
                            "You are an expert in β-VAE latent space geometry and FLUME "
                            "(Fluid Latent Understanding through Manifold Encoding). "
                            "Key invariants: β ≤ 0.01, 2-layer decoder, hidden_dim=4096. "
                            "Explain KL regularisation, posterior collapse thresholds, "
                            "and semantic cluster geometry concisely."
                        )},
                        {"role": "user", "content": q},
                    ],
                    "max_tokens": 600,
                },
                timeout=90,
            )
            r.raise_for_status()
            return r.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            return f"⚠️ Lemonade error: {exc}"

    _answer = _ask(flume_query.value, flume_model.value, flume_url.value)
    mo.callout(mo.md(_answer), kind="info")
    return ()


if __name__ == "__main__":
    app.run()
