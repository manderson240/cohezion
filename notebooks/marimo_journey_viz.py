import marimo


__generated_with = "0.1.0"
app = marimo.App(width="full")


@app.cell
def __():
    import asyncio

    import marimo as mo
    import numpy as np
    import pandas as pd
    import plotly.graph_objects as go
    from sklearn.decomposition import PCA

    from cohezion.storage.surreal_client import SurrealDBClient

    return PCA, SurrealDBClient, asyncio, go, mo, np, pd


@app.cell
def __(mo):
    mo.md("# 🌌 Holographic Agentic Journey Dashboard")
    return


@app.cell
async def __(SurrealDBClient):
    # Connect to local SurrealDB
    client = SurrealDBClient()
    try:
        await client.connect()
        db_status = "Connected ✅"
    except Exception as e:
        db_status = f"Disconnected ❌ ({e})"
    return client, db_status


@app.cell
def __(db_status, mo):
    mo.stat(value=db_status, label="SurrealDB Status")
    return


@app.cell
async def __(client):
    # Fetch holographic record (correlated journey and universe shifts)
    holo_record = await client.query_holographic_record("journey_alpha")

    # 1. Process Journey Data
    if not holo_record["journey"]:
        # Generate synthetic 12D journey
        n_steps = 50
        steps = np.linspace(0, 10, n_steps)
        # Latent intent (Cyan)
        latent_12d = 0.5 + 0.3 * np.exp(-0.1 * steps[:, None]) * np.cos(steps[:, None])
        df_j = pd.DataFrame(
            [
                {
                    "step": i,
                    "x": s[0],
                    "y": s[1],
                    "z": s[2],
                    "coherence": 1.0 - np.mean(np.abs(s - 0.5)),
                    "type": "latent",
                }
                for i, s in enumerate(latent_12d)
            ]
        )
    else:
        df_j = pd.DataFrame(holo_record["journey"])

    # 2. Process Universe Shift Data
    if not holo_record["universe_shifts"]:
        # Generate synthetic universe shifts (Magenta)
        # Universe reacts to intent with a delay and damping
        universe_12d = 0.5 + 0.4 * np.exp(-0.15 * steps[:, None]) * np.sin(steps[:, None] - 0.5)
        df_u = pd.DataFrame(
            [
                {
                    "step": i,
                    "x": s[0],
                    "y": s[1],
                    "z": s[2],
                    "coherence": 1.0 - np.mean(np.abs(s - 0.5)),
                    "shift": 0.05 + 0.1 * np.exp(-0.2 * i),
                    "type": "axiomatic",
                }
                for i, s in enumerate(universe_12d)
            ]
        )
    else:
        df_u = pd.DataFrame(holo_record["universe_shifts"])

    return df_j, df_u


@app.cell
def __(df_j, df_u, go):
    # 3D Holographic Visualization: Ghost Trajectories & Manifold Pressure

    fig = go.Figure()

    # 1. Plot Agent Intent (Ghost Trajectory - Semi-transparent Cyan)
    fig.add_trace(
        go.Scatter3d(
            x=df_j["x"],
            y=df_j["y"],
            z=df_j["z"],
            mode="lines",
            line=dict(color="cyan", width=4, dash="dash"),
            opacity=0.3,
            name="Agent Intent (Latent Ghost)",
        )
    )

    # 2. Plot Axiomatic Reality (Solid trajectory - Coherence colored)
    fig.add_trace(
        go.Scatter3d(
            x=df_u["x"],
            y=df_u["y"],
            z=df_u["z"],
            mode="lines+markers",
            marker=dict(
                size=5,
                color=df_u["coherence"],
                colorscale="Viridis",
                showscale=True,
                colorbar=dict(title="Coherence"),
            ),
            line=dict(color="magenta", width=3),
            name="Physical Reality (Axiomatic)",
        )
    )

    # 3. Pressure Heatmap (Visualize where intent 'pushes' reality)
    # We add markers where stability shift is high
    high_pressure = df_u[df_u["shift"] > 0.08]
    if not high_pressure.empty:
        fig.add_trace(
            go.Scatter3d(
                x=high_pressure["x"],
                y=high_pressure["y"],
                z=high_pressure["z"],
                mode="markers",
                marker=dict(size=12, color="red", opacity=0.5, symbol="diamond"),
                name="Manifold Pressure Spike",
            )
        )

    # 4. Add HIHO Attractor Point (0.5, 0.5, 0.5)
    fig.add_trace(
        go.Scatter3d(
            x=[0.5],
            y=[0.5],
            z=[0.5],
            mode="markers",
            marker=dict(size=15, color="white", symbol="x"),
            name="HIHO Attractor (0.5)",
        )
    )

    fig.update_layout(
        title="Holographic Record: Physics/Intent Correlation",
        template="plotly_dark",
        margin=dict(l=0, r=0, b=0, t=40),
        scene=dict(xaxis_title="Spatial X", yaxis_title="Spatial Y", zaxis_title="Spatial Z"),
    )
    return (fig,)


@app.cell
def __(fig, mo):
    mo.plotly(fig)
    return


@app.cell
def __(df_u, mo):
    # Dissonance Sonification Monitor
    curr_coherence = df_u.iloc[-1]["coherence"]
    delta = abs(curr_coherence - 0.5)

    is_dissonant = delta > 0.1

    status_text = "🔊 RESONANT (STABLE)" if not is_dissonant else "📢 DISSONANT (MANIFOLD DRIFT)"
    color = "cyan" if not is_dissonant else "red"

    mo.md(f"### Current Audio State: <span style='color: {color}'>{status_text}</span>")
    return delta, is_dissonant


@app.cell
def __(df_j, df_u, mo):
    # Combined Stats Table
    mo.md("### Trajectory Checksum")
    mo.table(pd.concat([df_j.tail(5), df_u.tail(5)]))
    return


if __name__ == "__main__":
    app.run()
