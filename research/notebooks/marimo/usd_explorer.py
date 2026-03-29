# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "numpy",
#     "plotly",
#     "pandas",
# ]
# ///
"""
USD Explorer - Interactive Itonic Cluster Simulation
=====================================================
Visualize Matsumoto's Underwater Spark Discharge method
for generating itonic clusters (micro ball lightning).

Uses HIHO framework: Stability at 0.5 coherence threshold.
"""

import marimo


__generated_with = "0.19.4"
app = marimo.App(width="full")


@app.cell
def _():
    import marimo as mo
    import numpy as np
    import plotly.express as px
    import plotly.graph_objects as go
    from plotly.subplots import make_subplots

    return mo, np, go, px, make_subplots


@app.cell
def _(mo):
    mo.md("""
    # ⚡ USD Explorer: Itonic Cluster Generator

    *Interactive simulation of Matsumoto's Underwater Spark Discharge method*

    ---

    ### 🏠 Think of it like...
    Imagine dropping a tiny lightning bolt into water. The resulting plasma bubble
    can organize electrons into stable clusters—even though electrons normally repel each other!
    This happens at the **HIHO sweet spot (0.5 coherence)**.

    ---

    **Adjust the sliders below to control the spark parameters:**
    """)


@app.cell
def _(mo):
    # Control sliders
    voltage = mo.ui.slider(
        start=5, stop=20, step=1, value=10, label="⚡ Voltage (kV)", show_value=True
    )

    pulse_duration = mo.ui.slider(
        start=10, stop=500, step=10, value=100, label="⏱️ Pulse Duration (μs)", show_value=True
    )

    num_sparks = mo.ui.slider(
        start=10, stop=200, step=10, value=50, label="🔢 Number of Sparks", show_value=True
    )

    mo.vstack([mo.hstack([voltage, pulse_duration], justify="start", gap=2), num_sparks])
    return voltage, pulse_duration, num_sparks


@app.cell
def _(mo, np, voltage, pulse_duration, num_sparks):
    # USD Simulation Core (simplified from usd_simulator.py)
    HIHO_THRESHOLD = 0.5

    def simulate_spark(voltage_kv, pulse_us):
        """Simulate single spark and return cluster properties."""
        voltage_v = voltage_kv * 1000
        pulse_s = pulse_us * 1e-6
        conductivity = 0.05

        # Energy calculation
        resistance = 1.0 / (conductivity * 0.01)
        energy_j = (voltage_v**2) * pulse_s / resistance

        # Plasma bubble
        bubble_radius = (energy_j / 100) ** 0.33
        electron_density = 1e20 * (energy_j / 10)
        num_electrons = int(electron_density * (bubble_radius / 10) ** 3)

        # FIXED: Coherence depends on energy!
        # Higher voltage + longer pulse = higher energy = better coherence
        # Normalize energy: at max settings (20kV, 500μs), energy should give ~0.6 coherence on average
        max_energy = (20000**2) * (500e-6) / resistance  # Max possible energy
        energy_ratio = energy_j / max_energy  # 0 to 1

        # Base coherence increases with energy, plus random variation
        # At max energy: mean ~0.55 (above threshold)
        # At min energy: mean ~0.25 (well below threshold)
        base_coherence = 0.2 + 0.4 * energy_ratio  # Range: 0.2 to 0.6
        noise = np.random.normal(0, 0.1)  # Random fluctuation
        coherence = np.clip(base_coherence + noise, 0, 1)

        # Cluster formation at HIHO threshold
        formed = coherence >= HIHO_THRESHOLD
        lifetime_us = 100 / (1 + abs(coherence - 0.5) * 100) if formed else 0
        radius_nm = bubble_radius * 1e6 * coherence if formed else 0

        return {
            "formed": formed,
            "coherence": coherence,
            "num_electrons": num_electrons,
            "radius_nm": radius_nm,
            "lifetime_us": lifetime_us,
            "energy_j": energy_j,
        }

    # Run simulations
    results = [simulate_spark(voltage.value, pulse_duration.value) for _ in range(num_sparks.value)]

    formed_count = sum(1 for r in results if r["formed"])
    success_rate = formed_count / len(results) * 100

    coherences = [r["coherence"] for r in results]
    lifetimes = [r["lifetime_us"] for r in results if r["formed"]]
    radii = [r["radius_nm"] for r in results if r["formed"]]

    mean_lifetime = np.mean(lifetimes) if lifetimes else 0
    mean_coherence = np.mean(coherences) if coherences else 0

    mo.md(f"""
    ## 📊 Simulation Results

    | Metric | Value |
    |--------|-------|
    | ⚡ Sparks Generated | {num_sparks.value} |
    | ✅ Clusters Formed | {formed_count} |
    | 📈 Success Rate | **{success_rate:.1f}%** |
    | 🎯 Mean Coherence | {mean_coherence:.4f} |
    | ⏱️ Mean Lifetime | {mean_lifetime:.2f} μs |

    > **HIHO Threshold: 0.5** — Clusters only form when coherence reaches this sweet spot!
    """)
    return results, coherences, lifetimes, radii, success_rate, formed_count, HIHO_THRESHOLD


@app.cell
def _(mo, np, go, coherences, HIHO_THRESHOLD):
    mo.md("### 📈 Coherence Distribution")

    # Histogram of coherence values
    fig_hist = go.Figure()

    fig_hist.add_trace(
        go.Histogram(x=coherences, nbinsx=30, marker_color="#4ECDC4", opacity=0.8, name="Coherence")
    )

    # Add HIHO threshold line
    fig_hist.add_vline(
        x=HIHO_THRESHOLD,
        line_dash="dash",
        line_color="gold",
        annotation_text="HIHO Threshold (0.5)",
        annotation_position="top right",
    )

    fig_hist.update_layout(
        title="Electron Coherence Distribution",
        xaxis_title="Coherence",
        yaxis_title="Count",
        template="plotly_dark",
        height=400,
    )

    fig_hist
    return (fig_hist,)


@app.cell
def _(mo, np, go, make_subplots, results):
    mo.md("### 🔬 Cluster Properties")

    # Filter to formed clusters only
    formed = [r for r in results if r["formed"]]

    if len(formed) > 0:
        fig_props = make_subplots(
            rows=1, cols=2, subplot_titles=["Lifetime vs Coherence", "Radius vs Energy"]
        )

        # Lifetime vs Coherence
        fig_props.add_trace(
            go.Scatter(
                x=[r["coherence"] for r in formed],
                y=[r["lifetime_us"] for r in formed],
                mode="markers",
                marker=dict(
                    size=10,
                    color=[r["coherence"] for r in formed],
                    colorscale="Viridis",
                    showscale=True,
                    colorbar=dict(title="Coherence", x=0.45),
                ),
                name="Clusters",
            ),
            row=1,
            col=1,
        )

        # Radius vs Energy
        fig_props.add_trace(
            go.Scatter(
                x=[r["energy_j"] for r in formed],
                y=[r["radius_nm"] for r in formed],
                mode="markers",
                marker=dict(size=10, color="#FF6B6B"),
                name="Size",
                showlegend=False,
            ),
            row=1,
            col=2,
        )

        fig_props.update_layout(template="plotly_dark", height=400, showlegend=False)
        fig_props.update_xaxes(title_text="Coherence", row=1, col=1)
        fig_props.update_yaxes(title_text="Lifetime (μs)", row=1, col=1)
        fig_props.update_xaxes(title_text="Energy (J)", row=1, col=2)
        fig_props.update_yaxes(title_text="Radius (nm)", row=1, col=2)

        fig_props
    else:
        mo.md("*No clusters formed yet. Try increasing voltage or pulse duration!*")
    return (formed,)


@app.cell
def _(mo):
    mo.md("""
    ---

    ## 🧪 How It Works: The Matsumoto Method

    **Step 1: Spark Discharge**
    - High voltage (5-20 kV) creates spark through water
    - Plasma bubble forms instantaneously

    **Step 2: Electron Clustering**
    - Despite Coulomb repulsion, electrons can cluster
    - Electromagnetic force is 10⁴⁰ stronger than gravity!
    - HIHO coherence enables this "impossible" clustering

    **Step 3: Itonic Cluster Formation**
    - At 0.5 coherence (HIHO threshold), stability emerges
    - Cluster becomes self-sustaining
    - Can persist for microseconds to seconds

    ---

    ### 🌍 Why It Matters

    - **Clean Energy**: Potential pathway to cold fusion (LENR)
    - **Novel Materials**: Electron clusters with unusual properties
    - **Fundamental Physics**: Challenges our understanding of charge clustering

    > 👉 **The key insight**: At exactly 50% coherence, the "impossible" becomes stable.
    """)


@app.cell
def _(mo):
    mo.md("""
    ---

    ## 📖 References

    - Matsumoto, T. (1989-1999) - Underwater spark discharge experiments
    - Ken Shoulders (1996) - EVO (Exotic Vacuum Objects) research
    - HIHO Reality framework - Half-In-Half-Out stability principle

    ---

    *Built with Cohezion Swarm | FLUME Methodology | 2026*
    """)


if __name__ == "__main__":
    app.run()
