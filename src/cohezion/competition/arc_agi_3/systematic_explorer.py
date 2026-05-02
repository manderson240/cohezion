"""Systematic exploration agent for ARC-AGI-3.

This agent improves on random by:
1. Systematically testing each available action
2. Detecting what changed (player movement, object interaction, state transitions)
3. Building a simple action-effect model
4. Choosing actions that promote exploration or move toward goals
"""

from __future__ import annotations

import random
from typing import Any

import numpy as np


def grid_diff(prev: Any, next: Any) -> tuple[int, tuple[int, int] | None]:
    """Count changed pixels and detect movement direction."""
    prev_arr = np.array(prev) if prev is not None else np.array([])
    next_arr = np.array(next) if next is not None else np.array([])
    if prev_arr.size == 0 or next_arr.size == 0 or prev_arr.shape != next_arr.shape:
        return 0, None
    prev = prev_arr.tolist() if hasattr(prev_arr, "tolist") else prev
    next = next_arr.tolist() if hasattr(next_arr, "tolist") else next

    diff_count = 0
    movement = None
    for y in range(len(prev)):
        for x in range(len(prev[0])):
            if prev[y][x] != next[y][x]:
                diff_count += 1
                movement = (x, y)
    return diff_count, movement


def find_player_pos(grid: list[list[int]]) -> tuple[int, int] | None:
    """Find player as small distinct colored region near center."""
    arr = np.array(grid)
    h, w = arr.shape
    center = (w // 2, h // 2)

    # Find regions of non-background colors that are small (<=16 pixels)
    unique_colors = np.unique(arr)
    candidates = []
    for color in unique_colors:
        if color == 0:
            continue
        mask = arr == color
        pixels = np.argwhere(mask)
        if 1 <= len(pixels) <= 16:
            cx, cy = int(pixels[:, 1].mean()), int(pixels[:, 0].mean())
            dist_to_center = abs(cx - center[0]) + abs(cy - center[1])
            candidates.append((color, cx, cy, len(pixels), dist_to_center))

    if candidates:
        # Prefer: small, near center
        candidates.sort(key=lambda c: c[4])  # Sort by distance to center
        return (candidates[0][1], candidates[0][2])
    return None


class SystematicExplorer:
    """Agent that explores systematically then exploits learned patterns."""

    def __init__(self, game_id: str, max_actions: int = 400):
        self.game_id = game_id
        self.max_actions = max_actions
        self.action_effects: dict[str, dict[str, Any]] = {}
        self.tested_actions: set[str] = set()
        self.player_positions: list[tuple[int, int]] = []
        self.last_grid: list[list[int]] | None = None
        self.exploration_mode = True

    def observe_action(
        self,
        action_name: str,
        prev_grid: list[list[int]],
        next_grid: list[list[int]],
        state_name: str,
    ) -> None:
        """Record what an action did."""
        diff, _ = grid_diff(prev_grid, next_grid)
        prev_player = find_player_pos(prev_grid)
        next_player = find_player_pos(next_grid)

        effect = {
            "diff_pixels": diff,
            "prev_player": prev_player,
            "next_player": next_player,
            "state": state_name,
        }
        self.action_effects[action_name] = effect
        self.tested_actions.add(action_name)

        if next_player:
            self.player_positions.append(next_player)

    def choose_action(self, available_actions: list[Any], obs: Any) -> Any:
        """Choose action based on current knowledge."""
        from arcengine import GameAction

        available_names = [a.name for a in available_actions]

        # Phase 1: Systematic testing - test each unexplored action once
        unexplored = [a for a in available_actions if a.name not in self.tested_actions]
        if unexplored and self.exploration_mode:
            return unexplored[0]

        # Phase 2: If all actions explored, look for promising ones
        if self.exploration_mode and len(self.tested_actions) >= len(available_names):
            self.exploration_mode = False

        # Heuristic: prefer actions that caused movement
        movement_actions = []
        for name, effect in self.action_effects.items():
            if effect.get("diff_pixels", 0) > 0:
                movement_actions.append(name)

        if movement_actions and not self.exploration_mode:
            # Try movement actions in rotation to explore the grid
            action_name = movement_actions[len(self.player_positions) % len(movement_actions)]
            return GameAction.from_name(action_name)

        # Fallback: random
        return random.choice(available_actions)


def run_systematic_explorer(game_id: str, max_actions: int = 400) -> dict[str, Any]:
    """Run one game with the systematic explorer."""
    import arc_agi
    from arcengine import GameAction, GameState

    arc = arc_agi.Arcade()
    env = arc.make(game_id)
    obs = env.reset()

    agent = SystematicExplorer(game_id, max_actions)
    wins = 0
    actions_taken = 0

    while actions_taken < max_actions:
        prev_grid = obs.frame[0] if obs.frame else []
        action = agent.choose_action(env.action_space, obs)
        obs = env.step(action)
        actions_taken += 1

        # Observe effect
        next_grid = obs.frame[0] if obs.frame else []
        agent.observe_action(action.name, prev_grid, next_grid, obs.state.name)

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
        "levels_completed": obs.levels_completed if obs else 0,
        "action_effects": agent.action_effects,
        "exploration_complete": not agent.exploration_mode,
    }


if __name__ == "__main__":
    import logging

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    for game_id in ["r11l", "ls20", "lp85"]:
        result = run_systematic_explorer(game_id)
        print(
            f"\n{game_id}: wins={result['wins']}, score={result['score']}, "
            f"actions={result['actions']}, explored={result['exploration_complete']}"
        )
        if result["action_effects"]:
            for name, effect in result["action_effects"].items():
                print(
                    f"  {name}: diff={effect['diff_pixels']}px, "
                    f"player={effect['next_player']}, state={effect['state']}"
                )
