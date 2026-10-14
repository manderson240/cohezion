import arc_agi
from arcengine import GameAction, GameState
import numpy as np
import random
from collections import deque
from typing import Any, Dict, List, Optional, Tuple, Set

# 64-bit SplitMix64 Zobrist table for 64x64 grids across 16 discrete colors (preserves 20261002 seed)
RNG = np.random.default_rng(20261002)
ZOBRIST_TABLE = RNG.integers(0, (1 << 62) - 1, size=(64, 64, 16), dtype=np.int64)

OPPOSITE_ACTION = {1: 2, 2: 1, 3: 4, 4: 3}  # Up <-> Down, Left <-> Right
ACTION_DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}

def hash_frame(frame_layers: list) -> int:
    """Vectorized 64-bit Zobrist XOR hash for O(1) grid state comparison across 16 colors."""
    if not frame_layers or frame_layers[0] is None:
        return 0
    grid = frame_layers[0]
    h, w = grid.shape
    if h > 64 or w > 64:
        return 0
    colors = np.clip(grid, 0, 15)
    r_idx = np.arange(h)[:, None]
    c_idx = np.arange(w)
    return int(np.bitwise_xor.reduce(ZOBRIST_TABLE[:h, :w, :][r_idx, c_idx, colors].ravel()))

def find_components(grid: np.ndarray) -> list[dict[str, Any]]:
    """Extract foreground connected components sorted by color rarity ascending, then size ascending."""
    h, w = grid.shape
    visited = np.zeros((h, w), dtype=bool)
    components = []
    vals, counts = np.unique(grid, return_counts=True)
    bg_color = vals[np.argmax(counts)]
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
            })

    components.sort(key=lambda c: (c["color_count"], c["size"]))
    return components

class CohezionDirectedRarityAgentV28:
    """Affordance-targeted search agent with Markov cycle evasion, 16-color Zobrist hashing, and corner deadlock pruning."""
    def __init__(self, game_id: str, seed: int = 42):
        self.game_id = game_id
        self.rng = random.Random(seed + hash(game_id) % 100000)
        self.transition_model: dict[int, dict[int, int]] = {}
        self.state_visits: dict[int, int] = {}
        self.state_action_visits: dict[tuple[int, int], int] = {}
        self.clicked_targets: dict[int, set[tuple[int, int]]] = {}
        self.consecutive_no_op_clicks = 0
        self.last_state_hash: Optional[int] = None
        self.last_action_id: Optional[int] = None
        self.last_frame: Optional[np.ndarray] = None
        self.player_pos: Optional[tuple[int, int]] = None
        self.step_count = 0
        self.consecutive_loops = 0
        self.state_history: deque[int] = deque(maxlen=24)
        self.recent_hashes: deque[int] = deque(maxlen=8)

    def is_corner_deadlock(self, grid: np.ndarray, r: int, c: int, bg_color: int) -> bool:
        """Check if destination (r, c) is an irreversible non-goal corner."""
        h, w = grid.shape
        def is_wall(nr, nc):
            return not (0 <= nr < h and 0 <= nc < w) or grid[nr, nc] != bg_color
        top = is_wall(r - 1, c)
        bottom = is_wall(r + 1, c)
        left = is_wall(r, c - 1)
        right = is_wall(r, c + 1)
        return (top and left) or (top and right) or (bottom and left) or (bottom and right)

    def choose_action(self, obs) -> tuple[GameAction, Optional[dict[str, Any]]]:
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

        # Check if last click was a no-op (no frame change)
        if self.last_frame is not None and grid is not None and self.last_action_id == 6:
            if np.array_equal(grid, self.last_frame):
                self.consecutive_no_op_clicks += 1
            else:
                self.consecutive_no_op_clicks = 0

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
        simple_ids = [a for a in avail if a not in (0, 6, 7)]
        has_click = 6 in avail

        if curr_hash not in self.clicked_targets:
            self.clicked_targets[curr_hash] = set()

        comps = find_components(grid) if grid is not None else []
        bg_color = 0
        if grid is not None:
            vals, counts = np.unique(grid, return_counts=True)
            bg_color = int(vals[np.argmax(counts)])

        # 1. Click handling: Trigger on unclicked affordances, or breakout if trapped in loops
        if has_click and (not simple_ids or self.consecutive_loops >= 2 or self.rng.random() < 0.35):
            unclicked = [c for c in comps if (c["center_c"], c["center_r"]) not in self.clicked_targets[curr_hash]]
            if unclicked:
                target = unclicked[0]
                coord = (target["center_c"], target["center_r"])
                self.clicked_targets[curr_hash].add(coord)
                self.last_state_hash = curr_hash
                self.last_action_id = 6
                return GameAction.ACTION6, {"x": coord[0], "y": coord[1]}
            elif comps and not simple_ids:
                # Cycle click positions within bounding boxes to prevent lock
                target = self.rng.choice(comps)
                r_min, c_min, r_max, c_max = target["bbox"]
                coord = (self.rng.randint(c_min, c_max), self.rng.randint(r_min, r_max))
                self.last_state_hash = curr_hash
                self.last_action_id = 6
                return GameAction.ACTION6, {"x": coord[0], "y": coord[1]}

        # 2. Directed Movement handling with Markov Cycle Evasion & Deadlock Pruning
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

                # Deadlock Pruning: Check if pushing a block into a corner
                if self.player_pos is not None and grid is not None and act_id in ACTION_DIRS:
                    dr, dc = ACTION_DIRS[act_id]
                    adj_r, adj_c = self.player_pos[0] + dr, self.player_pos[1] + dc
                    h, w = grid.shape
                    if 0 <= adj_r < h and 0 <= adj_c < w:
                        adj_val = grid[adj_r, adj_c]
                        if adj_val != bg_color:
                            dest_r, dest_c = adj_r + dr, adj_c + dc
                            if self.is_corner_deadlock(grid, dest_r, dest_c, bg_color):
                                penalty += 300.0  # Irreversible deadlock penalty

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

arcade = arc_agi.Arcade(operation_mode=arc_agi.OperationMode.OFFLINE, environments_dir='./environment_files')
card_id = arcade.create_scorecard()
envs = arcade.get_environments()

print("=== Running Refined Cohezion ARC-AGI-3 v28 Offline Test ===")
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
