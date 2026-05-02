"""Main competition orchestrator — dispatches to specialist agents via Lemonade.

Drives all active prize tracks using local model inference (Gemma-4-26B on port 8002).
Handles the paper track, ARC analysis, and any remaining competition work.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from cohezion.competition.orchestrator.agents.arc_solver_agent import ARCSolverAgent
from cohezion.competition.orchestrator.agents.gemma_hackathon_agent import GemmaHackathonAgent
from cohezion.competition.orchestrator.agents.neurogolf_agent import NeuroGolfAgent
from cohezion.competition.orchestrator.agents.paper_track_agent import PaperTrackAgent
from cohezion.competition.orchestrator.agents.sei_accelathon_agent import SeiAccelathonAgent
from cohezion.competition.orchestrator.model_dispatcher import ModelDispatcher
from cohezion.competition.orchestrator.resource_guard import ResourceGuard


logger = logging.getLogger(__name__)


class CompetitionOrchestrator:
    """Dispatch tasks to specialist agents using local model inference.

    Active targets (Apr 2026):
    - arc-paper: highest EV ($450k), ready for model-assisted review
    - arc-solver: program analysis and strategy suggestions
    - gemma-hackathon: social good hackathon ($200k, May 18 deadline)
    - neurogolf: tiny NN architecture analysis ($50k, July 15)
    - sei-accelathon: blockchain tooling (pruned: ended Aug 2025)
    """

    AGENTS = ["arc-paper", "arc-solver", "gemma-hackathon", "neurogolf", "sei-accelathon"]

    def __init__(self) -> None:
        self.dispatcher = ModelDispatcher()
        self.paper_agent = PaperTrackAgent(self.dispatcher)
        self.arc_agent = ARCSolverAgent(self.dispatcher)
        self.gemma_agent = GemmaHackathonAgent(self.dispatcher)
        self.neuro_agent = NeuroGolfAgent(self.dispatcher)
        self.sei_agent = SeiAccelathonAgent(self.dispatcher)
        self.guard = ResourceGuard()
        self._agent_map = {
            "arc-paper": self.paper_agent,
            "arc-solver": self.arc_agent,
            "gemma-hackathon": self.gemma_agent,
            "neurogolf": self.neuro_agent,
            "sei-accelathon": self.sei_agent,
        }

    def dispatch(self, target: str, task: dict[str, Any]) -> dict[str, Any]:
        """Dispatch a task to the appropriate specialist.

        Args:
            target: one of ['arc-paper', 'arc-solver', 'neurogolf', 'sei-accelathon']
            task: agent-specific task dict
        """
        if target not in self.AGENTS:
            return {"error": f"Unknown target: {target}. Supported: {self.AGENTS}"}

        agent = self._agent_map[target]
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

    # Test all 5 agents
    agents_tested = 0

    print("\n--- PAPER AGENT TEST ---")
    result = orch.dispatch(
        "arc-paper",
        {
            "action": "review_claim",
            "claim": ("Strategy selection provides a 4.2x solve rate multiplier (0.8% -> 3.4%)"),
        },
    )
    print(json.dumps(result, indent=2, default=str))
    if result.get("status") == "success":
        agents_tested += 1

    print("\n--- ARC SOLVER AGENT TEST ---")
    result = orch.dispatch(
        "arc-solver",
        {
            "action": "analyze_task",
            "grid_data": [[0, 0, 0], [0, 1, 0], [0, 0, 0]],
        },
    )
    if result.get("status") == "success":
        agents_tested += 1

    print("\n--- GEMMA HACKATHON AGENT TEST ---")
    result = orch.dispatch(
        "gemma-hackathon",
        {
            "action": "impact_assessment",
            "description": "A compound crisis response system using Gemma-4 to coordinate disaster relief.",
        },
    )
    if result.get("status") == "success":
        agents_tested += 1

    print("\n--- NEUROGOLF AGENT TEST ---")
    result = orch.dispatch(
        "neurogolf",
        {
            "action": "analyze_architecture",
            "architecture": "5-layer residual conv + batch norm, hidden=40",
            "params": 73410,
            "accuracy": 2,
        },
    )
    if result.get("status") == "success":
        agents_tested += 1

    print("\n--- SEI AGENT TEST ---")
    result = orch.dispatch(
        "sei-accelathon",
        {
            "action": "assess_competition",
            "competition": "sei-ai-accelathon",
        },
    )
    if result.get("status") == "success":
        agents_tested += 1

    print(f"\nMETRIC competitions_orchestrated={agents_tested}")
