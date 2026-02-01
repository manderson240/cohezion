import json
from pathlib import Path

import marimo as mo
import pandas as pd
import plotly.express as px

# Load results from the debates directory
DEBATE_DIR = Path("src/cohezion/knowledge_graph/universe_nodes/debates/hiho")


@mo.md
def header():
    return mo.md(
        "# 🌐 Cohezion HIHO Stability Dashboard\n### Recursive Consensus & Manifold Calibration"
    )


@mo.cache
def load_data():
    files = sorted(
        DEBATE_DIR.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True
    )
    if not files:
        return None
    with open(files[0]) as f:
        return json.load(f)


@mo.md
def dashboard(data=None):
    if data is None:
        data = load_data()
    if data is None:
        return mo.md("⚠️ No debate data found. Run `hiho_consensus_runner.py` first.")

    # Process Rounds Data
    rounds_df = pd.DataFrame(
        [
            {
                "Round": r["round"],
                "Coherence": r["coherence"],
                "Stability": r["stability"],
            }
            for r in data["rounds"]
        ]
    )

    # 1. Stability Trajectory
    fig_stable = px.line(
        rounds_df,
        x="Round",
        y=["Coherence", "Stability"],
        title="Recursive Stability Trajectory",
        markers=True,
        color_discrete_map={"Coherence": "#4ECDC4", "Stability": "#FF6B6B"},
    )
    fig_stable.add_hline(
        y=0.5,
        line_dash="dash",
        line_color="gold",
        annotation_text="HIHO Stability Point",
    )

    # 2. Calibration Heatmap (Mockup based on rounds)
    # We show drift from 0.5
    rounds_df["Drift"] = abs(rounds_df["Coherence"] - 0.5)
    fig_drift = px.bar(
        rounds_df,
        x="Round",
        y="Drift",
        title="Agent Drift (Distance from 0.5)",
        color="Drift",
        color_continuous_scale="RdYlGn_r",
    )

    return mo.vstack(
        [
            mo.md(f"**Mission ID**: {data['mission_id']}"),
            mo.md(f"**Topic**: {data['topic']}"),
            mo.columns([mo.as_html(fig_stable), mo.as_html(fig_drift)]),
            mo.md("### Final Synthesis"),
            mo.md(data["final_synthesis"]["synthesis"]),
        ]
    )


if __name__ == "__main__":
    mo.app().run()
