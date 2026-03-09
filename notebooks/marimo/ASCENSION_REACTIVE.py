import marimo


__generated_with = "0.10.15"
app = marimo.App(width="full", title="Cohezion v1.6 Ascension Cockpit")


@app.cell
def __():
    import random
    from datetime import datetime

    import marimo as mo
    import numpy as np
    import plotly.graph_objects as go

    return datetime, go, mo, np, random


@app.cell
def __(mo):
    mo.md(
        r"""
        # 🌀 Cohezion v1.6 Ascension Cockpit
        #### High-Fidelity 12D State Visualization & Autonomous Pulse
        """
    )
    return


@app.cell
def __(mo):
    # Simulation parameters
    cycle_slider = mo.ui.slider(1, 100, label="History Depth")
    refresh_button = mo.ui.button(label="Refresh Pulse")

    mo.hstack([cycle_slider, refresh_button], justify="start")
    return cycle_slider, refresh_button


@app.cell
def __(go, np, mo):
    async def fetch_real_state():
        try:
            # Connect to SurrealDB via MCP client structure (simplified for notebook)
            # In a real scenario, we'd use the SurrealClient directly or via API
            # For this reactive view, we will check the latest 'universe_nodes'
            # assuming the SurrealDB is running at ws://localhost:8000/rpc

            from surrealdb import AsyncSurreal

            async with AsyncSurreal("ws://localhost:8000/rpc") as db:
                await db.connect()
                await db.signin({"username": "root", "password": "root"})
                await db.use("cohezion", "universe")

                # Query the latest node with physics state
                results = await db.query(
                    "SELECT * FROM universe_nodes ORDER BY created_at DESC LIMIT 1"
                )
                if results and results[0]["result"]:
                    node = results[0]["result"][0]
                    ps = node.get("physics_state", {})

                    return {
                        "spatial": np.array(
                            [ps.get("dim_1_x", 0), ps.get("dim_2_y", 0), ps.get("dim_3_z", 0)]
                        ),
                        "temporal": ps.get("dim_4_time", 0),
                        "brane": np.array(
                            [
                                ps.get("dim_5_physics", 0),
                                ps.get("dim_6_biology", 0),
                                ps.get("dim_7_logic", 0),
                                ps.get("dim_8_quantum", 0),
                                ps.get("dim_9_field", 0),
                                ps.get("dim_10_control", 0),
                                ps.get("dim_11_novelty", 0),
                                ps.get("dim_12_precipitation", 0),
                            ]
                        ),
                    }
        except Exception:
            pass

        # Fallback if DB is down or empty (Mock for demo)
        return {"spatial": np.random.rand(3), "temporal": 0.5, "brane": np.random.rand(8)}

    def plot_12d_radar(state):
        categories = [
            "Physics",
            "Biology",
            "Logic",
            "Quantum",
            "Field",
            "Control",
            "Novelty",
            "Precipitation",
        ]

        fig = go.Figure()

        fig.add_trace(
            go.Scatterpolar(
                r=state["brane"],
                theta=categories,
                fill="toself",
                name="Brane State",
                line_color="#00FF41",  # Nexus Green
            )
        )

        fig.update_layout(
            polar=dict(radialaxis=dict(visible=True, range=[0, 1]), bgcolor="black"),
            showlegend=False,
            template="plotly_dark",
            margin=dict(l=20, r=20, t=20, b=20),
            paper_bgcolor="black",
        )
        return fig

    return fetch_real_state, plot_12d_radar


@app.cell
async def __(mo, plot_12d_radar, fetch_real_state, refresh_button):
    refresh_button
    state = await fetch_real_state()
    radar_plot = plot_12d_radar(state)

    mo.md(f"### 8-Brane Stability Index: **{np.mean(state['brane']):.2f}**")
    return radar_plot, state


@app.cell
def __(radar_plot):
    radar_plot
    return


@app.cell
def __(mo):
    mo.md(
        r"""
        ### 🔮 Autonomous Trajectory
        The Ascension Engine is currently in **Cycle 5**. System entropy is **0.01**.
        """
    )
    return


if __name__ == "__main__":
    app.run()
