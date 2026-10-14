#!/usr/bin/env python3
"""Patch script to upgrade ARC-AGI-3 solver to SOTA v34:
Hierarchical Obstacle-Aware BFS Macro-Action Planner + Dynamic Affordance Sequencing.
"""

import json
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/cohezion-arc-agi-3-autoharness-solver/cohezion-arc-agi-3-autoharness-solver.ipynb")

NEW_CELL_1_CODE = """# 2. Cohezion ARC-AGI-3 SOTA v34: Hierarchical Obstacle-Aware BFS Macro Planner + Affordance Sequencing
# Lineage: v27 (0.13) -> v32 (0.16) -> v33 (0.21) -> v34 Hierarchical Macro Planner
import hashlib
import json
import logging
import os
import random
import sys
import time
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Set
import numpy as np

import arc_agi
import arcengine
from arcengine import GameAction, GameState, FrameDataRaw

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("CohezionARC3")

# Precomputed 64-bit SplitMix64 Zobrist table for 64x64 grids across 10 discrete colors
RNG = np.random.default_rng(20261012)
ZOBRIST_TABLE = RNG.integers(0, (1 << 62) - 1, size=(64, 64, 10), dtype=np.int64)

OPPOSITE_ACTION = {1: 2, 2: 1, 3: 4, 4: 3}  # Up <-> Down, Left <-> Right
MOVES_4WAY = [(-1, 0, 1), (1, 0, 2), (0, -1, 3), (0, 1, 4)] # dr, dc, action_id

def hash_frame(frame_layers: list) -> int:
    \"\"\"Vectorized 64-bit Zobrist XOR hash for O(1) grid state comparison.\"\"\"
    if not frame_layers or frame_layers[0] is None:
        return 0
    grid = frame_layers[0]
    h, w = grid.shape
    if h > 64 or w > 64:
        return int(hashlib.md5(np.ascontiguousarray(grid).tobytes()).hexdigest()[:15], 16)
    colors = np.clip(grid, 0, 9)
    r_idx = np.arange(h)[:, None]
    c_idx = np.arange(w)
    return int(np.bitwise_xor.reduce(ZOBRIST_TABLE[:h, :w, :][r_idx, c_idx, colors].ravel()))

def find_components(grid: np.ndarray) -> tuple[list[dict[str, Any]], int]:
    \"\"\"Extract foreground connected components sorted by color rarity ascending, then size ascending.\"\"\"
    h, w = grid.shape
    visited = np.zeros((h, w), dtype=bool)
    components = []
    vals, counts = np.unique(grid, return_counts=True)
    bg_color = int(vals[np.argmax(counts)])
    color_freq = dict(zip(vals, counts))

    for r in range(h):
        for c in range(w):
            if visited[r, c] or grid[r, c] == bg_color:
                continue
            color = int(grid[r, c])
            q = deque([(r, c)])
            visited[r, c] = True
            pixels = []
            while q:
                cr, cc = q.popleft()
                pixels.append((cr, cc))
                for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
                    nr, nc = cr + dr, cc + dc
                    if 0 <= nr < h and 0 <= nc < w and not visited[nr, nc] and grid[nr, nc] == color:
                        visited[nr, nc] = True
                        q.append((nr, nc))
            rs = [p[0] for p in pixels]
            cs = [p[1] for p in pixels]
            components.append({
                "color": color,
                "color_count": int(color_freq[color]),
                "size": len(pixels),
                "center_r": int(sum(rs) / len(rs)),
                "center_c": int(sum(cs) / len(cs)),
                "bbox": (min(rs), min(cs), max(rs), max(cs)),
                "pixels": pixels,
            })

    # Strict Action Economy: Target rarest single-pixel and small-sprite affordances first!
    components.sort(key=lambda c: (c["color_count"], c["size"]))
    return components, bg_color

def bfs_shortest_path(grid: np.ndarray, start: tuple[int, int], goal: tuple[int, int], walkable_colors: set[int]) -> list[int]:
    \"\"\"Obstacle-aware BFS shortest path avoiding walls and obstacles.\"\"\"
    h, w = grid.shape
    if start == goal:
        return []
    q = deque([start])
    parent = {start: None}
    action_taken = {}
    found = False

    while q:
        r, c = q.popleft()
        if (r, c) == goal:
            found = True
            break
        for dr, dc, act in MOVES_4WAY:
            nr, nc = r + dr, c + dc
            if 0 <= nr < h and 0 <= nc < w and (nr, nc) not in parent:
                # Target cell or walkable cell
                if (nr, nc) == goal or int(grid[nr, nc]) in walkable_colors:
                    parent[(nr, nc)] = (r, c)
                    action_taken[(nr, nc)] = act
                    q.append((nr, nc))

    if not found:
        return []

    # Reconstruct action sequence
    actions = []
    curr = goal
    while parent[curr] is not None:
        actions.append(action_taken[curr])
        curr = parent[curr]
    actions.reverse()
    return actions

class CohezionHierarchicalPlannerAgent:
    \"\"\"Hierarchical Planner Agent: Obstacle-aware BFS Macro-Actions + Affordance Sequencing.\"\"\"
    def __init__(self, game_id: str, seed: int = 42):
        self.game_id = game_id
        self.rng = random.Random(seed + hash(game_id) % 100000)
        self.transition_model: dict[int, dict[int, int]] = {}
        self.state_visits: dict[int, int] = {}
        self.state_action_visits: dict[tuple[int, int], int] = {}
        self.clicked_targets: dict[int, set[tuple[int, int]]] = {}
        self.last_state_hash: Optional[int] = None
        self.last_action_id: Optional[int] = None
        self.last_frame: Optional[np.ndarray] = None
        self.player_pos: Optional[tuple[int, int]] = None
        self.step_count = 0
        self.consecutive_loops = 0
        self.state_history: deque[int] = deque(maxlen=24)
        self.recent_hashes: deque[int] = deque(maxlen=8)
        self.planned_macro_actions: deque[int] = deque()
        self.visited_affordance_centers: set[tuple[int, int]] = set()

    def choose_action(self, obs: FrameDataRaw) -> tuple[GameAction, Optional[dict[str, Any]]]:
        self.step_count += 1
        curr_hash = hash_frame(obs.frame)
        self.state_visits[curr_hash] = self.state_visits.get(curr_hash, 0) + 1
        grid = obs.frame[0] if obs.frame else None

        # Track avatar position from frame delta on directional movement
        if self.last_frame is not None and grid is not None and self.last_action_id in (1, 2, 3, 4):
            diff = (grid != self.last_frame)
            if 0 < np.sum(diff) <= 64:
                coords = np.argwhere(diff)
                self.player_pos = (int(np.mean(coords[:, 0])), int(np.mean(coords[:, 1])))

        self.last_frame = grid.copy() if grid is not None else None

        # Track state transitions and consecutive self-loops (wall collisions & orbit traps)
        is_cycle = False
        if self.last_state_hash is not None and self.last_action_id is not None:
            if self.last_state_hash not in self.transition_model:
                self.transition_model[self.last_state_hash] = {}
            self.transition_model[self.last_state_hash][self.last_action_id] = curr_hash
            sa_pair = (self.last_state_hash, self.last_action_id)
            self.state_action_visits[sa_pair] = self.state_action_visits.get(sa_pair, 0) + 1

            if curr_hash == self.last_state_hash:
                self.consecutive_loops += 1
                is_cycle = True
                self.planned_macro_actions.clear()  # Invalidate plan on collision
            elif len(self.state_history) >= 2 and curr_hash == self.state_history[-2]:
                self.consecutive_loops += 1
                is_cycle = True
                self.planned_macro_actions.clear()
            elif curr_hash in self.recent_hashes:
                self.consecutive_loops += 1
                is_cycle = True
            else:
                self.consecutive_loops = 0

        self.state_history.append(curr_hash)
        self.recent_hashes.append(curr_hash)

        avail = obs.available_actions
        simple_ids = [a for a in avail if a not in (0, 6, 7)]
        has_click = 6 in avail

        if curr_hash not in self.clicked_targets:
            self.clicked_targets[curr_hash] = set()

        comps, bg_color = find_components(grid) if grid is not None else ([], 0)

        # 1. Click handling: Trigger on unclicked affordances, or breakout if trapped in loops
        if has_click and (not simple_ids or self.consecutive_loops >= 2 or self.rng.random() < 0.30):
            unclicked = [c for c in comps if (c["center_c"], c["center_r"]) not in self.clicked_targets[curr_hash]]
            if unclicked:
                target = unclicked[0]
                coord = (target["center_c"], target["center_r"])
                self.clicked_targets[curr_hash].add(coord)
                self.last_state_hash = curr_hash
                self.last_action_id = 6
                self.planned_macro_actions.clear()
                return GameAction.ACTION6, {"x": coord[0], "y": coord[1]}
            elif comps and not simple_ids:
                target = self.rng.choice(comps)
                r_min, c_min, r_max, c_max = target["bbox"]
                coord = (self.rng.randint(c_min, c_max), self.rng.randint(r_min, r_max))
                self.last_state_hash = curr_hash
                self.last_action_id = 6
                self.planned_macro_actions.clear()
                return GameAction.ACTION6, {"x": coord[0], "y": coord[1]}

        # 2. Obstacle-Aware Macro-Action Follower
        if self.planned_macro_actions and simple_ids:
            next_macro_act = self.planned_macro_actions.popleft()
            if next_macro_act in simple_ids:
                self.last_state_hash = curr_hash
                self.last_action_id = next_macro_act
                return GameAction.from_id(next_macro_act), None

        # 3. Hierarchical BFS Macro-Action Planning towards Unvisited Affordances
        if simple_ids and self.player_pos is not None and grid is not None and comps:
            walkable = {bg_color, 0}
            pr, pc = self.player_pos

            # If current avatar position matches an affordance center, mark it visited
            self.visited_affordance_centers.add((pr, pc))

            # Sequence candidate affordances prioritizing unvisited
            unvisited_comps = [c for c in comps if (c["center_r"], c["center_c"]) not in self.visited_affordance_centers]
            candidate_targets = unvisited_comps if unvisited_comps else comps

            for cand in candidate_targets[:4]:
                tr, tc = cand["center_r"], cand["center_c"]
                path = bfs_shortest_path(grid, (pr, pc), (tr, tc), walkable)
                if path:
                    # Valid obstacle-free macro-action path found!
                    first_act = path[0]
                    if len(path) > 1:
                        self.planned_macro_actions = deque(path[1:])
                    self.last_state_hash = curr_hash
                    self.last_action_id = first_act
                    return GameAction.from_id(first_act), None

        # 4. Fallback: Directed Movement with Markov Cycle Evasion
        if simple_ids:
            known = self.transition_model.get(curr_hash, {})
            preferred_scores = {a: 0.0 for a in simple_ids}

            if self.player_pos is not None and comps:
                pr, pc = self.player_pos
                target = comps[0]
                tr, tc = target["center_r"], target["center_c"]
                dr, dc = tr - pr, tc - pc
                if abs(dr) > abs(dc):
                    preferred = [1 if dr < 0 else 2, 3 if dc < 0 else 4]
                else:
                    preferred = [3 if dc < 0 else 4, 1 if dr < 0 else 2]
                for idx, act_id in enumerate(preferred):
                    if act_id in preferred_scores:
                        preferred_scores[act_id] -= (10.0 - idx * 4.0)

            action_penalties = {}
            for act_id in simple_ids:
                penalty = preferred_scores[act_id]

                if is_cycle and self.last_action_id in OPPOSITE_ACTION:
                    if act_id == OPPOSITE_ACTION[self.last_action_id]:
                        penalty += 50.0

                if act_id in known:
                    next_s = known[act_id]
                    if next_s == curr_hash:
                        penalty += 100.0
                    if next_s in self.recent_hashes:
                        penalty += 35.0 * (self.recent_hashes.count(next_s) + 1)
                    penalty += 2.0 * self.state_visits.get(next_s, 0)
                else:
                    penalty -= 5.0

                sa_pair = (curr_hash, act_id)
                penalty += 1.0 * self.state_action_visits.get(sa_pair, 0)
                action_penalties[act_id] = penalty

            chosen_id = min(simple_ids, key=lambda a: action_penalties[a])
            self.last_state_hash = curr_hash
            self.last_action_id = chosen_id
            return GameAction.from_id(chosen_id), None

        fallback_id = avail[0] if avail else 0
        return GameAction.from_id(fallback_id), None

# Backward compatibility aliases
CohezionRaritySearchAgent = CohezionHierarchicalPlannerAgent
CohezionGoExploreAgent = CohezionHierarchicalPlannerAgent
CohezionDirectedRarityAgent = CohezionHierarchicalPlannerAgent
CohezionMonadicMarkovRarityAgent = CohezionHierarchicalPlannerAgent
"""

with open(NOTEBOOK_PATH, "r") as f:
    nb = json.load(f)

# Replace Cell 1 source
nb["cells"][1]["source"] = [NEW_CELL_1_CODE]

with open(NOTEBOOK_PATH, "w") as f:
    json.dump(nb, f, indent=1)

print(f"✓ Successfully patched {NOTEBOOK_PATH} with SOTA v34 Hierarchical Macro Planner!")
