import json
import logging
from typing import Any

from cohezion.agents.base import BaseAgent
from cohezion.swarm.swarm_types import SwarmConfig


logger = logging.getLogger(__name__)


class HealerAgent(BaseAgent):
    """
    Agent responsible for synthesizing system patches and architecture
    adjustments based on Ouroboros anomaly reports.
    """

    def __init__(
        self, model_name: str = "qwen3-coder", config: SwarmConfig | None = None, **kwargs
    ):
        super().__init__(model_name, config, **kwargs)

    async def synthesize_patch(self, anomaly_report: dict[str, Any]) -> str:
        """
        Generates a patch proposal based on the provided anomaly report.

        Args:
            anomaly_report: Dictionary containing degradation details.

        Returns:
            str: The synthesized patch proposal.
        """
        prompt = f"""
        ANOMALY REPORT DETECTED:
        {json.dumps(anomaly_report, indent=2)}

        As the Ouroboros Healer, synthesize a specific patch proposal to stabilize
        the Cohezion Triune Manifold. Focus on coherence recovery toward the 0.5
        HIHO stability point.

        Provide your response in the following format:
        PATCH Proposal: <Description of adjustment>
        Rationale: <Explanation of why this stabilizes the system>
        """

        logger.info("HealerAgent synthesizing patch for detected anomalies...")
        patch_proposal = await self._call_ollama(prompt)

        return patch_proposal

    async def process(self, *args: Any, **kwargs: Any) -> Any:
        """
        Required BaseAgent process implementation.
        """
        report = args[0] if args else kwargs.get("report", {})
        return await self.synthesize_patch(report)
