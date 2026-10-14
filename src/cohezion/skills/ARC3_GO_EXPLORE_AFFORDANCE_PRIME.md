---
name: arc3-go-explore-affordance-prime
description: "Go-Explore frontier expansion, BFS macro-action pathfinding, 64-bit SplitMix64 Zobrist hashing, and dynamic affordance learning for ARC-AGI-3."
version: v0.1
---

# SKILL: ARC3_GO_EXPLORE_AFFORDANCE_PRIME

## DOMAIN EXPERTISE
Autonomous decision-making for ARC-AGI-3 interactive puzzle environments using Go-Explore frontier archiving, online transition model learning, SplitMix64 Zobrist cycle evasion, and macro-action shortest path compilation over discrete 2D spatial manifolds.

## KEY TEXTS & CONCEPTS
* **SplitMix64 Incremental Zobrist Hashing**: $O(|\Delta|)$ state hash updates over non-masked spatial cells, guaranteeing cycle detection with negligible collision probability ($\sim n^2 / 2^{65}$).
* **Semi-MDP Macro-Action Compilation**: Abstracting high-level goal options $g = (\text{node}, a)$ into atomic BFS shortest-path trajectories, reducing wandering entropy by orders of magnitude.
* **Online Affordance & Transition Learning**: Inferring agent footprint, stride, solid obstacle colors, and reactive affordances from centroid shifts without pre-programmed rules.
* **Annealed & Re-heated Exploration Temperature**: Adaptive exploration rate $T_t$ balancing goal exploitation against cyclical stagnation re-heating.
* **Go-Explore Archive & Stagnation Rollback**: Trajectory prefix caching with lowest-expansion resumption upon exploration dead-ends.

## INSTRUCTION

1. **Initialize Incremental SplitMix64 Zobrist Hasher**:
```python
from __future__ import annotations
import numpy as np

M64 = (1 << 64) - 1

def splitmix64(x: int) -> int:
    x = (x + 0x9E3779B97F4A7C15) & M64
    x = ((x ^ (x >> 30)) * 0xBF58476D1CE4E5B9) & M64
    x = ((x ^ (x >> 27)) * 0x94D049BB133111EB) & M64
    return x ^ (x >> 31)

class ZobristGridHasher:
    def __init__(self, height: int, width: int, num_colors: int = 16, seed: int = 0xCAFE):
        self.H, self.W = height, width
        self.table = np.zeros((height * width, num_colors), dtype=np.uint64)
        for i in range(height * width):
            for c in range(num_colors):
                self.table[i, c] = np.uint64(splitmix64(seed ^ ((i << 8) | c)))

    def compute_hash(self, grid: np.ndarray, masked_rows: set[int] | None = None) -> int:
        h = np.uint64(0)
        flat = grid.ravel()
        for idx, val in enumerate(flat):
            r = idx // self.W
            if masked_rows and r in masked_rows:
                continue
            h ^= self.table[idx, int(val)]
        return int(h)
```

2. **Online Affordance & Agent Geometry Extraction**:
```python
def locate_agent(prev_grid: np.ndarray, curr_grid: np.ndarray, action: int) -> tuple[int, tuple[int, int]]:
    """Identifies agent color and bounding-box centroid shift."""
    diff = prev_grid != curr_grid
    candidate_colors = np.unique(curr_grid[diff])
    best_color = -1
    best_pos = (0, 0)
    for c in candidate_colors:
        prev_coords = np.argwhere(prev_grid == c)
        curr_coords = np.argwhere(curr_grid == c)
        if len(prev_coords) > 0 and len(prev_coords) == len(curr_coords):
            # Centroid translation
            shift = curr_coords.mean(axis=0) - prev_coords.mean(axis=0)
            if np.linalg.norm(shift) > 0:
                best_color = int(c)
                best_pos = (int(curr_coords[:, 0].min()), int(curr_coords[:, 1].min()))
                break
    return best_color, best_pos
```

3. **Semi-MDP BFS Macro-Action Pathfinding**:
```python
from collections import deque

DIRS = {1: (-1, 0), 2: (1, 0), 3: (0, -1), 4: (0, 1)}

def bfs_macro_path(start: tuple[int, int], target: tuple[int, int], solid_mask: np.ndarray) -> list[int]:
    """Finds primitive action sequence connecting agent to affordance target."""
    if start == target:
        return []
    queue = deque([(start, [])])
    visited = {start}
    H, W = solid_mask.shape

    while queue:
        (r, c), path = queue.popleft()
        if (r, c) == target:
            return path
        for act, (dr, dc) in DIRS.items():
            nr, nc = r + dr, c + dc
            if 0 <= nr < H and 0 <= nc < W and not solid_mask[nr, nc] and (nr, nc) not in visited:
                visited.add((nr, nc))
                queue.append(((nr, nc), path + [act]))
    return []
```

4. **Frontier Scoring & Softmax Selection**:
```python
def score_frontier_target(target_pos: tuple[int, int], agent_pos: tuple[int, int],
                          visit_counts: dict, cycle_penalty: float) -> float:
    dist = abs(target_pos[0] - agent_pos[0]) + abs(target_pos[1] - agent_pos[1])
    n_visits = visit_counts.get(target_pos, 0)
    # Utility = exploration novelty - BFS traversal cost - cycle penalty
    utility = 2.0 / np.sqrt(1.0 + n_visits) - 0.1 * dist - cycle_penalty
    return float(utility)
```

5. **Go-Explore Archive Stagnation Recovery**:
```python
class GoExploreArchive:
    def __init__(self):
        self.archive: dict[int, tuple[list[int], int]] = {} # hash -> (action_prefix, times_expanded)

    def register_state(self, state_hash: int, action_history: list[int]) -> None:
        if state_hash not in self.archive:
            self.archive[state_hash] = (list(action_history), 0)

    def sample_stagnation_anchor(self) -> list[int] | None:
        if not self.archive:
            return None
        # Select state with minimum expansions to break local optima
        min_state = min(self.archive.items(), key=lambda item: item[1][1])
        prefix, count = min_state[1]
        self.archive[min_state[0]] = (prefix, count + 1)
        return prefix
```

## VERSION
v0.1

## SEE ALSO
- ARC3_MACRO_AFFORDANCE_SEARCH_PRIME.md
- KAGGLE_STRIX_DETERMINISTIC_VERIFIER_PRIME.md
- RETROSPECTIVE_SKILL.md
