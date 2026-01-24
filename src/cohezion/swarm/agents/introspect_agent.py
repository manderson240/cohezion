import logging
import asyncio
import time
from pathlib import Path
from cohezion.swarm.agents.sovereign_agent import SovereignAgent
from cohezion.swarm.swarm_types import SwarmConfig
from cohezion.introspect.scanner import get_internal_scanner
from cohezion.bio.biophotonics import Wavelength

logger = logging.getLogger(__name__)

class IntrospectAgent(SovereignAgent):
    """
    Introspect Agent (Phase 20).

    Gateway 30+: System Self-Awareness.

    Role:
    - The Monk: Meditates on repo state and history.
    - Generates 'Daily Reflection' artifact.
    """
    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(config=config)
        self.scanner = get_internal_scanner()
        self.id = "IntrospectAgent"

    async def process(self, query: str) -> str:
        """
        Perform a system-wide introspection.
        """
        # 1. Scan Internal State
        code_signals = self.scanner.scan_codebase()
        history_signals = self.scanner.scan_history()

        # 2. Generate Reflection
        reflection = f"\n\n### 🧘 Daily Reflection (System Introspection)\n"

        # Codebase Insights
        todos = code_signals["todo_count"]
        reflection += f"**Codebase Entropy**:\n"
        reflection += f"- Active Nodes (Files): {code_signals['file_count']}\n"
        reflection += f"- Karmic Debt (TODOs): {todos}\n"

        if todos > 50:
             reflection += "⚠️ **Disturbance Detected**: High technical debt density.\n"
             self._emit(Wavelength.BLUE, 0.7, "INT: High Debt")

        if code_signals["high_churn_files"]:
            hotspots = ", ".join([f"{f} ({c})" for f, c in code_signals["high_churn_files"]])
            reflection += f"- **Energy Hotspots (Churn)**: {hotspots}\n"

        # History Insights
        themes = history_signals["recurring_themes"]
        if themes:
            reflection += f"**Recurring Thoughts**: {', '.join(themes)}\n"

        # 3. Write Artifact (Simulated persistence)
        # In a real run, this would save to a markdown file
        self._write_reflection(reflection)

        return await super().process(query) + reflection

    def _write_reflection(self, content: str):
        path = Path("daily_reflection.md")
        try:
            with open(path, "w") as f:
                f.write(f"# Daily Reflection {time.strftime('%Y-%m-%d')}\n{content}")
        except Exception:
            pass

    async def close(self):
        await super().close()
