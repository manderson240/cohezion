# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "numpy",
#     "plotly",
#     "pandas",
#     "httpx",
# ]
# ///
import marimo


__generated_with = "0.19.4"
app = marimo.App(width="full")


@app.cell
def _():
    import json
    import os
    from datetime import datetime

    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    return mo, np, go, px, make_subplots, pd, json, os, datetime


@app.cell
def _(mo):
    mo.md("""
    # 🌌 12D Journey Explorer: Swarm Interpretability

    *Mapping the hidden trajectories of LLM reasoning into physical state vectors.*

    ---

    ### 🏠 Think of it like...
    Imagine the swarm's thoughts as a 256-dimensional cloud. We project that cloud into a
    **12D Vector** (3 Spatial + 1 Time + 8 Brane) to see exactly how they are navigating
    the problem space. If they get stuck in a loop, you'll see a redundant toroidal orbit!

    ---
    """)
    return


@app.cell
def _(mo, np, pd):
    # Mock data generation if SurrealDB is empty (Sprint 6 bootstrap)
    def generate_mock_journey(n_steps=20):
        data = []
        for i in range(n_steps):
            # 12D State Vector construction
            # [x, y, z, t, b1, b2, b3, b4, b5, b6, b7, b8]
            x = np.sin(i / 5.0) * i
            y = np.cos(i / 5.0) * i
            z = i * 0.5
            t = i
            branes = np.random.rand(8) * 0.5 + (0.5 if i > 10 else 0.2)

            data.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "agent": "NexusResearchAgent" if i % 2 == 0 else "AnalystAgent",
                    "x": x,
                    "y": y,
                    "z": z,
                    "t": t,
                    "b1": branes[0],
                    "b2": branes[1],
                    "b3": branes[2],
                    "b4": branes[3],
                    "b5": branes[4],
                    "b6": branes[5],
                    "b7": branes[6],
                    "b8": branes[7],
                    "content": f"Exploring trajectory step {i}...",
                }
            )
        return pd.DataFrame(data)

    journey_df = generate_mock_journey()

    step_slider = mo.ui.slider(
        start=0, stop=len(journey_df) - 1, step=1, value=0, label="🚶 Journey Step", show_value=True
    )

    mo.hstack([step_slider], justify="center")
    return journey_df, step_slider


@app.cell
def _(mo, journey_df, step_slider, go):
    # Radar Chart for 8-Brane Sub-Manifold
    current_step = journey_df.iloc[step_slider.value]

    categories = [
        "Brane 1",
        "Brane 2",
        "Brane 3",
        "Brane 4",
        "Brane 5",
        "Brane 6",
        "Brane 7",
        "Brane 8",
    ]

    values = [current_step[f"b{i + 1}"] for i in range(8)]

    fig_radar = go.Figure()

    fig_radar.add_trace(
        go.Scatterpolar(
            r=values,
            theta=categories,
            fill="toself",
            line_color="#4ECDC4",
            name=f"Step {step_slider.value}",
        )
    )

    # Add HIHO stability circle at 0.5
    fig_radar.add_trace(
        go.Scatterpolar(
            r=[0.5] * 8,
            theta=categories,
            mode="lines",
            line=dict(color="gold", dash="dash"),
            name="HIHO Stability (0.5)",
        )
    )

    fig_radar.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 1], gridcolor="gray"),
            angularaxis=dict(gridcolor="gray"),
        ),
        showlegend=True,
        template="plotly_dark",
        margin=dict(t=30, b=30, l=30, r=30),
        title=f"8-Brane Resonance: {current_step['agent']}",
    )

    mo.md(f"""
    ### 📡 8-Brane Resonance (Step {step_slider.value})

    Agent: **{current_step["agent"]}**
    Observation: *{current_step["content"]}*
    """)

    return (fig_radar,)


@app.cell
def _(mo, journey_df, go):
    # 3D Spatial-Temporal Path
    fig_3d = go.Figure()

    fig_3d.add_trace(
        go.Scatter3d(
            x=journey_df["x"],
            y=journey_df["y"],
            z=journey_df["z"],
            mode="lines+markers",
            line=dict(color="#FF6B6B", width=4),
            marker=dict(size=5, color=journey_df["t"], colorscale="Viridis", opacity=0.8),
            name="Thought Trajectory",
        )
    )

    fig_3d.update_layout(
        title="12D Spatial-Temporal Journey",
        scene=dict(
            xaxis_title="Spatial X",
            yaxis_title="Spatial Y",
            zaxis_title="Spatial Z",
            bgcolor="black",
        ),
        template="plotly_dark",
        margin=dict(t=50, b=10, l=10, r=10),
        height=600,
    )

    return (fig_3d,)


@app.cell
def _(mo, fig_radar, fig_3d):
    mo.hstack([fig_radar, fig_3d], justify="space-around")
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    ### 🔬 Interpreting the 12D Vector

    - **Spatial (X, Y, Z)**: Represents the conceptual clustering. Similar ideas stay close.
    - **Time (T)**: Velocity of reasoning. Fast jumps indicate non-linear "Aha!" moments.
    - **Brane 1-8**: Specific information fabrics (Logic, Memory, Creativity, Physics, etc.).

    > 👉 **HIHO Threshold**: Look for Brane resonance at **0.5**. This is where reality precipitation occurs.

    ---
    *Built with Cohezion Swarm | FLUME Methodology | 2026*
    """)
    return


if __name__ == "__main__":
    app.run()
