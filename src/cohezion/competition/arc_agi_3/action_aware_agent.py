"""Action-type-aware agent for ARC-AGI-3.

Breakthrough insight from reading game source:
- Some games are CLICK-ONLY (available_actions=[6])
- Some are DIRECTIONAL-ONLY (available_actions=[1,2,3,4])
- ACTION6 requires x,y coordinates
- ACTION1-4 are directional but camera follows player, making grid-shift detection misleading
"""

from __future__ import annotations

import random
from typing import Any

import numpy as np


class ActionAwareAgent:
    """Agent that adapts strategy based on available action types."""

    def __init__(self, game_id: str, max_actions: int = 400):
        self.game_id = game_id
        self.max_actions = max_actions
        self.click_mode = False
        self.direction_mode = False
        self.stuck = 0

        # Click state
        self.click_grid: dict[tuple[int, int], dict[str, Any]] = {}
        self.click_positions: list[tuple[int, int]] = []
        self.click_idx = 0

        # Direction state
        self.player_trail: list[tuple[int, int] | None] = []
        self.recent_diffs: dict[str, list[int]] = {
            "ACTION1": [],
            "ACTION2": [],
            "ACTION3": [],
            "ACTION4": [],
        }

    def find_player_by_motion(self, prev_grid: Any, next_grid: Any) -> tuple[int, int] | None:
        """Find player by tracking which pixels moved consistently."""
        if prev_grid is None or next_grid is None:
            return None
        prev = np.array(prev_grid)
        next = np.array(next_grid)
        if prev.shape != next.shape:
            return None

        # Find regions that changed color
        diff = prev != next
        ys, xs = np.where(diff)
        if len(xs) == 0:
            return None

        # The player is the region that moved (old location gone, new location appeared)
        # But with camera follow, the whole grid shifts.
        # Compensate by looking for the consistent shift direction.
        if len(xs) > 2:
            mx, my = int(xs.mean()), int(ys.mean())
            return (mx, my)
        return None

    def init_click_positions(self, grid_shape: tuple[int, int]) -> None:
        """Create systematic click positions across the grid."""
        h, w = grid_shape
        # Create a sparse grid of click positions
        positions = []
        for y in range(4, h, 8):
            for x in range(4, w, 8):
                positions.append((x, y))
        random.shuffle(positions)
        self.click_positions = positions
        self.click_idx = 0

    def choose_action(
        self, obs: Any, available_actions: list[Any], env_action_space: list[Any]
    ) -> Any:
        """Choose action based on game type and state."""

        action_names = [a.name for a in available_actions]
        self.click_mode = "ACTION6" in action_names and len(action_names) == 1
        self.direction_mode = any(
            n in action_names for n in ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]
        )

        if self.click_mode:
            return self._choose_click_action(obs)
        elif self.direction_mode:
            return self._choose_direction_action(env_action_space)
        else:
            # Mixed or other - random
            return random.choice(available_actions)

    def _choose_click_action(self, obs: Any) -> Any:
        from arcengine import GameAction

        grid = obs.frame[0] if obs.frame else None
        if grid is not None and not self.click_positions:
            self.init_click_positions((len(grid), len(grid[0])))

        if self.click_positions and self.click_idx < len(self.click_positions):
            x, y = self.click_positions[self.click_idx]
            self.click_idx += 1
            action = GameAction.from_name("ACTION6")
            action.set_data({"x": x, "y": y})
            return action

        # If all positions clicked, try clicking center again with ACTION5 if available
        action = GameAction.from_name("ACTION6")
        action.set_data({"x": 32, "y": 32})
        return action

    def _choose_direction_action(self, action_space: list[Any]) -> Any:
        from arcengine import GameAction

        # Simple strategy: cycle through directions to explore
        directions = ["ACTION1", "ACTION2", "ACTION3", "ACTION4"]
        available = [a for a in directions if a in [ac.name for ac in action_space]]
        if not available:
            return (
                GameAction.from_name("ACTION5")
                if any(a.name == "ACTION5" for a in action_space)
                else GameAction.ACTION1
            )

        # Rotate directions
        idx = (self.stuck // 5) % len(available)
        self.stuck += 1
        return GameAction.from_name(available[idx])

    def observe(self, action_name: str, prev_grid: Any, next_grid: Any, obs: Any) -> None:
        if action_name == "ACTION6" and self.click_mode:
            if self.click_positions and self.click_idx > 0:
                pos = self.click_positions[self.click_idx - 1]
                if prev_grid is not None and next_grid is not None:
                    self.click_grid[pos] = {
                        "state": obs.state.name if hasattr(obs, "state") else "?",
                        "levels": obs.levels_completed if hasattr(obs, "levels_completed") else 0,
                    }
        elif action_name.startswith("ACTION") and self.direction_mode:
            player = self.find_player_by_motion(prev_grid, next_grid)
            self.player_trail.append(player)


def run_action_aware_agent(game_id: str, max_actions: int = 400) -> dict[str, Any]:
    import arc_agi
    from arcengine import GameAction, GameState

    arc = arc_agi.Arcade()
    env = arc.make(game_id)
    obs = env.reset()

    agent = ActionAwareAgent(game_id, max_actions)
    wins = 0
    actions_taken = 0

    while actions_taken < max_actions:
        prev_grid = obs.frame[0] if obs.frame else None
        action = agent.choose_action(obs, env.action_space, env.action_space)
        obs = env.step(action)
        actions_taken += 1

        agent.observe(action.name, prev_grid, obs.frame[0] if obs.frame else None, obs)

        if obs.state == GameState.WIN:
            wins += 1
            break
        elif obs.state == GameState.GAME_OVER:
            obs = env.step(GameAction.RESET)

    scorecard = arc.get_scorecard()
    return {
        "game_id": game_id,
        "actions": actions_taken,
        "wins": wins,
        "score": scorecard.score if scorecard else 0.0,
        "click_positions_tested": len(agent.click_grid),
        "mode": "click" if agent.click_mode else "direction",
    }


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    for game_id in ["r11l", "ls20", "lp85"]:
        result = run_action_aware_agent(game_id)
        print(
            f"\n{game_id}: wins={result['wins']}, score={result['score']}, "
            f"actions={result['actions']}, mode={result['mode']}, "
            f"clicks={result['click_positions_tested']}"
        )
