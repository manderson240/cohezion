#!/usr/bin/env python3
"""
Plotly Gateway Progression Plot
Modern interactive replacement for matplotlib version
"""

import json
from pathlib import Path

import plotly.graph_objects as go


# Load overnight data
data_path = Path("/home/mike-anderson/dev/cohezion/data/overnight/final_report.json")
data = json.loads(data_path.read_text())

discoveries = data["discoveries"]

# Extract gateway progression
gateways = [d["gateway"] for d in discoveries]
iterations = [d["iteration"] for d in discoveries]
stabilities = [d["mean_stability"] for d in discoveries]
bright_spots = [d["bright_spots"] for d in discoveries]

# Calculate thresholds
thresholds = [0.950 + (g - 43) * 0.001 for g in gateways]

# Create interactive plot
fig = go.Figure()

# Threshold line
fig.add_trace(
    go.Scatter(
        x=gateways,
        y=thresholds,
        mode="lines",
        name="Required Threshold",
        line={"color": "#e74c3c", "width": 3, "dash": "dash"},
        hovertemplate="Gateway %{x}<br>Threshold: %{y:.4f}<extra></extra>",
    )
)

# Achievement scatter
fig.add_trace(
    go.Scatter(
        x=gateways,
        y=stabilities,
        mode="markers",
        name="Achieved Stability",
        marker={
            "size": 8,
            "color": bright_spots,
            "colorscale": "Viridis",
            "showscale": True,
            "colorbar": {"title": "Bright Spots"},
            "line": {"width": 1, "color": "white"},
        },
        hovertemplate="<b>Gateway %{x}</b><br>"
        + "Stability: %{y:.4f}<br>"
        + "Bright Spots: %{marker.color:,}<br>"
        + "<extra></extra>",
    )
)

# Layout
fig.update_layout(
    title={
        "text": "Gateway Progression: Infinite Advancement System",
        "font": {"size": 20, "family": "Arial Black"},
    },
    xaxis={
        "title": "Gateway Number",
        "gridcolor": "rgba(128,128,128,0.2)",
        "showgrid": True,
    },
    yaxis={
        "title": "Mean Stability",
        "gridcolor": "rgba(128,128,128,0.2)",
        "showgrid": True,
        "range": [0.84, 0.96],
    },
    hovermode="closest",
    plot_bgcolor="#f8f9fa",
    paper_bgcolor="white",
    font={"family": "Arial", "size": 12},
    legend={
        "orientation": "h",
        "yanchor": "bottom",
        "y": 1.02,
        "xanchor": "right",
        "x": 1,
    },
    height=600,
    width=1000,
)

# Save to artifacts
output_dir = Path(
    "/home/mike-anderson/.gemini/antigravity/brain/1b98adc2-8dce-436b-bac3-d27890e7ce04/assets"
)
output_dir.mkdir(parents=True, exist_ok=True)

# HTML version (interactive)
fig.write_html(str(output_dir / "gateway_progression_interactive.html"))

# Static PNG
fig.write_image(str(output_dir / "gateway_progression_plotly.png"), width=1000, height=600, scale=2)

print(f"✅ Gateway progression plot saved to {output_dir}")
print("   - Interactive: gateway_progression_interactive.html")
print("   - Static: gateway_progression_plotly.png")
