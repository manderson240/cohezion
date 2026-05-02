"""Object-clicking agent for click-only ARC-AGI-3 games (r11l, lp85).

Insight from source: click games require ACTION6 with x,y targeting sprites.
This agent finds distinct colored regions and clicks their centers.
"""

from __future__ import annotations

import random
from collections import deque
from typing import Any

import numpy as np


def find_click_targets(
    grid: list[list[int]], min_size: int = 2, max_size: int = 256
) -> list[dict[str, Any]]:
    """Find all distinct click targets (non-background regions)."""
    arr = np.array(grid)
    h, w = arr.shape
    visited = np.zeros((h, w), dtype=bool)
    targets = []

    for y in range(h):
        for x in range(w):
            if visited[y, x] or arr[y, x] == 0:
                continue
            color = arr[y, x]
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
                targets.append(
                    {
                        "color": int(color),
                        "pixels": len(pixels),
                        "cx": int(sum(xs) / len(xs)),
                        "cy": int(sum(ys) / len(ys)),
                        "min_x": min(xs),
                        "max_x": max(xs),
                        "min_y": min(ys),
                        "max_y": max(ys),
                    }
                )
    return targets


def run_object_clicker(game_id: str, max_actions: int = 60) -> dict[str, Any]:
    import arc_agi
    from arcengine import GameAction, GameState

    arc = arc_agi.Arcade()
    env = arc.make(game_id)
    obs = env.reset()

    wins = 0
    actions_taken = 0
    targets = []
    target_idx = 0

    while actions_taken < max_actions:
        grid = obs.frame[0] if obs.frame else None
        if grid is not None and not targets:
            targets = find_click_targets(grid)
            # Sort by distinctiveness (unique colors first, medium size)
            targets.sort(
                key=lambda t: (
                    t["pixels"] > 100,
                    t["pixels"] < 4,
                    -len([x for x in targets if x["color"] == t["color"]]),
                )
            )

        if targets and target_idx < len(targets):
            t = targets[target_idx]
            x, y = t["cx"], t["cy"]
            # Add small random offsets near center
            x += random.randint(-2, 2)
            y += random.randint(-2, 2)
            x = max(0, min(63, x))
            y = max(0, min(63, y))

            action = GameAction.from_name("ACTION6")
            action.set_data({"x": x, "y": y})
            target_idx += 1
        else:
            # Random click
            action = GameAction.from_name("ACTION6")
            action.set_data({"x": random.randint(0, 63), "y": random.randint(0, 63)})

        obs = env.step(action)
        actions_taken += 1

        if obs.state == GameState.WIN:
            wins += 1
            break
        elif obs.state == GameState.GAME_OVER:
            break  # Out of actions

    scorecard = arc.get_scorecard()
    return {
        "game_id": game_id,
        "wins": wins,
        "score": scorecard.score if scorecard else 0.0,
        "actions": actions_taken,
        "targets_found": len(targets),
        "targets_clicked": target_idx,
    }


if __name__ == "__main__":
    for game_id in ["r11l", "lp85"]:
        result = run_object_clicker(game_id)
        print(
            f"{game_id}: wins={result['wins']}, score={result['score']}, "
            f"actions={result['actions']}, targets={result['targets_found']}, clicked={result['targets_clicked']}"
        )
