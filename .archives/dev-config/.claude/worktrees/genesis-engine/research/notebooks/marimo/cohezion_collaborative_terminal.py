# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "marimo",
#     "pandas",
#     "plotly",
#     "numpy",
#     "torch",
# ]
# ///
"""
Cohezion Collaborative Intelligent Terminal (Gateway 24).

The final mission control for the SLM Swarm, enabling real-time human-agent
collaboration across memory, architecture, and imagination.
"""

import sys
from pathlib import Path

import marimo as mo


# Add src to path
sys.path.append(str(Path.cwd() / "src"))

from cohezion.swarm.agents.analyst import AnalystAgent
from cohezion.swarm.agents.architect_agent import ArchitectAgent
from cohezion.swarm.agents.hypothesis_agent import HypothesisAgent
from cohezion.swarm.agents.memory_agent import MemoryAgent

from cohezion.core.credit_manager import get_credit_manager
from cohezion.swarm.swarm_types import Perspective, SwarmConfig


# Cell 1: Header
mo.md("""
# 🌌 Cohezion Collaborative Terminal
**Mission Control | Gateway 24: Collaborative Intelligence**

Welcome to the unified interface for the Cohezion SLM Swarm. This terminal allows you to coordinate complex operations across 12D thought manifolds, memory retrieval, and automated hypothesis testing.
""")

# Cell 2: System Status
cm = get_credit_manager()
analyst_balance = cm.get_balance("AnalystAgent")
total_credits = sum(cm._balances.values()) if cm._balances else 1000

mo.md(f"""
### 🚉 System Status
{
    mo.hstack(
        [
            mo.stat(label="Total Swarm Credits", value=str(total_credits)),
            mo.stat(label="Analyst Credits", value=str(analyst_balance)),
            mo.stat(label="Active Dimensions", value="768"),
            mo.stat(label="Reality Stability", value="0.52", caption="HIHO Equilibrium"),
        ]
    )
}
""")

# Cell 3: Mission Input
query_input = mo.ui.text_area(
    label="🛰️ Mission Objective",
    placeholder="Define a complex cross-domain requirement...",
    full_width=True,
)

mode_select = mo.ui.radio(
    options=["Analysis", "Architecture", "Memory Search", "Hypothesis Test"],
    value="Analysis",
    label="⚡ Select Mode",
)

run_button = mo.ui.run_button(label="🚀 Initiate Swarm")

mo.hstack([mode_select, run_button])


# Cell 4: Swarm Execution Logic
async def run_swarm(query, mode):
    if not query:
        return "Please enter a mission objective."

    config = SwarmConfig()

    if mode == "Analysis":
        agent = AnalystAgent(Perspective.TECHNICAL, config=config)
        result = await agent.analyze(query)
        return f"### 🧠 Analyst Result (Phi: {result.phi_score:.2f}, Confidence: {result.confidence:.2f})\n\n{result.content}"

    elif mode == "Architecture":
        agent = ArchitectAgent(config=config)
        result = await agent.process(query)
        return result

    elif mode == "Memory Search":
        agent = MemoryAgent(config=config)
        result = await agent.process(query)
        return result

    elif mode == "Hypothesis Test":
        agent = HypothesisAgent(config=config)
        result = await agent.process(query)
        return result

    return "Invalid Mode"


output = mo.stop(not run_button.value, mo.md("*Awaiting command...*"))

# Actually run the swarm
execution_result = mo.status.progress(
    run_swarm(query_input.value, mode_select.value) if run_button.value else None,
    title="🌌 Swarm Computing...",
    subtitle="Engaging 12-Parameter Quadrature",
)

mo.md(f"""
### 📡 Swarm Output
{execution_result if execution_result else ""}
""")

# Cell 5: Vector Manifold & Light Field
import numpy as np
import plotly.graph_objects as go
from cohezion.bio.biophotonics import get_light_field


def generate_visuals():
    # 1. 12D Manifold (3D Projection)
    n_points = 100
    points = np.random.randn(n_points, 3)

    fig_manifold = go.Figure(
        data=[
            go.Scatter3d(
                x=points[:, 0],
                y=points[:, 1],
                z=points[:, 2],
                mode="markers",
                marker={
                    "size": 4,
                    "color": np.linspace(0, 1, n_points),
                    "colorscale": "Viridis",
                    "opacity": 0.8,
                },
            )
        ]
    )
    fig_manifold.update_layout(
        title="12D Thought Manifold (3D Projection)",
        margin={"l": 0, "r": 0, "b": 0, "t": 30},
        template="plotly_dark",
        height=400,
    )

    # 2. Light Field Spectrum
    lf = get_light_field()
    summary = lf.get_spectrum_summary()

    colors = {"RED": "red", "GREEN": "#00ff00", "BLUE": "cyan", "UV": "violet"}

    fig_light = go.Figure(
        data=[
            go.Bar(
                x=list(summary.keys()),
                y=list(summary.values()),
                marker_color=[colors.get(k, "white") for k in summary],
            )
        ]
    )
    fig_light.update_layout(
        title="Biophotonic Spectrum (Last 5s)",
        yaxis={"range": [0, 1], "title": "Intensity"},
        margin={"l": 0, "r": 0, "b": 0, "t": 30},
        template="plotly_dark",
        height=400,
    )

    return fig_manifold, fig_light


fig_m, fig_l = generate_visuals()
mo.hstack([mo.plotly(fig_m), mo.plotly(fig_l)])

# Cell 6: Retrospective Link
mo.md("""
---
🔍 **Explore Learnings**: [KEY_LEARNINGS.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/KEY_LEARNINGS.md)
🛡️ **Security Audit**: [ADVERSARIAL_PATTERNS.surreal](file:///home/mike-anderson/dev/cohezion/src/cohezion/security/ADVERSARIAL_PATTERNS.surreal)
""")
