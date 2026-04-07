"""Meta-Reviewer for the EcoResilience swarm.
Conducts adversarial reviews of the system prompts and reasoning logic
used by the Triune Reviewer to prevent bias and maintain rigorous standards.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Tuple
from pydantic import BaseModel, Field

from cohezion.swarm.providers.gemma4_provider import Gemma4Provider, GenerationResult

logger = logging.getLogger(__name__)


class PromptAuditResult(BaseModel):
    """Result of a prompt adversarial review."""

    prompt_id: str
    vulnerabilities: List[str]
    bias_score: float  # 0.0 to 1.0
    rigor_score: float  # 0.0 to 1.0
    suggested_revision: str | None = None
    is_approved: bool


class MetaReviewer:
    """
    Reviewer of the Reviewers.
    Ensures that the Triune Reviewer's personas are actually adversarial
    and not just rubber-stamping the agent's output.
    """

    def __init__(self, provider: Gemma4Provider):
        self.provider = provider
        # The Meta-Reviewer uses the highest reasoning model (31B Cloud)
        self.model_name = "gemma4:31b-cloud"

    async def audit_prompt(self, persona_id: str, system_prompt: str) -> PromptAuditResult:
        """
        Analyzes a system prompt for potential 'workslop' or bias.
        """
        logger.info("Meta-Review: Auditing prompt for persona %s...", persona_id)

        audit_prompt = (
            f"You are a Meta-Reviewer specializing in prompt engineering and adversarial AI audit. "
            f"Audit the following system prompt for a persona in an EcoResilience swarm: \n\n"
            f"PROMPT: {system_prompt}\n\n"
            f"Analyze for: \n"
            f"1. Leniency: Does the prompt allow the agent to be too lenient?\n"
            f"2. Bias: Does it ignore TEK or Physics in favor of simple answers?\n"
            f"3. Rigor: Is it demanding enough for a high-stakes ecological simulation?\n\n"
            f'Return a JSON response: {{"vulnerabilities": [str], "bias_score": float, "rigor_score": float, "suggested_revision": str, "is_approved": bool}}'
        )

        try:
            res = await self.provider.generate(
                model=self.model_name, prompt=audit_prompt, regime="CALCULATION", format="json"
            )

            import json

            data = json.loads(res.response)

            return PromptAuditResult(
                prompt_id=persona_id,
                vulnerabilities=data.get("vulnerabilities", []),
                bias_score=data.get("bias_score", 0.0),
                rigor_score=data.get("rigor_score", 0.0),
                suggested_revision=data.get("suggested_revision"),
                is_approved=data.get("is_approved", False),
            )
        except Exception as e:
            logger.error("Meta-Review failed for %s: %s", persona_id, e)
            return PromptAuditResult(
                prompt_id=persona_id,
                vulnerabilities=["Audit failed due to technical error"],
                bias_score=0.0,
                rigor_score=0.0,
                suggested_revision=None,
                is_approved=False,
            )

    async def audit_triune_system(self, reviewer_instance: Any) -> Dict[str, PromptAuditResult]:
        """Audits all personas in a TriuneReviewer instance."""
        results = {}
        for persona_id, prompt in reviewer_instance.personas.items():
            results[persona_id] = await self.audit_prompt(persona_id, prompt)
        return results
