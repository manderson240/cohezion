"""Local phi4 agent for ARC-AGI-3 using Ollama inference.

Uses the local AMD Ryzen AI MAX+ 395 for inference instead of cloud APIs.
Text-only reasoning about grid state (no vision).
"""

from __future__ import annotations

import logging
import random
from typing import Any

import ollama


logger = logging.getLogger(__name__)


def grid_to_ascii(grid: list[list[int]], max_size: int = 32) -> str:
    """Convert grid to compact ASCII for LLM reasoning."""
    import numpy as np

    arr = np.array(grid)
    h, w = arr.shape

    # Downsample if too large
    if max(h, w) > max_size:
        scale = max(h, w) // max_size
        arr = arr[::scale, ::scale]
        h, w = arr.shape

    # Use chars 0-9, A-F for values
    chars = " .123456789ABCDEF"
    lines = []
    for row in arr.tolist():
        lines.append("".join(chars[v + 1] if 0 <= v <= 15 else "?" for v in row))
    return "\n".join(lines)


class Phi4Agent:
    """Agent using local phi4 via Ollama."""

    MODEL = "phi4"
    MAX_HISTORY = 6

    def __init__(self, game_id: str, max_actions: int = 100):
        self.game_id = game_id
        self.max_actions = max_actions
        self.history: list[dict[str, Any]] = []
        self.wins = 0
        self.actions_taken = 0

    def choose_action(self, obs: Any, available_actions: list[str]) -> str:
        """Ask phi4 to reason about next action."""
        if not available_actions:
            return "RESET"

        grid_str = grid_to_ascii(obs.frame[0]) if obs.frame else "(no grid)"
        state_name = obs.state.name if hasattr(obs, "state") else "UNKNOWN"
        levels = obs.levels_completed if hasattr(obs, "levels_completed") else 0

        # Build recent history summary
        recent = []
        for h in self.history[-self.MAX_HISTORY :]:
            recent.append(
                f"- {h['action']} -> state={h['state']}, levels={h['levels']}, reward={h.get('reward', 0)}"
            )
        history_str = "\n".join(recent) if recent else "(no prior actions)"

        prompt = f"""You are an AI agent playing a puzzle game on a grid.

Current grid ({state_name}, levels={levels}):
{grid_str}

Available actions: {available_actions}

Recent history:
{history_str}

Your goal is to WIN the game. Choose ONE action from the available list.
Return ONLY the action name, nothing else. Example: ACTION1"""

        try:
            response = ollama.chat(
                model=self.MODEL,
                messages=[{"role": "user", "content": prompt}],
                options={"temperature": 0.3, "num_predict": 10, "num_ctx": 4096},
            )
            raw = response.message.content.strip().upper()
            # Extract action name
            for action in available_actions:
                if action in raw:
                    return action
            return available_actions[0]
        except Exception as e:
            logger.warning(f"Ollama error: {e}")
            return random.choice(available_actions)

    def observe(self, action_name: str, obs: Any) -> None:
        self.history.append(
            {
                "action": action_name,
                "state": obs.state.name if hasattr(obs, "state") else "?",
                "levels": obs.levels_completed if hasattr(obs, "levels_completed") else 0,
            }
        )


def run_phi4_agent(game_id: str, max_actions: int = 50) -> dict[str, Any]:
    """Run phi4 agent on one game."""
    import arc_agi
    from arcengine import GameAction, GameState

    arc = arc_agi.Arcade()
    env = arc.make(game_id)
    obs = env.reset()

    agent = Phi4Agent(game_id, max_actions)

    for _ in range(max_actions):
        available = [a.name for a in env.action_space]
        action_name = agent.choose_action(obs, available)
        action = GameAction.from_name(action_name)
        obs = env.step(action)
        agent.observe(action_name, obs)

        if obs.state == GameState.WIN:
            agent.wins += 1
            break
        elif obs.state == GameState.GAME_OVER:
            obs = env.step(GameAction.RESET)

    scorecard = arc.get_scorecard()
    return {
        "game_id": game_id,
        "wins": agent.wins,
        "actions": len(agent.history),
        "score": scorecard.score if scorecard else 0.0,
        "history": agent.history,
    }


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    # Run on easiest game only (phi4 is slow)
    result = run_phi4_agent("r11l", max_actions=30)
    print(f"\nr11l: wins={result['wins']}, score={result['score']}, actions={result['actions']}")
    if result["history"]:
        print("Action sequence:")
        for h in result["history"]:
            print(f"  {h['action']} -> {h['state']}")
