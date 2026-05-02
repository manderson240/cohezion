"""ARC-AGI-2 solver agent using local model reasoning.

The agent analyzes tasks, suggests primitive strategies, and can generate code.
Does NOT run DSL search itself — focuses on high-level reasoning.
"""

from __future__ import annotations

import logging
from typing import Any

from cohezion.competition.orchestrator.agents.base_agent import BaseAgent


logger = logging.getLogger(__name__)

SYSTEM = """You are an ARC-AGI-2 reasoning specialist.
Given ARC tasks (grid transformations), analyze the pattern and suggest:
1. What transformation category is likely (geometric, color, object, compositional)
2. What primitives might solve it
3. Confidence level
Respond with structured JSON."""


class ARCSolverAgent(BaseAgent):
    """Agent for ARC-AGI-2 task analysis."""

    def __init__(self, dispatcher: Any) -> None:
        super().__init__("arc-solver", dispatcher)

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        if task.get("action") == "analyze_task":
            return self._analyze(task["grid_data"])
        if task.get("action") == "suggest_program":
            return self._suggest_program(task["grid_data"], task.get("previous_attempts", []))
        return {"error": f"Unknown action: {task.get('action')}"}

    def _analyze(self, grid_data: str) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "category": {"type": "string"},
                "primitives": {"type": "array", "items": {"type": "string"}},
                "confidence": {"type": "number"},
                "reasoning": {"type": "string"},
            },
            "required": ["category", "confidence"],
        }
        prompt = f"Analyze this ARC task:\n{grid_data}"
        return self.dispatcher.generate_structured(SYSTEM, prompt, schema)

    def _suggest_program(self, grid_data: str, prev: list) -> dict[str, Any]:
        schema = {
            "type": "object",
            "properties": {
                "program_steps": {"type": "array", "items": {"type": "string"}},
                "estimated_solve_rate": {"type": "number"},
                "confidence": {"type": "number"},
            },
            "required": ["program_steps", "confidence"],
        }
        prompt = f"Previous attempts: {prev}\nSuggest a new program for:\n{grid_data}"
        return self.dispatcher.generate_structured(SYSTEM, prompt, schema)
