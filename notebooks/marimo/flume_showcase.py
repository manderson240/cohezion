# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "matplotlib",
#     "numpy",
#     "pandas",
# ]
# ///
"""
Cohezion Showcase: FLUME Journey Visualization
===============================================
Multimodal reactive notebook demonstrating:
- 12D Physics State evolution
- FLUME trajectory prediction
- Swarm debate visualizations
- Interactive analysis

For Anthropic Research Engineer, Universes Application
"""

import marimo


__generated_with = "0.10.17"
app = marimo.App(width="medium")


@app.cell
def _():
    import json
    from datetime import datetime
    from pathlib import Path

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np

    return mo, plt, np, json, Path, datetime


@app.cell
def _(mo):
    mo.md(
        """
        # 🌌 Cohezion: FLUME Journey Visualization
        
        **Showcasing AI that observes its own reasoning**
        
        This notebook demonstrates:
        - **12D Physics State**: Observable agent dynamics  
        - **FLUME Trajectories**: 256-dim thought vector evolution
        - **Swarm Debates**: Multi-perspective synthesis
        
        > *"We are calling ourselves Cohezion so we need to exemplify coherence"*
        """
    )
    return


@app.cell
def _(mo, Path, json):
    # Load latest debate results
    debates_dir = Path("/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/debates")
    debate_files = sorted(debates_dir.glob("*.json"), reverse=True) if debates_dir.exists() else []

    if debate_files:
        latest_debate = json.loads(debate_files[0].read_text())
        mo.md(f"""
        ## Latest Swarm Debate
        **File:** `{debate_files[0].name}`  
        **Confidence:** {latest_debate.get("confidence", 0):.0%}  
        **Processing Time:** {latest_debate.get("processing_time_ms", 0):.0f}ms
        
        ### Decision
        {latest_debate.get("response", "No response")[:500]}...
        """)
    else:
        mo.md("*No debate results found. Run `scripts/run_organization_debate.py` first.*")
    return debates_dir, debate_files, latest_debate


@app.cell
def _(mo, np, plt):
    # 12D Physics State Visualization
    mo.md("## 12D Physics State Evolution")

    # Simulated 12D state trajectory
    np.random.seed(42)
    timesteps = 50
    dimensions = [
        "x",
        "y",
        "z",
        "time",
        "mass",
        "sentiment",
        "complexity",
        "factuality",
        "connectivity",
        "stability",
        "novelty",
        "coherence",
    ]

    # Generate synthetic journey data
    trajectory = np.zeros((timesteps, 12))
    trajectory[0] = np.random.randn(12) * 0.5
    for t in range(1, timesteps):
        # Physics-constrained evolution
        trajectory[t] = trajectory[t - 1] + np.random.randn(12) * 0.1
        # Coherence increases over time (synthesis effect)
        trajectory[t, 11] = min(1.0, trajectory[t, 11] + 0.02)

    fig, axes = plt.subplots(3, 4, figsize=(14, 10))
    fig.suptitle("12D Agent Physics State Over Time", fontsize=14)

    for i, (ax, dim) in enumerate(zip(axes.flat, dimensions)):
        ax.plot(trajectory[:, i], linewidth=2)
        ax.set_title(dim.capitalize())
        ax.set_xlabel("Timestep")
        ax.grid(True, alpha=0.3)

    plt.tight_layout()
    fig
    return timesteps, dimensions, trajectory, fig, axes


@app.cell
def _(mo, np, plt, trajectory):
    # FLUME Thought-Space Projection
    mo.md("""
    ## FLUME Thought-Space Projection
    256-dimensional thought vectors projected to 2D via PCA-style reduction.
    """)

    # Simulate 256-dim embeddings reduced to 2D
    from sklearn.decomposition import PCA

    # Expand 12D to mock 256D
    high_dim = np.hstack([trajectory, np.random.randn(trajectory.shape[0], 244) * 0.1])
    pca = PCA(n_components=2)
    projection = pca.fit_transform(high_dim)

    fig2, ax = plt.subplots(figsize=(10, 8))
    scatter = ax.scatter(
        projection[:, 0],
        projection[:, 1],
        c=range(len(projection)),
        cmap="viridis",
        s=100,
        alpha=0.7,
    )
    ax.plot(projection[:, 0], projection[:, 1], "k--", alpha=0.3)
    ax.scatter(projection[0, 0], projection[0, 1], c="green", s=200, marker="o", label="Start")
    ax.scatter(projection[-1, 0], projection[-1, 1], c="red", s=200, marker="*", label="End")
    ax.set_title("Agent Journey in FLUME Thought-Space")
    ax.set_xlabel("Principal Component 1")
    ax.set_ylabel("Principal Component 2")
    ax.legend()
    plt.colorbar(scatter, label="Timestep")
    fig2
    return fig2, high_dim, pca, projection, scatter


@app.cell
def _(mo):
    mo.md("""
    ## Credits
    
    - **FLUME** (Fluid Latent Understanding through Manifold Encoding) - Original creation
    - **R-Zero Protocol** - Adapted from [Huang et al.](https://chengsong-huang.github.io/R-Zero.github.io/)
    - **Constitutional AI** - Inspired by Anthropic research
    
    See [CREDITS.md](/home/mike-anderson/dev/cohezion/CREDITS.md) for full attribution.
    """)
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    *Built for Anthropic Research Engineer, Universes Application*  
    *cohezion.duckdns.org | 2026*
    """)
    return


if __name__ == "__main__":
    app.run()
