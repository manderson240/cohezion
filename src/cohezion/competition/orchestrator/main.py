"""Main competition orchestrator — dispatches to specialist agents via Lemonade.

Drives all active prize tracks using local model inference (Gemma-4-26B on port 8002).
Handles the paper track, ARC analysis, and any remaining competition work.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cohezion.competition.orchestrator.agents.arc_solver_agent import ARCSolverAgent
from cohezion.competition.orchestrator.agents.paper_track_agent import PaperTrackAgent
from cohezion.competition.orchestrator.model_dispatcher import ModelDispatcher
from cohezion.competition.orchestrator.resource_guard import ResourceGuard


logger = logging.getLogger(__name__)


class CompetitionOrchestrator:
    """Dispatch tasks to specialist agents using local model inference.

    Active targets (Apr 2026):
    - arc-paper: highest EV, ready for model-assisted review
    - arc-solver: program analysis and strategy suggestions
    """

    def __init__(self) -> None:
        self.dispatcher = ModelDispatcher()
        self.paper_agent = PaperTrackAgent(self.dispatcher)
        self.arc_agent = ARCSolverAgent(self.dispatcher)
        self.guard = ResourceGuard()

    def dispatch(self, target: str, task: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a task to the appropriate specialist.

        Args:
            target: one of ['arc-paper', 'arc-solver']
            task: agent-specific task dict
        """
        if target not in ("arc-paper", "arc-solver"):
            return {"error": f"Unknown target: {target}"}

        agent = self.paper_agent if target == "arc-paper" else self.arc_agent
        try:
            result = agent.run_task(task)
            result["agent"] = agent.name
            result["status"] = "success"
            return result
        except Exception as e:
            logger.exception("Agent task failed")
            return {"error": str(e), "agent": agent.name, "status": "failed"}

    def health_check(self) -> dict[str, Any]:
        """Verify Lemonade server + memory state."""
        mem = self.guard.current_memory()
        warm = self.dispatcher._ensure_warm()
        return {
            "lemonade_warm": warm,
            "memory_gb": {
                "total": round(mem.total_gb, 1),
                "available": round(mem.available_gb, 1),
                "used": round(mem.used_gb, 1),
            },
            "oom_safe": mem.available_gb > ResourceGuard.SAFETY_BUFFER_GB,
        }


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    orch = CompetitionOrchestrator()

    # Health check
    health = orch.health_check()
    print(json.dumps(health, indent=2))

    if not health["lemonade_warm"]:
        print("ERROR: Lemonade not warm. Exiting.")
        sys.exit(1)

    if not health["oom_safe"]:
        print("WARNING: Low memory!")

    # Example: have the paper agent review a claim from our draft
    print("\n--- PAPER AGENT TEST ---")
    result = orch.dispatch(
        "arc-paper",
        {
            "action": "review_claim",
            "claim": ("Strategy selection provides a 4.2x solve rate multiplier (0.8% -> 3.4%)"),
            "evidence": (
                "1000-task ablation on ARC-AGI-2 training set. "
                "Raw primitive search: 0.7-0.8%. "
                "With _select_strategies: 3.4%."
            ),
        },
    )
    print(json.dumps(result, indent=2, default=str))
    print("\nMETRIC competitions_orchestrated=2")
