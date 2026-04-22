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
Be honest about gaps. Respond concisely with structured JSON when requested."""

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

        schema = {
            "type": "object",
            "properties": {
                "technical_depth_score": {"type": "number"},
                "impact_score": {"type": "number"},
                "storytelling_score": {"type": "number"},
                "demo_completeness_score": {"type": "number"},
                "overall_readiness_score": {"type": "number"},
                "top_3_missing": {"type": "array", "items": {"type": "string"}},
                "strengths": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "technical_depth_score",
                "impact_score",
                "storytelling_score",
                "overall_readiness_score",
                "top_3_missing",
            ],
        }

        prompt = f"""Review this Gemma-4-Good hackathon submission:

Kernel URL: {kernel_url}
Writeup (first 2000 chars):
{writeup[:2000]}

Score each dimension 1-10. Identify top 3 missing pieces.
Respond in JSON with keys: technical_depth_score, impact_score, storytelling_score, demo_completeness_score, overall_readiness_score, top_3_missing, strengths."""

        parsed = self.dispatcher.generate_structured(
            self.SYSTEM_PROMPT, prompt, schema
        )
        return {
            "action": "review_submission",
            "review": parsed,
            "tokens_used": parsed.get("_tokens_used", 0),
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
        """Check our submission against actual requirements."""
        artifacts = task.get("artifacts", [])
        missing_human = task.get("missing_human", [])

        schema = {
            "type": "object",
            "properties": {
                "readiness_pct": {"type": "number"},
                "ai_completeness_pct": {"type": "number"},
                "human_completeness_pct": {"type": "number"},
                "missing_critical": {"type": "array", "items": {"type": "string"}},
                "next_actions": {"type": "array", "items": {"type": "string"}},
            },
            "required": [
                "readiness_pct",
                "ai_completeness_pct",
                "human_completeness_pct",
                "missing_critical",
                "next_actions",
            ],
        }

        prompt = f"""Evaluate Gemma-4-Good hackathon submission readiness.

Requirements and their status:
- Public project write-up: {"✅ COMPLETE" if "README.md" in artifacts else "❌ MISSING"}
- Public code repository / Kaggle kernel: {"✅ COMPLETE" if "kernel.py" in artifacts else "❌ MISSING"}
- Public demo or demo files: {"✅ COMPLETE" if "app.py" in artifacts or "dashboard.py" in artifacts else "❌ MISSING"}
- Training / blog post: {"✅ COMPLETE" if "BLOG_POST.md" in artifacts or "training_loop.py" in artifacts else "❌ MISSING"}
- 60-second demo video: {"✅ COMPLETE" if "video" not in missing_human else "❌ REQUIRES HUMAN"}
- Cover image for media gallery: {"✅ COMPLETE" if "cover_image" not in missing_human else "❌ REQUIRES HUMAN"}
- Kaggle registration: {"✅ COMPLETE" if "registration" not in missing_human else "❌ REQUIRES HUMAN"}

All AI-buildable artifacts: {artifacts}
Human-only blockers: {missing_human}

Calculate:
1. readiness_pct = overall percentage (0-100)
2. ai_completeness_pct = what % of AI-buildable items are done
3. human_completeness_pct = what % of human-required items are done
4. missing_critical = list of items most blocking submission
5. next_actions = ordered list of what to do next

Respond in JSON. Be honest."""

        parsed = self.dispatcher.generate_structured(
            self.SYSTEM_PROMPT, prompt, schema
        )
        return {
            "action": "check_requirements",
            "result": parsed,
            "tokens_used": parsed.get("_tokens_used", 0),
        }
