"""SEI Accelathon specialist agent.

Designs MCP tooling, writes smart contract integration, and plans hackathon submissions.
"""

from __future__ import annotations

import logging
from typing import Any

from cohezion.competition.orchestrator.agents.base_agent import BaseAgent


logger = logging.getLogger(__name__)

SYSTEM = """You are a Sei blockchain tooling specialist.
You design MCP servers, smart contract integrations, and hackathon entries
for the Sei AI Accelathon. All designs must integrate with Sei and be open-source.
Respond with structured JSON."""


class SeiAccelathonAgent(BaseAgent):
    """Agent for Sei Accelathon MCP tooling builds."""

    def __init__(self, dispatcher: Any) -> None:
        super().__init__("sei-accelathon", dispatcher)

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action")
        if action == "design_mcp_tools":
            return self._design_mcp_tools(task["requirements"])
        if action == "plan_submission":
            return self._plan_submission(
                track=task["track"], idea=task["idea"], deadline=task["deadline"]
            )
        if action == "write_contract_interface":
            return self._write_contract_interface(task["contract_type"])
        return {"error": f"Unknown action: {action}"}

    def _design_mcp_tools(self, requirements: str) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "tools": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "description": {"type": "string"},
                            "params": {"type": "array", "items": {"type": "string"}},
                            "complexity": {"type": "string", "enum": ["low", "medium", "high"]},
                        },
                        "required": ["name", "description", "complexity"],
                    },
                },
                "novelty": {"type": "string"},
                "sei_integration": {"type": "string"},
            },
            "required": ["tools", "novelty", "sei_integration"],
        }
        prompt = (
            f"Design MCP tools for this Sei Accelathon requirement:\n{requirements}\n"
            f"Consider compound session features: alignment gates, "
            f"journey tracking, vault persistence."
        )
        return self.dispatcher.generate_structured(SYSTEM, prompt, schema)

    def _plan_submission(self, track: str, idea: str, deadline: str) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "judging_score": {"type": "number"},
                "strengths": {"type": "array", "items": {"type": "string"}},
                "risks": {"type": "array", "items": {"type": "string"}},
                "tasks": {"type": "array", "items": {"type": "string"}},
                "weeks": {"type": "number"},
            },
            "required": ["judging_score", "strengths", "risks", "tasks"],
        }
        prompt = (
            f"Track: {track}\nIdea: {idea}\nDeadline: {deadline}\n"
            f"Plan a realistic submission. Estimate judging score (0-100)."
        )
        parsed = self.dispatcher.generate_structured(SYSTEM, prompt, schema)
        parsed["track"] = track
        return parsed

    def _write_contract_interface(self, contract_type: str) -> dict[str, Any]:
        prompt = (
            f"Write a minimal Solidity contract interface for {contract_type} "
            f"on Sei EVM. Keep it simple."
        )
        result = self.think(SYSTEM, prompt, temperature=0.3, max_tokens=1024)
        return {"contract_type": contract_type, "code": result.text}
