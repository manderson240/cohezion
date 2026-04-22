"""Gemma-4-Good Hackathon specialist agent — kernel review and social-good angle."""
from __future__ import annotations

import logging
from typing import Any

from cohezion.competition.orchestrator.agents.base_agent import BaseAgent


logger = logging.getLogger(__name__)


class GemmaHackathonAgent(BaseAgent):
    """Agent for Gemma-4-Good Hackathon submission support."""

    SYSTEM_PROMPT = """You are a Kaggle hackathon specialist focused on the Gemma-4-Good competition.

The competition rewards:
- Impact & Vision: how the project helps people or the planet
- Video Pitch & Storytelling: compelling narrative around the work
- Technical Depth & Execution: clean code, working demo, thorough documentation

You help review submissions, suggest improvements, and ensure all requirements are met.
Be honest about gaps. Respond concisely."""

    def __init__(self, dispatcher: Any) -> None:
        super().__init__("gemma-hackathon", dispatcher)

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "review")

        if action == "review_submission":
            return self._review_submission(task)
        if action == "impact_assessment":
            return self._impact_assessment(task)
        if action == "check_requirements":
            return self._check_requirements(task)

        return {"error": f"Unknown action: {action}"}

    def _review_submission(self, task: dict[str, Any]) -> dict[str, Any]:
        kernel_url = task.get("kernel_url", "")
        writeup = task.get("writeup", "")

        prompt = f"""Review this Gemma-4-Good hackathon submission:

Kernel: {kernel_url}
Writeup:
{writeup[:2000]}

Score 1-10 on:
1. Technical depth
2. Social impact / vision
3. Storytelling quality
4. Demo completeness
5. Overall readiness

Suggest the top 3 missing pieces that would most improve winning chances.
Respond in JSON."""

        result = self.think(self.SYSTEM_PROMPT, prompt, max_tokens=800)
        return {
            "action": "review_submission",
            "raw_response": result.text,
            "tokens_used": result.tokens_used,
        }

    def _impact_assessment(self, task: dict[str, Any]) -> dict[str, Any]:
        description = task.get("description", "")

        schema = {
            "type": "object",
            "properties": {
                "impact_score": {"type": "number"},
                "target_beneficiaries": {"type": "string"},
                "measurable_outcomes": {"type": "string"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "weaknesses": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["impact_score", "target_beneficiaries", "strengths", "weaknesses"],
        }
        prompt = f"""Assess the social impact of this project for the Gemma-4-Good hackathon:

{description[:2000]}

Evaluate how well it serves people or the planet."""

        parsed = self.dispatcher.generate_structured(
            self.SYSTEM_PROMPT, prompt, schema
        )
        return {
            "action": "impact_assessment",
            "assessment": parsed,
            "tokens_used": parsed.get("_tokens_used", 0),
        }

    def _check_requirements(self, task: dict[str, Any]) -> dict[str, Any]:
        prompt = """Checklist for Gemma-4-Good hackathon submission requirements:

Required:
□ Kaggle account with identity verification
□ Registered for the hackathon competition
□ Public project write-up (README.md style)
□ Public code repository or Kaggle kernel
□ Public demo or demo files
□ 60-second demo video
□ Cover image for media gallery

For each missing item, explain why it's important and how to complete it.
Respond in structured JSON with keys: requirements_met, requirements_missing, next_actions.
"""

        result = self.think(self.SYSTEM_PROMPT, prompt, max_tokens=600)
        return {
            "action": "check_requirements",
            "raw_response": result.text,
            "tokens_used": result.tokens_used,
        }
