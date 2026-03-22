import marimo


__generated_with = "0.10.9"
app = marimo.App(width="medium")


@app.cell
def _():
    import random
    import time
    from datetime import datetime

    import marimo as mo
    import plotly.graph_objects as go
    import psutil

    return datetime, go, mo, psutil, random, time


@app.cell
def _(mo):
    mo.md(
        r"""
        # 💓 The Pulse: 12D Cognitive Lattice
        
        Real-time monitoring of Cohezion's evolutionary state.
        """
    )
    return


@app.cell
def _(go, random):
    def get_state_vector():
        # In a real impl, this would query SurrealDB or valid metrics
        return [
            random.uniform(0.7, 1.0),  # Coherence
            random.uniform(0.8, 1.0),  # Stability
            random.uniform(0.4, 0.9),  # Complexity
            random.uniform(0.5, 1.0),  # Velocity
            random.uniform(0.6, 0.95),  # Coverage
            random.uniform(0.7, 1.0),  # Coupling (Inv)
            random.uniform(0.6, 1.0),  # Clarity
            random.uniform(0.8, 1.0),  # Necessity
            random.uniform(0.3, 0.8),  # Novelty
            random.uniform(0.7, 1.0),  # Utility
            random.uniform(0.9, 1.0),  # Security
            random.uniform(0.5, 1.0),  # Spirit
        ]

    categories = [
        "Coherence",
        "Stability",
        "Complexity",
        "Velocity",
        "Coverage",
        "Coupling",
        "Clarity",
        "Necessity",
        "Novelty",
        "Utility",
        "Security",
        "Spirit",
    ]
    return categories, get_state_vector


@app.cell
def _(categories, get_state_vector, go, mo, time):
    # Reactive refresher
    refresh = mo.ui.refresh(label="Refresh Pulse", interval="2s")

    refresh

    # Generate data
    state = get_state_vector()

    fig = go.Figure()

    fig.add_trace(
        go.Scatterpolar(
            r=state,
            theta=categories,
            fill="toself",
            name="Current State",
            line_color="#00ff99",
            fillcolor="rgba(0, 255, 153, 0.2)",
        )
    )

    fig.add_trace(
        go.Scatterpolar(
            r=[0.9] * 12,
            theta=categories,
            name="Gold Standard",
            line_color="rgba(255, 215, 0, 0.5)",
            line_dash="dot",
        )
    )

    fig.update_layout(
        polar=dict(radialaxis=dict(visible=True, range=[0, 1])),
        showlegend=True,
        template="plotly_dark",
        margin=dict(l=40, r=40, t=40, b=40),
        height=500,
    )

    plot = mo.ui.plotly(fig)
    return fig, plot, refresh, state


@app.cell
def _(mo, plot):
    mo.vstack([plot])
    return


@app.cell
def _(mo, psutil):
    # System vitals
    mem = psutil.virtual_memory()
    cpu = psutil.cpu_percent()

    mo.md(
        f"""
        ### Active Defense Status
        - **CPU Load**: {cpu}%
        - **Memory Usage**: {mem.percent}% ({mem.used / 1024**3:.1f} / {mem.total / 1024**3:.1f} GB)
        - **Available**: {mem.available / 1024**3:.1f} GB
        """
    )
    return cpu, mem


if __name__ == "__main__":
    app.run()
