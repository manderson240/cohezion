import marimo


__generated_with = "0.10.12"
app = marimo.App(title="Cohezion Manifold Explorer")


@app.cell
def __():
    import asyncio

    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.express as px
    from sklearn.decomposition import PCA

    from cohezion.core.persistence.surreal_client import SurrealClient

    mo.md("# 🌌 Cohezion Manifold Explorer")
    return PCA, SurrealClient, asyncio, mo, np, pd, px


@app.cell
async def __(np):
    # Load data from SurrealDB
    # In a real environment, we'd use the SurrealClient
    # For now, we'll simulate data if DB is down
    data = []
    try:
        # client = SurrealClient()
        # await client.connect()
        # nodes = await client.query("SELECT * FROM agent_thought WHERE embedding IS NOT NULL")
        # data = nodes
        pass
    except Exception:
        pass

    if not data:
        # Simulated data for UI demo
        n_points = 50
        data = [
            {
                "id": f"thought_{i}",
                "content": f"Sample thought content {i}",
                "embedding": np.random.randn(256).tolist(),
                "agent": np.random.choice(["Analyst", "Critic", "Synthesizer"]),
                "mission": "Alpha",
                "coherence": np.random.rand(),
            }
            for i in range(n_points)
        ]
    return (data,)


@app.cell
def __(PCA, data, mo, np, pd, px):
    # Process Embeddings with PCA
    embeddings = np.array([d["embedding"] for d in data])
    if len(embeddings) > 3:
        pca = PCA(n_components=3)
        coords = pca.fit_transform(embeddings)

        df = pd.DataFrame(coords, columns=["x", "y", "z"])
        df["agent"] = [d["agent"] for d in data]
        df["id"] = [d["id"] for d in data]
        df["coherence"] = [d["coherence"] for d in data]

        fig = px.scatter_3d(
            df,
            x="x",
            y="y",
            z="z",
            color="agent",
            size="coherence",
            hover_data=["id"],
            title="Agent Thought Trajectories in Latent Space",
            color_discrete_map={
                "Analyst": "#FF6B6B",
                "Critic": "#4ECDC4",
                "Synthesizer": "#45B7D1",
            },
        )

        fig.update_layout(margin={"l": 0, "r": 0, "b": 0, "t": 30})
        plot = mo.ui.plotly(fig)
    else:
        plot = mo.md("Not enough data points yet to render manifold.")

    mo.vstack([mo.md("### 3D Latent Manifold Projection"), plot])
    return coords, df, fig, pca, plot


@app.cell
def __(df, mo, plot):
    # Details Panel
    selected = plot.value
    if selected and not df.empty:
        idx = selected[0]
        row = df.iloc[idx]
        details = mo.md(
            f"**Selected Node**: {row['id']}  \n**Agent**: {row['agent']}  \n**Coherence**: {row['coherence']:.2f}"
        )
    else:
        details = mo.md("*Select a point in the manifold to see details.*")

    mo.section(details, title="🔍 Thought Details")
    return details, idx, row, selected


if __name__ == "__main__":
    app.run()
