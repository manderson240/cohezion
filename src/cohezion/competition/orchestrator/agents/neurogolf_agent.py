"""NeuroGolf specialist agent — analysis and submission for tiny NN competition."""
from __future__ import annotations

import logging
from typing import Any

from cohezion.competition.orchestrator.agents.base_agent import BaseAgent


logger = logging.getLogger(__name__)


class NeuroGolfAgent(BaseAgent):
    """Agent for NeuroGolf 2026 competition tasks."""

    SYSTEM_PROMPT = """You are a specialist in tiny neural network design for ARC-AGI grid transformations.

Constraints:
- Network MUST be under 100K parameters
- Input: 30×30 grid with 10 color values (0-9)
- Output: transformed grid
- No external data, no pretrained models, no LLM APIs during inference

Your role: analyze architecture proposals, suggest improvements, review submission format.
Be concise. Focus on parameter count, forward pass efficiency, and ARC-suitable inductive biases.
"""

    def __init__(self, dispatcher: Any) -> None:
        super().__init__("neurogolf", dispatcher)

    def run_task(self, task: dict[str, Any]) -> dict[str, Any]:
        action = task.get("action", "analyze")

        if action == "analyze_architecture":
            return self._analyze_architecture(task)
        if action == "review_submission":
            return self._review_submission(task)
        if action == "score_estimate":
            return self._score_estimate(task)

        return {"error": f"Unknown action: {action}"}

    def _analyze_architecture(self, task: dict[str, Any]) -> dict[str, Any]:
        arch = task.get("architecture", "unknown")
        params = task.get("params", 0)
        accuracy = task.get("accuracy", 0)

        prompt = f"""Analyze this NeuroGolf architecture:

Architecture: {arch}
Parameters: {params:,}
Test accuracy: {accuracy}%

1. Is the param count under 100K?
2. What inductive biases does it have for grid transformations?
3. What are 2 specific improvements that could boost accuracy while staying under 100K?
4. Is this competitive for a $50K prize with 611 teams?

Respond in JSON with keys: under_budget, inductive_biases, improvements, competitive_assessment."""

        result = self.think(self.SYSTEM_PROMPT, prompt, max_tokens=800)
        return {
            "action": "analyze_architecture",
            "architecture": arch,
            "raw_response": result.text,
            "tokens_used": result.tokens_used,
        }

    def _review_submission(self, task: dict[str, Any]) -> dict[str, Any]:
        notebook_path = task.get("notebook_path", "")
        prompt = f"""Review this Kaggle submission for NeuroGolf 2026:

Notebook: {notebook_path}

Check:
1. Does it read competition data from /kaggle/input/ correctly?
2. Does it write submission.json in the right format?
3. Does the network stay under 100K params?
4. Are there any obvious runtime errors?

Respond in JSON with keys: data_loading_ok, format_ok, under_budget, runtime_risks."""

        result = self.think(self.SYSTEM_PROMPT, prompt, max_tokens=500)
        return {
            "action": "review_submission",
            "notebook_path": notebook_path,
            "raw_response": result.text,
            "tokens_used": result.tokens_used,
        }

    def _score_estimate(self, task: dict[str, Any]) -> dict[str, Any]:
        params = task.get("params", 0)
        accuracy = task.get("accuracy", 0)

        prompt = f"""Estimate NeuroGolf 2026 score for:
Parameters: {params:,}
Test accuracy: {accuracy}%

The NeuroGolf scoring formula is unknown, but likely combines accuracy and size penalty.
Models under 100K params are eligible. Rank-1 target is ≥20% accuracy.

1. What is the likely leaderboard position with this model?
2. What accuracy would be needed to be competitive?
3. Is this worth submitting given the Kaggle time cost?

Respond concisely."""

        result = self.think(self.SYSTEM_PROMPT, prompt, max_tokens=400)
        return {
            "action": "score_estimate",
            "params": params,
            "accuracy": accuracy,
            "raw_response": result.text,
            "tokens_used": result.tokens_used,
        }
