"""ARC Prize Paper Track specialist agent.

Writes paper sections, validates experimental claims, suggests improvements.
Uses structured JSON output for traceability.
"""

from __future__ import annotations

import logging
from typing import Any

from cohezion.competition.orchestrator.agents.base_agent import BaseAgent


logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """You are an AI research writing assistant specializing in AGI benchmark papers.
You help draft, critique, and improve academic papers for the ARC Prize Paper Track.
Be honest about limitations. Cite specific empirical results when available.
Respond with structured JSON."""


class PaperTrackAgent(BaseAgent):
    """Agent for ARC Prize Paper Track drafting and review."""

    def __init__(self, dispatcher: Any) -> None:
        super().__init__("paper-track", dispatcher)

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        if action == "draft_section":
            return self._draft_section(
                section=task["section"],
                context=task.get("context", ""),
                word_limit=task.get("word_limit", 500),
            )
        if action == "review_claim":
            return self._review_claim(
                claim=task["claim"],
                evidence=task.get("evidence", ""),
            )
        if action == "suggest_improvements":
            return self._suggest_improvements(draft=task["draft"])
        return {"error": f"Unknown action: {action}"}

    def _draft_section(self, section: str, context: str, word_limit: int) -> dict[str, Any]:
        prompt = (
            f"Draft the '{section}' section for an ARC Prize paper.\n"
            f"Context:\n{context}\n"
            f"Limit: {word_limit} words. Be concise and empirical."
        )
        result = self.think(SYSTEM_PROMPT, prompt, temperature=0.4, max_tokens=2048)
        return {"section": section, "draft": result.text, "tokens": result.tokens_used}

    def _review_claim(self, claim: str, evidence: str) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "claim_valid": {"type": "boolean"},
                "strength": {
                    "type": "string",
                    "enum": ["strong", "moderate", "weak", "unsupported"],
                },
                "suggested_evidence": {"type": "string"},
                "limitations": {"type": "string"},
            },
            "required": ["claim_valid", "strength"],
        }
        prompt = (
            f"Claim: {claim}\n"
            f"Evidence provided:\n{evidence}\n"
            f"Evaluate whether the claim is supported by the evidence."
        )
        parsed = self.dispatcher.generate_structured(SYSTEM_PROMPT, prompt, schema)
        return {"review": parsed, "claim": claim}

    def _suggest_improvements(self, draft: str) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "issues": {"type": "array", "items": {"type": "string"}},
                "improvements": {"type": "array", "items": {"type": "string"}},
                "priority": {"type": "string", "enum": ["high", "medium", "low"]},
            },
            "required": ["issues", "improvements", "priority"],
        }
        prompt = f"Review this paper draft and suggest concrete improvements:\n{draft[:4000]}"
        parsed = self.dispatcher.generate_structured(SYSTEM_PROMPT, prompt, schema)
        return {"suggestions": parsed}
