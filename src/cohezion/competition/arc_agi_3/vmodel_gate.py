"""V-Model Gate Hook for ARC-AGI-3 Milestone #1.

Automated gate that executes the full V-Model lifecycle for competition entry
decisions. Uses local inference (Ollama phi4) for baselines and integrates
learnings back into Cohezion core systems.
"""

from __future__ import annotations

import json
import logging
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


@dataclass
class VModelGateConfig:
    """Configuration for the V-Model decision gate."""

    # Timing
    milestone_deadline: str = "2026-06-30"
    spike_duration_days: int = 7
    decision_date: str = "2026-04-28"

    # Score thresholds
    min_games_solved: int = 3
    min_efficiency_ratio: float = 0.10
    max_leaderboard_score_target: float = 0.50

    # Experiment budget
    max_experiments_before_decision: int = 50
    max_hours_invested: int = 40

    # Lever names in Cohezion system
    efficiency_target_lever: str = "efficiency_target"
    exploration_budget_lever: str = "exploration_budget"
    planning_depth_lever: str = "planning_depth"

    def days_until_deadline(self) -> int:
        """Calculate days remaining until milestone deadline."""
        deadline = time.mktime(time.strptime(self.milestone_deadline, "%Y-%m-%d"))
        now = time.time()
        return max(0, int((deadline - now) / 86400))


@dataclass
class BaselineResult:
    """Result from a baseline experiment."""

    agent_type: str
    game_id: str
    score: float
    efficiency: float
    actions_taken: int
    levels_completed: int
    games_won: int
    duration_seconds: float
    states_visited: int
    timestamp: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ"))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "agent_type": self.agent_type,
            "game_id": self.game_id,
            "score": self.score,
            "efficiency": self.efficiency,
            "actions_taken": self.actions_taken,
            "levels_completed": self.levels_completed,
            "games_won": self.games_won,
            "duration_seconds": self.duration_seconds,
            "states_visited": self.states_visited,
            "timestamp": self.timestamp,
        }


class VModelGate:
    """Automated V-Model gate for competition entry decisions.

    This hook runs before expensive experiments to validate whether
    the ARC-AGI-3 milestone is worth pursuing. It:

    1. Measures baseline performance (random + local LLM)
    2. Compares against leaderboard targets
    3. Applies dynamic lever constraints
    4. Makes GO/NO-GO decision
    5. Triggers next phase automatically
    """

    def __init__(self, config: Optional[VModelGateConfig] = None):
        self.config = config or VModelGateConfig()
        self.results_dir = Path("data/arc_agi_3/baselines")
        self.results_dir.mkdir(parents=True, exist_ok=True)
        self.baselines: List[BaselineResult] = []

    def _has_local_phi4(self) -> bool:
        """Check if phi4 is available locally for LLM baselines."""
        try:
            result = subprocess.run(
                ["ollama", "list"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            return "phi4" in result.stdout
        except Exception:
            return False

    def run_random_baseline(
        self, game_id: str = "r11l", max_steps: int = 200
    ) -> BaselineResult:
        """Run random agent baseline on a single game."""
        logger.info(f"Running random baseline on {game_id}")

        import random

        import arc_agi
        from arcengine import GameAction

        random.seed(42)
        start = time.time()

        arc = arc_agi.Arcade()
        env = arc.make(game_id)
        obs = env.reset()

        states: set[int] = set()
        actions_taken = 0
        games_won = 0
        levels_completed = 0

        while actions_taken < max_steps:
            action = random.choice([a for a in env.action_space if a != GameAction.RESET])
            obs = env.step(action)
            states.add(hash(str(obs.frame[0])))
            actions_taken += 1

            if obs.state.name == "WIN":
                games_won += 1
                levels_completed = obs.levels_completed
                break
            elif obs.state.name == "GAME_OVER":
                obs = env.step(GameAction.RESET)

        duration = time.time() - start
        scorecard = arc.get_scorecard()
        score = scorecard.score if scorecard else 0.0

        result = BaselineResult(
            agent_type="random",
            game_id=game_id,
            score=score,
            efficiency=0.0,
            actions_taken=actions_taken,
            levels_completed=levels_completed,
            games_won=games_won,
            duration_seconds=duration,
            states_visited=len(states),
        )
        self.baselines.append(result)
        return result

    def run_local_llm_baseline(
        self, game_id: str = "r11l", max_actions: int = 80
    ) -> Optional[BaselineResult]:
        """Run LLM baseline using local phi4 via Ollama.

        Falls back to None if phi4 not available.
        """
        if not self._has_local_phi4():
            logger.warning("phi4 not available locally, skipping LLM baseline")
            return None

        logger.info(f"Running phi4 LLM baseline on {game_id}")

        import random

        import arc_agi
        import ollama
        from arcengine import GameAction

        random.seed(42)
        start = time.time()

        arc = arc_agi.Arcade()
        env = arc.make(game_id)
        obs = env.reset()

        states: set[int] = set()
        actions_taken = 0
        games_won = 0
        history: List[str] = []

        # Build action mapping for LLM
        action_names = {
            "ACTION1": GameAction.ACTION1,
            "ACTION2": GameAction.ACTION2,
            "ACTION3": GameAction.ACTION3,
            "ACTION4": GameAction.ACTION4,
            "ACTION5": GameAction.ACTION5,
            "ACTION6": GameAction.ACTION6,
            "RESET": GameAction.RESET,
        }

        while actions_taken < max_actions:
            # Build prompt
            available = [a.name for a in env.action_space]
            grid_summary = self._summarize_grid(obs.frame[0])

            prompt = f"""You are playing a video game on a 64x64 grid.

Available actions: {available}
Current state: {obs.state.name}
Levels completed: {obs.levels_completed}

Grid summary (top-left 8x8):
{grid_summary}

Previous actions: {history[-5:]}

Rules: You must WIN the game. Choose exactly one action from the available list.
Return ONLY the action name (e.g. ACTION1)."""

            try:
                response = ollama.chat(
                    model="phi4",
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.2, "num_predict": 10},
                )
                raw = response.message.content.strip().upper()
                # Extract action name
                chosen_name = None
                for name in action_names:
                    if name in raw:
                        chosen_name = name
                        break
                if chosen_name is None:
                    chosen_name = random.choice(available)
            except Exception as e:
                logger.warning(f"Ollama call failed: {e}")
                chosen_name = random.choice(available)

            action = action_names[chosen_name]
            history.append(chosen_name)
            obs = env.step(action)
            states.add(hash(str(obs.frame[0])))
            actions_taken += 1

            if obs.state.name == "WIN":
                games_won += 1
                break
            elif obs.state.name == "GAME_OVER":
                obs = env.step(GameAction.RESET)

        duration = time.time() - start
        scorecard = arc.get_scorecard()
        score = scorecard.score if scorecard else 0.0

        result = BaselineResult(
            agent_type="phi4-local",
            game_id=game_id,
            score=score,
            efficiency=0.0,
            actions_taken=actions_taken,
            levels_completed=obs.levels_completed if obs else 0,
            games_won=games_won,
            duration_seconds=duration,
            states_visited=len(states),
        )
        self.baselines.append(result)
        return result

    def _summarize_grid(self, grid: List[List[int]], sample_size: int = 8) -> str:
        """Create a text summary of a grid for LLM prompting."""
        rows = min(len(grid), sample_size)
        cols = min(len(grid[0]), sample_size) if grid else 0
        lines = []
        for r in range(rows):
            line = " ".join(str(grid[r][c]) for c in range(cols))
            lines.append(line)
        return "\n".join(lines)

    def evaluate_go_no_go(self) -> Tuple[str, Dict[str, Any]]:
        """Evaluate GO/NO-GO criteria based on baseline results.

        Returns:
            (decision, evidence_dict)
        """
        evidence: Dict[str, Any] = {
            "days_until_deadline": self.config.days_until_deadline(),
            "baselines_run": len(self.baselines),
            "random_scores": [],
            "llm_scores": [],
            "meet_min_games": False,
            "meet_min_efficiency": False,
            "meet_deadline": False,
        }

        for b in self.baselines:
            if b.agent_type == "random":
                evidence["random_scores"].append(b.to_dict())
            elif b.agent_type == "phi4-local":
                evidence["llm_scores"].append(b.to_dict())

        # Check criteria
        games_solved = sum(b.games_won for b in self.baselines)
        evidence["meet_min_games"] = games_solved >= self.config.min_games_solved

        avg_efficiency = sum(b.efficiency for b in self.baselines) / max(len(self.baselines), 1)
        evidence["meet_min_efficiency"] = avg_efficiency >= self.config.min_efficiency_ratio
        evidence["avg_efficiency"] = avg_efficiency

        evidence["meet_deadline"] = self.config.days_until_deadline() >= 14

        # Decision logic
        if not evidence["meet_deadline"]:
            return "NO-GO", evidence

        if evidence["meet_min_games"] and evidence["meet_min_efficiency"]:
            return "GO", evidence

        if games_solved > 0 and avg_efficiency > 0:
            return "CONDITIONAL-GO", evidence

        return "NO-GO", evidence

    def save_results(self) -> Path:
        """Save baseline results and decision evidence."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        path = self.results_dir / f"baseline_{timestamp}.json"
        data = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "config": {
                "milestone_deadline": self.config.milestone_deadline,
                "days_remaining": self.config.days_until_deadline(),
            },
            "baselines": [b.to_dict() for b in self.baselines],
            "decision": self.evaluate_go_no_go()[0],
            "evidence": self.evaluate_go_no_go()[1],
        }
        path.write_text(json.dumps(data, indent=2))
        logger.info(f"Saved baseline results to {path}")
        return path

    def trigger_next_phase(self, decision: str) -> None:
        """Trigger next automated phase based on decision.

        This integrates with the autoresearch loop and Cohezion core.
        """
        if decision == "GO":
            logger.info("V-Model Gate: GO → Triggering full agent development")
            self._emit_trigger("arc_agi_3_development_start")
        elif decision == "CONDITIONAL-GO":
            logger.info("V-Model Gate: CONDITIONAL-GO → Triggering extended spike")
            self._emit_trigger("arc_agi_3_extended_spike")
        else:
            logger.info("V-Model Gate: NO-GO → Pivoting back to Paper Track")
            self._emit_trigger("arc_agi_3_cancel", reason="baselines_too_low")

    def _emit_trigger(self, event_type: str, **kwargs: Any) -> None:
        """Emit a trigger event for Cohezion systems.

        Writes to the trigger log that other systems watch.
        """
        trigger_path = Path("data/arc_agi_3/triggers.jsonl")
        trigger_path.parent.mkdir(parents=True, exist_ok=True)

        event = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "event_type": event_type,
            "source": "vmodel_gate",
            "data": kwargs,
        }
        with open(trigger_path, "a") as f:
            f.write(json.dumps(event) + "\n")

    def run_full_gate(self, games: Optional[List[str]] = None) -> Tuple[str, Dict[str, Any]]:
        """Execute the full V-Model gate: baselines + decision + trigger.

        This is the main entry point for the hook.
        """
        games = games or ["r11l", "ls20"]  # Easiest + representative

        logger.info("=" * 60)
        logger.info("V-MODEL GATE: ARC-AGI-3 MILESTONE #1")
        logger.info(f"Days until deadline: {self.config.days_until_deadline()}")
        logger.info("=" * 60)

        # Run baselines
        for game_id in games:
            self.run_random_baseline(game_id=game_id)
            if self._has_local_phi4():
                self.run_local_llm_baseline(game_id=game_id)

        # Evaluate
        decision, evidence = self.evaluate_go_no_go()

        # Save and trigger
        self.save_results()
        self.trigger_next_phase(decision)

        logger.info("-" * 60)
        logger.info(f"DECISION: {decision}")
        logger.info(f"Evidence: {json.dumps(evidence, indent=2)}")
        logger.info("-" * 60)

        return decision, evidence


def main() -> None:
    """CLI entry point for the V-Model gate hook."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    gate = VModelGate()
    decision, evidence = gate.run_full_gate()

    print(f"\n{'=' * 50}")
    print(f"V-MODEL GATE DECISION: {decision}")
    print(f"{'=' * 50}")
    print(f"Days remaining: {evidence['days_until_deadline']}")
    print(f"Baselines run: {evidence['baselines_run']}")
    print(f"Avg efficiency: {evidence.get('avg_efficiency', 0):.3f}")
    print(f"Min games met: {evidence['meet_min_games']}")
    print(f"Min efficiency met: {evidence['meet_min_efficiency']}")
    print(f"Deadline feasible: {evidence['meet_deadline']}")

    sys.exit(0 if decision in ("GO", "CONDITIONAL-GO") else 1)


if __name__ == "__main__":
    main()
