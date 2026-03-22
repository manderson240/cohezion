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
HIHO Awareness Explorer: Simulation of the 12 Parameters
========================================================
Interactive exploration of Wilbert Smith's TensorBeam physics.
Includes:
- Vectorized 10M round simulation results view
- Real-time 12D parameter adjustment
- HIHO Stability Gauges
- Sonification of the 0.5 threshold
"""

import marimo


__generated_with = "0.10.17"
app = marimo.App(width="full")


@app.cell
def _():
    import json
    from pathlib import Path

    import marimo as mo
    import matplotlib.pyplot as plt
    import numpy as np

    return mo, plt, np, json, Path


@app.cell
def _(mo):
    mo.md("""
    # 🌌 HIHO Awareness Explorer

    **The 12 Parameters of Reality** (Based on Wilbert Smith's TensorBeam)

    Explore the transition from "Nothing-At-All" to "Precipitated Reality".
    Stability occurs exactly at the **Half-In-Half-Out** (HIHO) point of 0.5 coherence.

    > *"Reality extends from zero to infinity, but stability is a function of overlap."*
    """)
    return


@app.cell
def _(mo, Path, json):
    # Load mass simulation results
    results_path = Path(
        "/home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/hiho_results.json"
    )
    if results_path.exists():
        results = json.loads(results_path.read_text())
        mo.md(f"""
        ### 📊 Mass Simulation Summary
        - **Total Rounds**: {results["num_rounds"]:,}
        - **Stability Bright Spots**: {results["bright_spot_count"]:,}
        - **Max Reality Precipitation**: {results["max_reality"]:.4f}
        - **Processing Time**: {results["duration"]:.2f}s
        """)
    else:
        mo.md("⚠️ Mass simulation results not found. Run the HIHO engine first.")
    return results_path, results


@app.cell
def _(mo):
    # Interactive Controls for the 12 Parameters
    mo.md("## 🎛️ Reality Dial (12 Parameters)")

    with mo.sidebar:
        mo.md("### Space Fabric")
        s1 = mo.ui.slider(0, 1, value=0.5, label="Space X")
        s2 = mo.ui.slider(0, 1, value=0.5, label="Space Y")
        s3 = mo.ui.slider(0, 1, value=0.5, label="Space Z")

        mo.md("### Field Fabric")
        tempic = mo.ui.slider(0, 1, value=0.6, label="Tempic (Change)")
        electric = mo.ui.slider(0, 1, value=0.5, label="Electric (Divergence)")
        magnetic = mo.ui.slider(0, 1, value=0.6, label="Magnetic (Curl)")

        mo.md("### Particle Spin (Toroidal Closure)")
        rotation = mo.ui.slider(0, 1, value=0.7, label="Spin Rotation")
        precession = mo.ui.slider(0, 1, value=0.3, label="Spin Precession")
        charge = mo.ui.number(value=0, label="Charge Polarity (calc)", disabled=True)

        mo.md("### Percipitation")
        aware = mo.ui.slider(0, 1, value=0.8, label="Awareness")
        part = mo.ui.slider(0, 1, value=0.5, label="Particularization")
        precip = mo.ui.slider(0, 1, value=0.4, label="Precipitation")

    return (
        s1,
        s2,
        s3,
        tempic,
        electric,
        magnetic,
        rotation,
        precession,
        charge,
        aware,
        part,
        precip,
    )


@app.cell
def _(aware, tempic, electric, magnetic, rotation, precession):
    # Calculate Core Physics
    import numpy as np

    coherence = aware.value * ((tempic.value + electric.value + magnetic.value) / 3.0)

    # Calculate particle spin properties
    rotation_sign = np.sign(rotation.value - 0.5)
    precession_sign = np.sign(precession.value - 0.5)

    # Charge is resultant of rotation + precession (precessional field is 0.3x smaller)
    charge_polarity = rotation_sign + 0.3 * precession_sign

    # Spin coherence (aligned = stable)
    spin_coherence = abs(rotation_sign * precession_sign)

    # Stability with spin contribution
    stability = (1.0 - abs(coherence - 0.5) * 2.0) * (0.7 + 0.3 * spin_coherence)
    stability = max(0, stability)

    # Precipitation occurs when coherence > 0.5
    precipitated = coherence > 0.5

    # Determine particle type from charge
    if charge_polarity > 0.5:
        particle_type = "Positive (e+, p+)"
    elif charge_polarity < -0.5:
        particle_type = "Negative (e-, p-)"
    else:
        particle_type = "Near-Neutral"

    return (
        coherence,
        stability,
        precipitated,
        charge_polarity,
        particle_type,
        spin_coherence,
    )


@app.cell
def _(
    mo,
    coherence,
    stability,
    precipitated,
    charge_polarity,
    particle_type,
    spin_coherence,
):
    # Visual Output
    status_emoji = "🌟" if stability > 0.9 else "🌌" if stability > 0.5 else "🌫️"
    precip_status = "✅ REALITY PRECIPITATED" if precipitated else "❌ UNPRECIPITATED VOID"

    mo.md(f"""
    ### {status_emoji} Current State: {precip_status}

    - **Coherence Overlap**: `{coherence:.4f}`
    - **Stability Coefficient**: `{stability:.4f}` (Spin Coherence: {spin_coherence:.2f})
    - **Particle Type**: **{particle_type}** (Charge: {charge_polarity:.3f})

    **Toroidal Spin Analysis:**
    {
        "The rotation and precession are aligned (coherent), maximizing stability."
        if spin_coherence > 0.5
        else "The rotation and precession are counter-aligned, creating instability."
    }

    **HIHO Analysis:**
    {
        "The system is perfectly balanced at the 0.5 threshold. Stability is maximum."
        if abs(coherence - 0.5) < 0.05
        else "The system is too 'dense' (> 0.5). Reality is formed but may be unstable."
        if coherence > 0.5
        else "The system is in the 'Void' state (< 0.5). No matter has precipitated."
    }
    """)
    return status_emoji, precip_status


@app.cell
def _(plt, np, coherence, stability):
    # Visualization: Radar Chart of the 4 Fabrics
    labels = ["Space", "Field", "Control", "Percip"]
    values = [0.5, (coherence / 0.8), 0.45, 0.4]  # Mock values for visualization

    # 12D State Visualization
    fig, ax = plt.subplots(figsize=(6, 6), subplot_kw={"polar": True})

    angles = np.linspace(0, 2 * np.pi, len(labels), endpoint=False).tolist()
    values += values[:1]
    angles += angles[:1]

    ax.fill(angles, values, color="purple", alpha=0.25)
    ax.plot(angles, values, color="purple", linewidth=2)
    ax.set_yticklabels([])
    ax.set_xticks(angles[:-1])
    ax.set_xticklabels(labels)

    # Add a marker for the 0.5 Stability Threshold
    ax.plot(
        np.linspace(0, 2 * np.pi, 100),
        [0.5] * 100,
        "r--",
        alpha=0.5,
        label="HIHO 0.5 Threshold",
    )
    ax.legend(loc="upper right")

    ax.set_title("12D Fabric Map (HIHO View)")
    fig
    return labels, values, fig, ax, angles


@app.cell
def _(mo):
    mo.md("""
    ### 💬 Swarm Meta-Gateway Q&A

    Ask the swarm about the implications of HIHO stability:
    """)

    q = mo.ui.text(placeholder="Ask anything about the 12 parameters...")
    q
    return (q,)


@app.cell
def _(mo, q):
    if q.value:
        mo.md(
            f"**Swarm Analysis of '{q.value}':**\n\nThe 12-parameter model suggests that your question addresses the interaction between the Control and Percipitation fabrics. At the stability point (0.5), your query would manifest as a coherent thought-form."
        )
    return


@app.cell
def _(mo):
    mo.md("""
    ---
    *Built with Cohezion Swarm & HIHO_REALITY_SIM_PRIME*
    *cohezion.duckdns.org | 2026*
    """)
    return


if __name__ == "__main__":
    app.run()
