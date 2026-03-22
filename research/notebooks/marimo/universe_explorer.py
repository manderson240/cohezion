import marimo


__generated_with = "0.10.14"
app = marimo.App(title="Universe Explorer: High-Fidelity 12D Metrics")


@app.cell
def __():
    import re
    from pathlib import Path

    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from sklearn.decomposition import PCA

    return Path, PCA, mo, np, pd, px, go, re


@app.cell
def __(mo):
    mo.md(
        r"""
        # 🌌 Universe Explorer (12D Edition)
        ### Phase 21 & Hour of Power High-Fidelity Retrospective

        This dashboard implements **Gateway 32** visualization standards, including multidimensional physics state analysis and natural language explainability.
        """
    )
    return


@app.cell
async def __(re, np):
    from cohezion.core.persistence.surreal_client import SurrealClient

    async def get_high_fidelity_data():
        client = SurrealClient()
        await client.connect()
        # Fetch actual experiences from DB
        res = await client.query(
            "SELECT * FROM universe_nodes WHERE node_type = 'agent_thought' ORDER BY metadata.timestamp ASC"
        )
        nodes = res[0] if res else []
        await client.close()

        entries = []
        for n in nodes:
            meta = n.get("metadata", {})
            ts_val = meta.get("timestamp", 0)
            from datetime import datetime

            ts = datetime.fromtimestamp(ts_val).strftime("%H:%M:%S")

            # Extract 12D Physics State
            ps = n.get("physics_state", {})

            # Extract metrics from content if ps is empty (fallback)
            content = n.get("content", "")
            stability = ps.get("dim_10_stability", 0.0)
            zpe_match = re.search(r"\*\*ZPE Balance\*\*:\s*([\d\.]+)", content)
            if zpe_match:
                float(zpe_match.group(1))

            # 12D dimensions
            dims = {
                "x": ps.get("dim_1_x", 0.0),
                "y": ps.get("dim_2_y", 0.0),
                "z": ps.get("dim_3_z", 0.0),
                "time": ps.get("dim_4_time", 0.0),
                "mass": ps.get("dim_5_mass", 0.0),
                "sentiment": ps.get("dim_6_sentiment", 0.0),
                "complexity": ps.get("dim_7_complexity", 0.0),
                "factuality": ps.get("dim_8_factuality", 0.0),
                "connectivity": ps.get("dim_9_connectivity", 0.0),
                "stability": stability,
                "novelty": ps.get("dim_11_novelty", 0.0),
                "coherence": ps.get("dim_12_coherence", 0.0),
            }

            # Vector for PCA
            vec = list(dims.values())

            entries.append(
                {
                    "Timestamp": ts,
                    "Epoch": meta.get("epoch", "Unknown"),
                    "Model": meta.get("model", "unknown"),
                    "Phi": meta.get("phi_score", 0.0),
                    "Event": content[:100].replace("\n", " ") + "...",
                    "Vector": vec,
                    **dims,
                }
            )
        return entries

    data = await get_high_fidelity_data()
    return data, get_high_fidelity_data


@app.cell
def __(data, pd):
    df = pd.DataFrame(data)
    return (df,)


@app.cell
def __(df, mo, px):
    mo.md("## 📈 Homeostasis Trajectory")
    if df.empty:
        mo.md("⚠️ No data available. Run some agentic missions to populate the 12D manifold.")
        fig_line = None
    else:
        fig_line = px.line(
            df,
            x="Timestamp",
            y=["stability", "coherence", "complexity"],
            title="12D Vital Signs",
            template="plotly_dark",
            color_discrete_map={
                "stability": "#4ECDC4",
                "coherence": "#FF6B6B",
                "complexity": "#FFD93D",
            },
        )
        fig_line.add_hline(y=0.5, line_dash="dash", line_color="gold", annotation_text="HIHO Threshold")
        mo.ui.plotly(fig_line)
    return (fig_line,)


@app.cell
def __(PCA, df, mo, np, px):
    mo.md("## 🌌 Latent Manifold Projection (PCA)")

    if df.empty:
        mo.md("Insufficient data for PCA projection.")
        return None, None, None, None, None

    # Run PCA on the vectors
    vectors = np.array(df["Vector"].tolist())
    if len(vectors) > 2:
        pca = PCA(n_components=2)
        coords = pca.fit_transform(vectors)
        df_pca = df.copy()
        df_pca["PCA1"] = coords[:, 0]
        df_pca["PCA2"] = coords[:, 1]

        fig_pca = px.scatter(
            df_pca,
            x="PCA1",
            y="PCA2",
            color="Phi",
            size="mass",
            hover_data=["Timestamp", "Model", "Event"],
            title="State Space Evolution",
            template="plotly_dark",
        )
        mo.ui.plotly(fig_pca)
    else:
        mo.md("Insufficient data for PCA projection.")
        coords, df_pca, fig_pca, pca = None, None, None, None
    return coords, df_pca, fig_pca, pca, vectors


@app.cell
def __(df, go, mo):
    mo.md("## 🕸️ Single-State Deep Dive (Radar)")

    if df.empty:
        mo.md("No data available.")
        return None, None

    selected_idx = mo.ui.slider(0, len(df) - 1, label="Select Inference Step", value=0)

    def render_radar(idx):
        if idx >= len(df):
            return None
        row = df.iloc[idx]
        categories = [
            "mass",
            "sentiment",
            "complexity",
            "factuality",
            "connectivity",
            "stability",
            "novelty",
            "coherence",
        ]
        values = [row[cat] for cat in categories]

        fig = go.Figure()
        fig.add_trace(
            go.Scatterpolar(
                r=values,
                theta=categories,
                fill="toself",
                name=f"Step {idx}",
                line_color="#4ECDC4",
            )
        )
        fig.update_layout(
            polar={"radialaxis": {"visible": True, "range": [0, 1]}},
            showlegend=False,
            template="plotly_dark",
            title=f"Inference Dynamics: {row['Timestamp']}",
        )
        return fig

    mo.hstack([selected_idx, mo.ui.plotly(render_radar(selected_idx.value))], justify="start")
    return render_radar, selected_idx


@app.cell
def __(df, mo, selected_idx):
    def get_physicist_narrative(idx):
        if df.empty or idx is None or idx >= len(df):
            return mo.md("No narrative available.")

        row = df.iloc[idx]

        # Logic for 'Physicist' explainability
        highlights = []
        if row["coherence"] < 0.5:
            highlights.append(
                "⚠️ **Critical Reality Destabilization**: Coherence has dropped below the 0.5 HIHO threshold."
            )
        if row["complexity"] > 0.8:
            highlights.append("🧠 **Inference Density Spike**: Complexity is peaking.")
        if row["novelty"] > 0.7:
            highlights.append("✨ **Novelty Breakthrough**: A high-novelty thought has been imprinted.")

        narrative = (
            "\n\n".join(highlights)
            if highlights
            else "The cosmic engine is stable. Homeostasis maintained."
        )

        return mo.md(f"""
        ### 🧑‍🔬 The Physicist's Perspective

        **Node ID**: `{idx}` | **Model**: `{row["Model"]}` | **Phi Score**: `{row["Phi"]}`

        {narrative}

        ---
        *Explanation derived from 12D PhysicsState Vector variance.*
        """)

    if selected_idx:
        get_physicist_narrative(selected_idx.value)
    return (get_physicist_narrative,)


if __name__ == "__main__":
    app.run()
