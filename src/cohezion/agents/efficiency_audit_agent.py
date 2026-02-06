"""
Efficiency Audit Agent for Cohezion.

Analyzes token usage, context window density, and system coherence.
Wires metrics from TimeKeeper into actionable optimization reports.
"""

import logging
from pathlib import Path
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.core.time_keeper import get_time_keeper

logger = logging.getLogger(__name__)


class EfficiencyAuditAgent(BaseAgent):
    """
    An agent dedicated to auditing system performance (Tokens/Context/Latency).
    """

    def __init__(self, model_name: str = "phi3:mini", **kwargs):
        super().__init__(model_name=model_name, **kwargs)
        self.tk = get_time_keeper()

    async def analyze_token_efficiency(self) -> dict[str, Any]:
        """
        Analyzes recent LLM calls for token/response ratios.
        """
        # Fetch recent events via raw query
        events = await self.tk.db.query(
            "SELECT * FROM velocity_events WHERE type = 'LLM_CALL' ORDER BY timestamp DESC LIMIT 100"
        )

        if not events:
            return {"status": "No data", "score": 1.0}

        total_tokens = sum(e.get("details", {}).get("tokens", 0) for e in events)
        avg_latency = sum(e.get("duration_ms", 0) for e in events) / len(events)

        prompt = f"""
        Audit the following swarm performance data:
        - Total LLM Calls: {len(events)}
        - Total Estimated Tokens: {total_tokens}
        - Avg Latency: {avg_latency:.2f}ms

        Evaluate the "Token Efficiency" (tokens per accomplishment) and "Context Density."
        Are we sending too much redundant context?

        Format:
        EFFICIENCY_SCORE: [0.0-1.0]
        ISSUES: [List of issues]
        REMEDIES: [Suggested optimizations]
        """

        response = await self._call_ollama(prompt)
        return {
            "report": response,
            "metrics": {"tokens": total_tokens, "latency": avg_latency},
        }

    async def process(self, input_data: str) -> str:
        """
        Main entry point for efficiency auditing.
        """
        report = await self.analyze_token_efficiency()
        return report.get("report", "Audit failed.")


async def main():
    agent = EfficiencyAuditAgent()
    try:
        print("Starting Token Efficiency Audit...")
        report = await agent.analyze_token_efficiency()
        print(f"--- EFFICIENCY REPORT ---\n{report['report']}\n")

        # Save to artifacts
        report_path = Path(
            "/home/mike-anderson/.gemini/antigravity/brain/4f5d1f06-5ebf-4df8-ac39-15c8a876e05c/efficiency_audit.md"
        )
        report_path.write_text(f"# Swarm Efficiency Audit\n\n{report['report']}")
        print(f"Report saved to {report_path}")
    finally:
        await agent.close()


if __name__ == "__main__":
    import asyncio

    logging.basicConfig(level=logging.INFO)
    asyncio.run(main())
