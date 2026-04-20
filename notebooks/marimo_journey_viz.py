import marimo

__generated_with = "0.1.0"
app = marimo.App(width="full")


@app.cell
def __():
    import marimo as mo
    import plotly.graph_objects as go
    import numpy as np
    import pandas as pd
    from sklearn.decomposition import PCA
    import asyncio
    from cohezion.storage.surreal_client import SurrealDBClient
    
    return PCA, SurrealDBClient, asyncio, go, mo, np, pd


@app.cell
def __(mo):
    mo.md("# 🌌 Agentic Journey Visualization")
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
    # Fetch recent trajectory nodes
    # Note: Using mock data if DB empty for demonstration
    raw_nodes = await client.query_trajectories("journey_alpha")
    
    if not raw_nodes:
        # Generate synthetic 12D trajectory for visualization
        n_steps = 50
        steps = np.linspace(0, 10, n_steps)
        # 12D state with convergence to 0.5
        state_12d = 0.5 + 0.4 * np.exp(-0.2 * steps[:, None]) * np.sin(steps[:, None] + np.random.normal(0, 0.1, (n_steps, 12)))
        data = []
        for i, s in enumerate(state_12d):
            data.append({
                "step": i,
                "coherence": 1.0 - np.mean(np.abs(s - 0.5)),
                "x": s[0], "y": s[1], "z": s[2],
                "vector": s.tolist()
            })
        df = pd.DataFrame(data)
    else:
        df = pd.DataFrame([n.dict() for n in raw_nodes])
    
    return df, raw_nodes


@app.cell
def __(df, go):
    # 3D PCA Projection (Mocking 256D -> 3D)
    # In production, we'd use the actual z_vectors from the DB
    
    fig = go.Figure()
    
    # 1. Plot 12D Trajectory (first 3 dims)
    fig.add_trace(go.Scatter3d(
        x=df['x'], y=df['y'], z=df['z'],
        mode='lines+markers',
        marker=dict(size=4, color=df['coherence'], colorscale='Viridis', opacity=0.8),
        line=dict(color='cyan', width=2),
        name="12D Journey (Axiomatic)"
    ))
    
    # 2. Add HIHO Attractor Point (0.5, 0.5, 0.5)
    fig.add_trace(go.Scatter3d(
        x=[0.5], y=[0.5], z=[0.5],
        mode='markers',
        marker=dict(size=10, color='red', symbol='diamond'),
        name="HIHO Attractor"
    ))
    
    fig.update_layout(
        title="12D Agentic Trajectory Projection",
        template="plotly_dark",
        margin=dict(l=0, r=0, b=0, t=40),
        scene=dict(
            xaxis_title='Spatial X',
            yaxis_title='Spatial Y',
            zaxis_title='Spatial Z'
        )
    )
    return fig,


@app.cell
def __(fig, mo):
    mo.plotly(fig)
    return


@app.cell
def __(mo):
    mo.md("## 🔊 Journey Sonification")
    return


@app.cell
def __(df, mo):
    # Display stability table
    mo.table(df[['step', 'coherence']].tail(10))
    return


if __name__ == "__main__":
    app.run()
