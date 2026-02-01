import json
from pathlib import Path

import marimo as mo
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from sklearn.decomposition import PCA

mo.md("# 🌌 Cohezion Multiverse Scenario Explorer")

# Load the latest multiverse results
results_dir = Path("src/cohezion/knowledge_graph/universe_nodes/simulations")
study_files = sorted(results_dir.glob("multiverse_*.json"), reverse=True)

if not study_files:
    mo.md(
        "### ❌ No multiverse results found. Please run the scenario mission runner first."
    )
else:
    latest_file = study_files[0]
    with open(latest_file) as f:
        data = json.load(f)

    mo.md(
        f"**Mission ID:** `{data['mission_id']}`  |  **Timestamp:** {data['timestamp']}"
    )

    # 1. Cross-Universe Stability Comparison
    scenarios_df = pd.DataFrame(
        [
            {
                "Universe": s["scenario_name"],
                "Mean Stability": s["mean_stability"],
                "Bright Spots": s["bright_spot_count"],
                "Max Reality": s["max_reality"],
                "Momentum": s["params"]["momentum"],
                "Coupling": s["params"]["coupling"],
            }
            for s in data["scenarios"]
        ]
    )

    mo.md("## 📊 Universe Stability Gradient")

    fig_bubbles = px.scatter(
        scenarios_df,
        x="Mean Stability",
        y="Max Reality",
        size="Bright Spots",
        color="Universe",
        hover_name="Universe",
        title="Stability vs Reality (Bubble Size = Bright Spots)",
        template="plotly_dark",
    )
    mo.as_html(fig_bubbles)

    # 2. PCA Cloud Projection
    mo.md("## ☁️ 12D Latent Cloud (PCA)")

    # Collect samples from all universes
    all_samples = []
    labels = []
    for s in data["scenarios"]:
        samples = np.array(s["bright_spot_samples"])
        if samples.size > 0:
            all_samples.append(samples)
            labels.extend([s["scenario_name"]] * len(samples))

    if all_samples:
        X = np.concatenate(all_samples)
        pca = PCA(n_components=3)
        X_pca = pca.fit_transform(X)

        pca_df = pd.DataFrame(X_pca, columns=["PC1", "PC2", "PC3"])
        pca_df["Universe"] = labels

        fig_pca = px.scatter_3d(
            pca_df,
            x="PC1",
            y="PC2",
            z="PC3",
            color="Universe",
            title="Top 3 Principal Components of Bright Spot States",
            opacity=0.7,
            template="plotly_dark",
        )
        mo.as_html(fig_pca)
    else:
        mo.md("⚠️ No bright spot data available for PCA projection.")

    # 3. Interactive Archetype Viewer
    mo.md("## 📽️ Archetype Deep Dive")
    universe_selector = mo.ui.dropdown(
        options={s["scenario_name"]: s for s in data["scenarios"]},
        label="Select Universe Archetype",
        value="Fractal_Nexus",
    )
    universe_selector  # noqa: B018

    selected = universe_selector.value

    # Archetype Visualization
    ARCHETYPE_IMAGES = {
        "The_Void": "/home/mike-anderson/.gemini/antigravity/brain/50ca8f0d-c9b3-4c86-915c-865a8abbd5e3/the_void_archetype_1769027705303.png",
        "Resonant_Lattice": "/home/mike-anderson/.gemini/antigravity/brain/50ca8f0d-c9b3-4c86-915c-865a8abbd5e3/resonant_lattice_archetype_1769027720759.png",
        "The_Glitch": "/home/mike-anderson/.gemini/antigravity/brain/50ca8f0d-c9b3-4c86-915c-865a8abbd5e3/the_glitch_archetype_1769027737704.png",
        "Fractal_Nexus": "/home/mike-anderson/.gemini/antigravity/brain/50ca8f0d-c9b3-4c86-915c-865a8abbd5e3/fractal_nexus_archetype_1769027752892.png",
    }

    img_col, stats_col = mo.columns([1, 1])

    with img_col:
        img_path = ARCHETYPE_IMAGES.get(selected["scenario_name"], "")
        if img_path:
            mo.md(f"![{selected['scenario_name']}]({img_path})")

    with stats_col:
        mo.md(f"### 🛡️ Parameters for `{selected['scenario_name']}`")
        mo.md(f"""
        - **Momentum:** {selected['params']['momentum']}
        - **Coupling:** {selected['params']['coupling']}
        - **HIHO Target:** {selected['params']['hiho_target']}
        - **Entropy (Drift):** {selected['params']['entropy']}

        **Results:**
        - **Mean Stability:** {selected['mean_stability']:.4f}
        - **Bright Spots:** {selected['bright_spot_count']}
        """)

    # Radar Chart
    samples = np.array(selected["bright_spot_samples"])
    if samples.size > 0:
        param_names = [
            "Awareness",
            "Space_1",
            "Space_2",
            "Space_3",
            "Tempic",
            "Electric",
            "Magnetic",
            "Spin_Rotation",
            "Spin_Precession",
            "Charge_Polarity",
            "Particularization",
            "Precipitation",
        ]
        fig_radar = go.Figure()
        fig_radar.add_trace(
            go.Scatterpolar(
                r=samples[0],
                theta=param_names,
                fill="toself",
                name=selected["scenario_name"],
            )
        )
        fig_radar.update_layout(
            polar={"radialaxis": {"visible": True, "range": [0, 1]}},
            template="plotly_dark",
            title="Typical 12D Bright Spot Configuration",
        )
        mo.as_html(fig_radar)

    mo.md("---")
    mo.md("### 🧠 Process Insight")
    mo.md("""
    Comparing these clusters allows us to identify 'Universal Bridges'—latent paths that
    remain stable across different physical constants. This is the foundation for
    **Cross-Domain Generalization** in the Cohezion swarm.
    """)
