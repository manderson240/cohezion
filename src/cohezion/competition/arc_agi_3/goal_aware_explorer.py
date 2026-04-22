"""Goal-aware systematic explorer for ARC-AGI-3.

Builds on systematic_explorer.py by adding:
1. Grid region analysis (find distinct/interesting areas)
2. Goal hypothesis: try ACTION5 (Enter/Spacebar) and ACTION6 (Click) at key locations
3. Navigation toward unexplored or unique-color regions
4. Better action selection after exploration phase
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any, Dict, List, Optional, Tuple

import numpy as np


def find_regions(grid: List[List[int]], min_size: int = 4, max_size: int = 256) -> List[Dict[str, Any]]:
    """Find connected-component regions in the grid."""
    arr = np.array(grid)
    h, w = arr.shape
    visited = np.zeros((h, w), dtype=bool)
    regions = []

    for y in range(h):
        for x in range(w):
            if visited[y, x] or arr[y, x] == 0:
                continue
            color = arr[y, x]
            # BFS for connected component
            queue = deque([(y, x)])
            visited[y, x] = True
            pixels = []
            while queue:
                cy, cx = queue.popleft()
                pixels.append((cx, cy))
                for dy, dx in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    ny, nx = cy + dy, cx + dx
                    if 0 <= ny < h and 0 <= nx < w and not visited[ny, nx] and arr[ny, nx] == color:
                        visited[ny, nx] = True
                        queue.append((ny, nx))

            if min_size <= len(pixels) <= max_size:
                xs = [p[0] for p in pixels]
                ys = [p[1] for p in pixels]
                regions.append({
                    "color": int(color),
                    "pixels": len(pixels),
                    "center_x": int(sum(xs) / len(xs)),
                    "center_y": int(sum(ys) / len(ys)),
                    "bbox": (min(xs), min(ys), max(xs), max(ys)),
                })
    return regions


def find_player(grid: List[List[int]]) -> Optional[Tuple[int, int]]:
    """Find player as a small non-background region near center."""
    regions = find_regions(grid, min_size=1, max_size=16)
    if not regions:
        return None

    arr = np.array(grid)
    cx, cy = arr.shape[1] // 2, arr.shape[0] // 2

    # Score regions: prefer small, near-center, unique colors
    scored = []
    for r in regions:
        dist = abs(r["center_x"] - cx) + abs(r["center_y"] - cy)
        uniqueness = len([x for x in regions if x["color"] == r["color"]])
        score = -dist - r["pixels"] * 2 - uniqueness * 10
        scored.append((score, r))
    scored.sort(key=lambda x: x[0], reverse=True)
    best = scored[0][1]
    return (best["center_x"], best["center_y"])


def find_target_regions(grid: List[List[int]], player_pos: Optional[Tuple[int, int]]) -> List[Dict[str, Any]]:
    """Find regions that might be targets (exits, keys, etc.)."""
    regions = find_regions(grid, min_size=2, max_size=64)
    if not regions or player_pos is None:
        return regions

    # Target heuristics
    for r in regions:
        dist_to_player = abs(r["center_x"] - player_pos[0]) + abs(r["center_y"] - player_pos[1])
        r["dist_to_player"] = dist_to_player
        # Score: medium-sized, distinct color, not too close, not too far
        r["target_score"] = 100 - abs(r["pixels"] - 8) * 5 - dist_to_player

    # Sort by target score
    regions.sort(key=lambda x: x.get("target_score", 0), reverse=True)
    return regions


class GoalAwareExplorer:
    """Agent that explores then targets promising regions."""

    def __init__(self, game_id: str, max_actions: int = 400):
        self.game_id = game_id
        self.max_actions = max_actions
        self.action_effects: Dict[str, Dict[str, Any]] = {}
        self.tested: set = set()
        self.player_positions: List[Tuple[int, int]] = []
        self.explored = False
        self.phase = "EXPLORATION"  # EXPLORATION -> NAVIGATION -> INTERACTION
        self.target_regions: List[Dict[str, Any]] = []
        self.current_target: Optional[Tuple[int, int]] = None
        self.stuck_counter = 0

    def observe(self, action_name: str, prev_grid: Any, next_grid: Any, obs: Any) -> None:
        """Observe effect of an action."""
        import numpy as np
        prev_arr = np.array(prev_grid) if prev_grid is not None else np.array([])
        next_arr = np.array(next_grid) if next_grid is not None else np.array([])

        diff = 0
        if prev_arr.size > 0 and next_arr.size > 0 and prev_arr.shape == next_arr.shape:
            diff = int(np.sum(prev_arr != next_arr))

        prev_player = find_player(prev_grid) if prev_grid is not None else None
        next_player = find_player(next_grid) if next_grid is not None else None

        self.action_effects[action_name] = {
            "diff": diff,
            "prev_player": prev_player,
            "next_player": next_player,
            "state": getattr(obs, "state", None),
        }
        self.tested.add(action_name)

        if next_player:
            if not self.player_positions or self.player_positions[-1] != next_player:
                self.player_positions.append(next_player)
                self.stuck_counter = 0
            else:
                self.stuck_counter += 1

        # Update target regions based on latest observation
        if next_grid is not None:
            self.target_regions = find_target_regions(next_grid, next_player)

    def choose_action(self, available_actions: List[Any], obs: Any) -> Any:
        """Choose action based on current phase."""
        from arcengine import GameAction

        names = [a.name for a in available_actions]
        simple_actions = [a for a in available_actions if a.name.startswith("ACTION") and a.name != "ACTION6"]

        # Phase 1: Systematic exploration
        if not self.explored:
            untested = [a for a in available_actions if a.name not in self.tested]
            if untested:
                return untested[0]
            self.explored = True
            self.phase = "NAVIGATION"
            # After exploration, pick first target
            if self.target_regions:
                t = self.target_regions[0]
                self.current_target = (t["center_x"], t["center_y"])

        player = find_player(obs.frame[0]) if obs.frame else None

        # Phase 2: Navigation toward target
        if self.phase == "NAVIGATION" and player and self.current_target:
            px, py = player
            tx, ty = self.current_target
            dx, dy = tx - px, ty - py

            # Determine which simple action moves toward target
            action_order = []
            if abs(dx) > abs(dy):
                action_order.append("ACTION4" if dx > 0 else "ACTION3")  # Right : Left
                action_order.append("ACTION2" if dy > 0 else "ACTION1")  # Down : Up
            else:
                action_order.append("ACTION2" if dy > 0 else "ACTION1")  # Down : Up
                action_order.append("ACTION4" if dx > 0 else "ACTION3")  # Right : Left

            # Filter to available simple actions, fallback
            for name in action_order:
                if name in names:
                    return GameAction.from_name(name)

            # If we've been stuck too long, try ACTION5 (interact) or ACTION6 (click)
            if self.stuck_counter > 5:
                self.phase = "INTERACTION"

        # Phase 3: Interaction - try ACTION5 at player position, or ACTION6 at target
        if self.phase == "INTERACTION" or self.stuck_counter > 10:
            # Try ACTION5 first (Enter/Spacebar - generic interaction)
            if "ACTION5" in names:
                return GameAction.from_name("ACTION5")
            # Try ACTION6 (click) at player or target
            if "ACTION6" in names:
                action = GameAction.from_name("ACTION6")
                if player:
                    action.set_data({"x": player[0], "y": player[1]})
                return action
            # Try all simple actions as a sweep
            if simple_actions:
                return random.choice(simple_actions)

        # Fallback: random move or ACTION5
        if "ACTION5" in names and random.random() < 0.3:
            return GameAction.from_name("ACTION5")
        if simple_actions:
            return random.choice(simple_actions)
        if available_actions:
            return random.choice(available_actions)
        return GameAction.RESET


def run_goal_aware_explorer(game_id: str, max_actions: int = 400) -> Dict[str, Any]:
    """Run one episode with the goal-aware explorer."""
    import arc_agi
    from arcengine import GameAction, GameState

    arc = arc_agi.Arcade()
    env = arc.make(game_id)
    obs = env.reset()

    agent = GoalAwareExplorer(game_id, max_actions)
    wins = 0
    actions_taken = 0

    while actions_taken < max_actions:
        prev_grid = obs.frame[0] if obs.frame else None
        action = agent.choose_action(env.action_space, obs)
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
        "phase": agent.phase,
        "targets_found": len(agent.target_regions),
        "stuck": agent.stuck_counter,
    }


if __name__ == "__main__":
    import logging
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    results = []
    for game_id in ["r11l", "ls20", "lp85"]:
        result = run_goal_aware_explorer(game_id)
        results.append(result)
        print(f"\n{game_id}: wins={result['wins']}, score={result['score']}, "
              f"actions={result['actions']}, phase={result['phase']}, "
              f"targets={result['targets_found']}, stuck={result['stuck']}")

    # Compute average score for METRIC
    total_score = sum(r["score"] for r in results)
    avg_score = total_score / len(results)
    print(f"\nMETRIC agent_efficiency_score={avg_score:.4f}")
