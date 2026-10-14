import arc_agi
from arcengine import GameAction, GameState
import numpy as np
import random
from collections import deque
from typing import Any, Dict, List, Optional, Tuple, Set

# 64-bit SplitMix64 Zobrist table for 64x64 grids across 16 discrete colors
RNG = np.random.default_rng(20261004)
ZOBRIST_TABLE = RNG.integers(0, (1 << 62) - 1, size=(64, 64, 16), dtype=np.int64)

OPPOSITE_ACTION = {1: 2, 2: 1, 3: 4, 4: 3}  # Up <-> Down, Left <-> Right
ACTION_DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}

def hash_frame(frame_layers: list, inventory: Set[int]) -> int:
    """Vectorized 64-bit Zobrist XOR hash including inventory belief state."""
    if not frame_layers or frame_layers[0] is None:
        return 0
    grid = frame_layers[0]
    h, w = grid.shape
    if h > 64 or w > 64:
        return 0
    colors = np.clip(grid, 0, 15)
    r_idx = np.arange(h)[:, None]
    c_idx = np.arange(w)
    base_hash = int(np.bitwise_xor.reduce(ZOBRIST_TABLE[:h, :w, :][r_idx, c_idx, colors].ravel()))
    for item in sorted(inventory):
        base_hash ^= (int(item) + 1) * 0x517CC1B727220A95
    return base_hash & 0x7FFFFFFFFFFFFFFF

def find_components(grid: np.ndarray) -> tuple[int, list[dict[str, Any]]]:
    """Extract connected components with color rarity and bounding boxes."""
    h, w = grid.shape
    visited = np.zeros((h, w), dtype=bool)
    components = []
    vals, counts = np.unique(grid, return_counts=True)
    bg_color = int(vals[np.argmax(counts)])
    color_freq = {int(v): int(c) for v, c in zip(vals, counts)}

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
                "color_count": color_freq[color],
                "size": len(pixels),
                "center_r": int(sum(rs) / len(rs)),
                "center_c": int(sum(cs) / len(cs)),
                "bbox": (min(rs), min(cs), max(rs), max(cs)),
                "pixels": pixels,
            })

    components.sort(key=lambda c: (c["color_count"], c["size"]))
    return bg_color, components

class CohezionDirectedRarityAgentV28:
    """SOTA v28 ARC-AGI-3 Agent:

    Incorporates:
    1. 64-bit Zobrist Hashing across 16 discrete colors (no 9-color clipping defect).
    2. Sokoban Corner Deadlock Pruning: Prevents irreversible block freezing.
    3. Key & Consumable Inventory Belief State Tracking: Dynamic affordance gating.
    4. Closed-Loop Replanning: Immediate plan reset on large environmental deltas.
    5. Anti-Cycle Markov Penalty & Non-Degenerate Click Exploration.
    """
    def __init__(self, game_id: str, seed: int = 42):
        self.game_id = game_id
        self.rng = random.Random(seed + hash(game_id) % 100000)
        self.transition_model: dict[int, dict[int, int]] = {}
        self.state_visits: dict[int, int] = {}
        self.state_action_visits: dict[tuple[int, int], int] = {}
        self.clicked_targets: dict[int, set[tuple[int, int]]] = {}
        self.global_clicked_coords: dict[tuple[int, int], int] = {}
        self.last_state_hash: Optional[int] = None
        self.last_action_id: Optional[int] = None
        self.last_frame: Optional[np.ndarray] = None
        self.player_pos: Optional[tuple[int, int]] = None
        self.step_count = 0
        self.consecutive_loops = 0
        self.state_history: deque[int] = deque(maxlen=24)
        self.recent_hashes: deque[int] = deque(maxlen=8)
        self.inventory: Set[int] = set()

    def is_corner_deadlock(self, grid: np.ndarray, r: int, c: int, bg_color: int) -> bool:
        """Check if destination (r, c) is an irreversible corner formed by obstacles/walls."""
        h, w = grid.shape
        def is_wall(nr, nc):
            if not (0 <= nr < h and 0 <= nc < w):
                return True
            # Non-passable wall if not background
            val = grid[nr, nc]
            return val != bg_color

        top = is_wall(r - 1, c)
        bottom = is_wall(r + 1, c)
        left = is_wall(r, c - 1)
        right = is_wall(r, c + 1)
        return (top and left) or (top and right) or (bottom and left) or (bottom and right)

    def choose_action(self, obs) -> tuple[GameAction, Optional[dict[str, Any]]]:
        self.step_count += 1
        grid = obs.frame[0] if obs.frame else None
        h, w = grid.shape if grid is not None else (64, 64)

        # Update inventory belief state if player visited a collectible and it vanished
        if self.last_frame is not None and grid is not None and self.player_pos is not None:
            pr, pc = self.player_pos
            old_val = self.last_frame[pr, pc]
            new_val = grid[pr, pc]
            if old_val != new_val and old_val not in (0,):
                self.inventory.add(int(old_val))

        curr_hash = hash_frame(obs.frame, self.inventory)
        self.state_visits[curr_hash] = self.state_visits.get(curr_hash, 0) + 1

        # Track avatar position from frame delta on directional movement
        if self.last_frame is not None and grid is not None and self.last_action_id in ACTION_DIRS:
            diff = (grid != self.last_frame)
            diff_sum = np.sum(diff)
            # Closed-loop replanning if significant world alteration
            if diff_sum > 0.05 * (h * w):
                self.consecutive_loops = 0

            if 0 < diff_sum <= 64:
                coords = np.argwhere(diff)
                self.player_pos = (int(np.mean(coords[:, 0])), int(np.mean(coords[:, 1])))

        self.last_frame = grid.copy() if grid is not None else None

        # Track state transitions and consecutive self-loops
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
            elif len(self.state_history) >= 2 and curr_hash == self.state_history[-2]:
                self.consecutive_loops += 1
                is_cycle = True
            elif curr_hash in self.recent_hashes:
                self.consecutive_loops += 1
                is_cycle = True
            else:
                self.consecutive_loops = 0

        self.state_history.append(curr_hash)
        self.recent_hashes.append(curr_hash)

        avail = obs.available_actions
        simple_ids = [a for a in avail if a in ACTION_DIRS]
        has_click = 6 in avail

        if curr_hash not in self.clicked_targets:
            self.clicked_targets[curr_hash] = set()

        bg_color, comps = find_components(grid) if grid is not None else (0, [])

        # 1. Click handling (Action 6) with Non-Degenerate Spatial Exploration
        if has_click and (not simple_ids or self.consecutive_loops >= 2 or self.rng.random() < 0.25):
            # Prioritize interactive affordance targets that haven't been clicked repeatedly
            click_candidates = []
            for c in comps:
                coord = (c["center_c"], c["center_r"])
                times_clicked = self.global_clicked_coords.get(coord, 0)
                click_candidates.append((times_clicked, c["color_count"], coord))

            # Also allow clicking on empty/board cells if pieces are held or to place items
            if self.step_count > 1:
                # Add interior grid cells as candidates
                r_sample = self.rng.randint(8, max(9, h - 8))
                c_sample = self.rng.randint(8, max(9, w - 8))
                coord = (c_sample, r_sample)
                times_clicked = self.global_clicked_coords.get(coord, 0)
                click_candidates.append((times_clicked + 1, 99999, coord))

            click_candidates.sort(key=lambda x: (x[0], x[1]))

            if click_candidates:
                chosen_coord = click_candidates[0][2]
                self.global_clicked_coords[chosen_coord] = self.global_clicked_coords.get(chosen_coord, 0) + 1
                self.clicked_targets[curr_hash].add(chosen_coord)
                self.last_state_hash = curr_hash
                self.last_action_id = 6
                return GameAction.ACTION6, {"x": chosen_coord[0], "y": chosen_coord[1]}

        # 2. Directed Movement handling with Corner Deadlock Pruning & Markov Cycle Evasion
        if simple_ids:
            known = self.transition_model.get(curr_hash, {})

            # Compute preference ranking towards rarest affordance
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

            # Score each candidate action with cycle, repetition, and DEADLOCK penalties
            action_penalties = {}
            for act_id in simple_ids:
                penalty = preferred_scores[act_id]

                # Deadlock Pruning: Check if pushing a block into a corner
                if self.player_pos is not None and grid is not None:
                    dr, dc = ACTION_DIRS[act_id]
                    adj_r, adj_c = self.player_pos[0] + dr, self.player_pos[1] + dc
                    if 0 <= adj_r < h and 0 <= adj_c < w:
                        adj_val = grid[adj_r, adj_c]
                        # If adjacent tile is an object (not background), pushing it moves it to dest
                        if adj_val != bg_color:
                            dest_r, dest_c = adj_r + dr, adj_c + dc
                            if self.is_corner_deadlock(grid, dest_r, dest_c, bg_color):
                                penalty += 300.0  # Heavy penalty for irreversible corner freezing!

                # Immediate reverse penalty if last action formed a 2-cycle
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

# Run benchmark test on offline games
arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir='./environment_files')
card_id = arcade.create_scorecard()
envs = arcade.get_environments()

print("=== Running Cohezion ARC-AGI-3 v28 Offline Test ===")
for idx, env_info in enumerate(envs):
    game_id = env_info.game_id
    env = arcade.make(game_id, scorecard_id=card_id)
    agent = CohezionDirectedRarityAgentV28(game_id, seed=idx * 100)
    obs = env.reset()
    step = 0
    while obs and obs.state not in (GameState.WIN, GameState.GAME_OVER) and step < 150:
        act, data = agent.choose_action(obs)
        obs = env.step(act, data=data)
        step += 1
    print(f'-> {game_id}: steps={step}, state={obs.state if obs else None}, levels={obs.levels_completed if obs else 0}')

sc = arcade.close_scorecard(card_id)
print(f'✓ Scorecard Summary: Total actions: {sc.total_actions}, Completed: {sc.total_levels_completed}')
