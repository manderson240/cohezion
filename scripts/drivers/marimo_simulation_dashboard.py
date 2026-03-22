import marimo


__generated_with = "0.7.12"
app = marimo.App(width="full")


@app.cell
def __():
    import asyncio
    import json
    import time
    from datetime import datetime

    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.express as px

    from cohezion.core.persistence.surreal_client import PhysicsState, SurrealClient

    return PhysicsState, SurrealClient, asyncio, datetime, json, mo, np, pd, px, time


@app.cell
async def __(SurrealClient):
    # Fetch nodes in a reactive way
    async def fetch_nodes_from_db(limit=2000):
        client_instance = SurrealClient()
        try:
            await client_instance.connect()
            raw_data = await client_instance.get_all_nodes(limit=limit)
            return raw_data
        finally:
            await client_instance.close()

    nodes_data = await fetch_nodes_from_db()
    return nodes_data, fetch_nodes_from_db


@app.cell
def __(nodes_data, pd):
    # Process nodes into a dataframe including ECO metrics
    def to_dataframe(nodes):
        if not nodes:
            return pd.DataFrame()

        rows = []
        for n in nodes:
            p = n.physics_state
            meta = n.metadata
            eco = meta.get("eco_metrics", {})

            rows.append(
                {
                    "id": n.id,
                    "x": p.x,
                    "y": p.y,
                    "z": p.z,
                    "mass": p.mass,
                    "stability": p.stability,
                    "coherence": p.coherence,
                    "complexity": p.complexity,
                    "novelty": p.novelty,
                    "stream": meta.get("stream", "unknown"),
                    "content": n.content,
                    # Eco Metrics (InVEST Abstractions)
                    "info_density": eco.get("info_density", 0),
                    "energy_flow": eco.get("energy_flow", 0),
                    "habitat_quality": eco.get("habitat_quality", 0),
                }
            )
        return pd.DataFrame(rows)

    substrate_df = to_dataframe(nodes_data)
    return substrate_df, to_dataframe


@app.cell
def __(mo):
    mo.md("# 🌌 Cohezion: The Multiverse Lattice (Eco-Overlay Edition)")
    return


@app.cell
def __(mo, px, substrate_df):
    def render_manifold_plot(df, color_metric="stability"):
        if df.empty:
            return mo.md(
                "### 📡 Synchronizing with Substrate...\nNo simulation data found in SurrealDB yet."
            )

        # 3D Manifold Projection with Dynamic Metric Coloring
        fig = px.scatter_3d(
            df,
            x="x",
            y="y",
            z="z",
            color=color_metric,
            size="mass",
            hover_data=["id", "stream", "habitat_quality"],
            title=f"12D Physics Manifold - {color_metric.replace('_', ' ').title()}",
            color_continuous_scale="Viridis",
            template="plotly_dark",
            height=800,
        )
        fig.update_layout(margin={"l": 0, "r": 0, "b": 0, "t": 40})
        return mo.plotly(fig)

    metric_selector = mo.ui.dropdown(
        ["stability", "info_density", "energy_flow", "habitat_quality"],
        value="habitat_quality",
        label="Select Map Metric (InVEST Adaptation)",
    )

    return (
        mo.vstack([metric_selector, render_manifold_plot(substrate_df, metric_selector.value)]),
        metric_selector,
        render_manifold_plot,
    )


@app.cell
def __(mo, substrate_df):
    # Selection control
    options_list = substrate_df["id"].tolist() if not substrate_df.empty else []
    selected_sim_id = mo.ui.dropdown(options_list, label="🔍 Inspect Agentic Journey")
    selected_sim_id
    return (selected_sim_id,)


@app.cell
def __(mo, selected_sim_id, substrate_df):
    # Display details for selected simulation
    def show_discovery_details(df, target_id):
        if df.empty or not target_id:
            return mo.md("Select a node from the manifold to inspect the underlying logic.")

        row_match = df[df["id"] == target_id]
        if row_match.empty:
            return mo.md("Node not found.")

        data_point = row_match.iloc[0]

        return mo.vstack(
            [
                mo.md(f"## Journey: `{target_id}`"),
                mo.md(
                    f"**Stream:** `{data_point['stream']}` | **Habitat Quality:** `{data_point['habitat_quality']:.4f}`"
                ),
                mo.md(
                    f"**Info Density:** `{data_point['info_density']:.4f}` | **Energy Flow:** `{data_point['energy_flow']:.4f}`"
                ),
                mo.md("---"),
                mo.code(data_point["content"], language="markdown"),
            ]
        )

    show_discovery_details(substrate_df, selected_sim_id.value)
    return (show_discovery_details,)


@app.cell
def __(mo):
    # Global Controls
    mo.vstack(
        [
            mo.md("### 🛠️ Substrate Tuning"),
            mo.md("Adjust the reality precipitation parameters for the ongoing 1M+ mission."),
            mo.ui.slider(0, 1, step=0.01, value=0.85, label="Physics weight (PINO Enforcement)"),
            mo.ui.slider(0, 1, step=0.01, value=0.5, label="Stability Target (HIHO Goldilocks)"),
            mo.ui.button(label="Update Swarm Configuration", kind="primary"),
        ]
    )
    return


if __name__ == "__main__":
    app.run()
