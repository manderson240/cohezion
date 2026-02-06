"""
Red Team Agent: The Disruptor. Injects adversarial challenges to probe modularization health.
Blue Team Agent: The Stabilizer. Ensures system health and HIHO 0.5 equilibrium.
"""

import json
import logging
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig

logger = logging.getLogger(__name__)


class RedTeamAgent(BaseAgent):
    """
    Adversarial agent that attempts to identify weak points in modularization.
    """

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(model_name="phi3:mini", config=config)

    async def disrupt(
        self, module_path: str, proposed_changes: list[dict[str, Any]]
    ) -> dict[str, Any]:
        """
        Analyzes proposed refactoring and suggests "stress tests" or identifies potential breakage.
        """
        logger.info(f"💣 [RED TEAM] Probing {module_path} for weaknesses")

        prompt = f"""
PROPOSED CHANGES to '{module_path}':
{json.dumps(proposed_changes, indent=2)}

TASK:
1. As an adversary, identify how these changes could BREAK the system.
2. Look for: Circular imports, missing dependencies, hydration errors, or performance regressions.
3. Suggest a specific "Disruption Test" (e.g., a test case that would fail if modularization is incomplete).

Output JSON:
{{
  "vulnerability": "...",
  "disruption_test": "...",
  "risk_score": 0.0-1.0
}}
"""
        response = await self._call_ollama(
            prompt=prompt,
            system_prompt="You are a Red Team specialist. Your job is to find the hidden cracks in the architecture.",
            task_type="light-reasoning",
        )
        return {"disruption": str(response)}


class BlueTeamAgent(BaseAgent):
    """
    Stabilizer agent that ensures HIHO 0.5 equilibrium and heals disruptions.
    """

    def __init__(self, config: SwarmConfig | None = None):
        super().__init__(model_name="phi3:mini", config=config)

    async def stabilize(self, status_report: dict[str, Any]) -> dict[str, Any]:
        """
        Processes Red Team findings and Ouroboros sensing to apply healing protocols.
        """
        logger.info("🛡️ [BLUE TEAM] Stabilizing system equilibrium")

        prompt = f"""
SYSTEM STATUS REPORT:
{json.dumps(status_report, indent=2)}

TASK:
1. Analyze the disruptions and stability metrics.
2. Propose corrective actions (e.g., registering missing services, fixing imports, or adjusting resource allocation).
3. Ensure the system maintains a HIHO stability of exactly 0.5.

Output JSON:
{{
  "correction": "...",
  "is_stable": true/false,
  "healed_phi_score": 0.0-1.0
}}
"""
        response = await self._call_ollama(
            prompt=prompt,
            system_prompt="You are a Blue Team specialist. Your job is to maintain system homeostasis and protect against entropy.",
            task_type="light-reasoning",
        )
        return {"stabilization": str(response)}
