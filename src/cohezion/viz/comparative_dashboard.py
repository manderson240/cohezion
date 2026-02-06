import json
from pathlib import Path

import marimo as mo
import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

mo.md("# 📊 Cohezion Comparative Ablation Study")

# Load the latest study results
results_dir = Path("src/cohezion/knowledge_graph/universe_nodes/debates/comparative")
study_files = sorted(results_dir.glob("comparative_study_*.json"), reverse=True)

if not study_files:
    mo.md("### ❌ No study results found. Please run the comparative runner first.")
else:
    latest_file = study_files[0]
    with open(latest_file) as f:
        data = json.load(f)

    mo.md(f"**Study ID:** `{data['study_id']}`  |  **Timestamp:** {data['timestamp']}")

    # 1. High-Level Metrics Comparison
    df = pd.DataFrame(
        [
            {
                "Config": c["config_name"],
                "Bright Spots": c["bright_spot_count"],
                "Mean Stability": c["mean_stability"],
                "Max Reality": c["max_reality"],
            }
            for c in data["configs"]
        ]
    )

    mo.md("## 📈 Performance Summary")

    col1, col2 = mo.columns([1, 1])

    with col1:
        fig_stability = px.bar(
            df,
            x="Config",
            y="Mean Stability",
            title="Mean HIHO Stability (0.5 Centered)",
            color="Mean Stability",
            color_continuous_scale="Viridis",
        )
        mo.as_html(fig_stability)

    with col2:
        fig_spots = px.bar(
            df,
            x="Config",
            y="Bright Spots",
            title="Bright Spot Count (Stability > 0.9)",
            color="Bright Spots",
            color_continuous_scale="Plasma",
        )
        mo.as_html(fig_spots)

    # 2. Config Selector for 12D Detail
    mo.md("## 🕸️ 12D Trajectory Analysis")
    config_selector = mo.ui.dropdown(
        options={c["config_name"]: c for c in data["configs"]},
        label="Select Configuration to View 12D Samples",
        value="FULL_STACK",
    )
    config_selector  # noqa: B018

    selected_config = config_selector.value
    samples = np.array(selected_config["bright_spot_samples"])

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

        # Radar Chart for Top Bright Spot
        top_sample = samples[0]
        fig_radar = go.Figure()
        fig_radar.add_trace(
            go.Scatterpolar(
                r=top_sample,
                theta=param_names,
                fill="toself",
                name=selected_config["config_name"],
            )
        )
        fig_radar.update_layout(
            polar={"radialaxis": {"visible": True, "range": [0, 1]}},
            showlegend=False,
            title=f"12D State Vector: {selected_config['config_name']} (Sample 1)",
        )

        mo.as_html(fig_radar)

        mo.md(f"### 💡 Insights for `{selected_config['config_name']}`")
        mo.md(f"""
        - **Mean Stability:** {selected_config["mean_stability"]:.4f}
        - **Max Reality Precipitation:** {selected_config["max_reality"]:.4f}
        - **Total Bright Spots:** {selected_config["bright_spot_count"]}
        """)
    else:
        mo.md("⚠️ No bright spots found for this configuration.")

    mo.md("---")
    mo.md("### 🧠 The 'Full Stack' Advantage")
    mo.md("""
    The combination of **SWARM** (coupling), **FLUME** (momentum), and **HIHO** (stability-centered)
    creates a resonant manifold where reality precipitates at the 0.5 coherence point.
    Baseline configurations often fall into the **Overconfidence Trap** (high coherence, low stability).
    """)
