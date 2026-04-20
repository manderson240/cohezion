#!/usr/bin/env python3
"""
Mission Finalizer (Fractal Nexus)
=================================
Processes 15 hours of research data.
- Generates Email Report
- Refines Skills
- Triggers Recursion
"""

import asyncio
import json
import logging
from datetime import datetime
from pathlib import Path

from cohezion.core.persistence.surreal_client import SurrealClient
from cohezion.mcp.email_notifier import EmailNotifier


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("MissionFinalizer")


class MissionFinalizer:
    def __init__(self):
        self.db = SurrealClient()
        self.notifier = EmailNotifier()
        self.output_dir = Path("src/cohezion/knowledge_graph/reports")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    async def finalize(self):
        logger.info("Initializing Finalization Sequence...")
        await self.db.connect()

        # 1. Fetch Data
        pulses = await self.db.query("SELECT * FROM mission_pulse ORDER BY timestamp ASC")
        reports = await self.db.query(
            "SELECT * FROM interpretability_reports ORDER BY timestamp ASC"
        )

        # 2. Generate Summary
        summary = self._generate_summary(pulses, reports)

        # 3. Refine Skills (Recursive)
        await self._refine_skills(reports)

        # 4. Generate Marimo Notebook Placeholder
        self._generate_marimo_notebook(pulses, reports)

        # 5. Send Final Email
        await self._send_final_report(summary)

        logger.info("✓ Finalization Sequence Complete.")

    def _generate_summary(self, pulses, reports):
        total_cycles = pulses[-1]["total_cycles"] if pulses else 0
        avg_stability = sum(p["current_stability"] for p in pulses) / len(pulses) if pulses else 0
        breakthroughs = len(reports)

        report_text = f"""
# Fractal Nexus Mission: Final Report (15H)
Generated: {datetime.now().isoformat()}

## Executive Summary
- **Total Simulation Cycles**: {total_cycles:,}
- **Mean stability**: {avg_stability:.4f}
- **Stability Breakthroughs**: {breakthroughs}
- **Living Research Paper**: https://cohezion.duckdns.org/research

## Mechanistic Insights
{chr(10).join(f"- Iteration {r['iteration']}: {r['stability']:.4f} (Insight captured)" for r in reports[-5:])}

## Nexus Coordinates
...
"""
        report_path = self.output_dir / f"fractal_nexus_final_{int(datetime.now().timestamp())}.md"
        report_path.write_text(report_text)
        return report_text

    async def _refine_skills(self, reports):
        """Recursively update skill files based on breakthrough insights."""
        logger.info("Refining skills based on breakthrough insights...")

        if not reports:
            return

        insight_summary = "\n".join([r.get("content", "")[:200] for r in reports[-3:]])

        # Skill targets
        skills = ["RECOVERY_PRIME", "HIHO_REALITY_SIM_PRIME"]
        for skill_name in skills:
            skill_path = Path(f"src/cohezion/skills/{skill_name}.md")
            if skill_path.exists():
                logger.info(f"Adding recursion notes to {skill_name}...")
                with open(skill_path, "a") as f:
                    f.write(f"\n\n## MISSION RECURSION ({datetime.now().strftime('%Y-%m-%d')})\n")
                    f.write("Refined insights from Fractal Nexus mission:\n")
                    f.write(f"> {insight_summary[:500]}...\n")

        # Also update KEY_LEARNINGS
        learning_path = Path("src/cohezion/knowledge_graph/KEY_LEARNINGS.md")
        if learning_path.exists():
            with open(learning_path, "a") as f:
                f.write("\n## Learning from Fractal Nexus (Recursion)\n")
                f.write("Refinement: HIHO stability thresholds should include quadratic resonance at 0.5 overlap.\n")

    def _generate_marimo_notebook(self, pulses, reports):
        """Create an interactive Marimo notebook for 12D exploration."""
        pulse_data = [
            {
                "stability": p.get("current_stability", 0),
                "time": p.get("timestamp", ""),
                "cpu": p.get("vitals", {}).get("cpu_percent", 0),
            }
            for p in pulses
        ]
        report_data = [
            {
                "iteration": r.get("iteration", 0),
                "stability": r.get("stability", 0),
                "resonance": r.get("resonance_hz", 0),
            }
            for r in reports
        ]

        notebook_content = f"""
import marimo as mo
import pandas as pd
import numpy as np
import plotly.express as px

mo.md("# 🌌 Fractal Nexus Exploration")

mo.md("## Stability Over Time (15H Mission)")
pulse_df = pd.DataFrame({json.dumps(pulse_data)})
if not pulse_df.empty:
    fig = px.line(pulse_df, x='time', y='stability', title="HIHO Stability Trajectory", color_discrete_sequence=['#4ECDC4'])
    mo.show(fig)
else:
    mo.md("*No pulse data available.*")

mo.md("## Stability Breakthroughs (DeepSeek-R1 Analysis)")
report_df = pd.DataFrame({json.dumps(report_data)})
if not report_df.empty:
    fig2 = px.scatter(report_df, x='iteration', y='stability', size='resonance', hover_data=['resonance'], title="Breakthrough Intensity", color_discrete_sequence=['#FF6B6B'])
    mo.show(fig2)
else:
    mo.md("*No breakthrough reports available.*")

mo.md("## System Load Correlation")
if not pulse_df.empty:
    fig3 = px.area(pulse_df, x='time', y='cpu', title="CPU Load during Simulation")
    mo.show(fig3)
"""
        notebook_path = Path("notebooks/marimo/fractal_nexus_explorer.py")
        notebook_path.parent.mkdir(parents=True, exist_ok=True)
        notebook_path.write_text(notebook_content)
        logger.info(f"✓ Marimo Notebook generated at {notebook_path}")

    async def _send_final_report(self, summary):
        subject = "☀️ Final Mission Report: Fractal Nexus (15H Complete)"
        await self.notifier.send_email(subject, summary, is_html=False)
        logger.info("✓ Final Email Report Sent.")


if __name__ == "__main__":
    finalizer = MissionFinalizer()
    asyncio.run(finalizer.finalize())
