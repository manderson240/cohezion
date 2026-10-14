"""arc3_macro_action_compiler.py

Standalone macro-action compiler for the ARC Prize 2026 ARC-AGI-3 Interactive
Agent competition. Drop-in ready for Kaggle kernels: pure standard library,
no third-party imports, CPython 3.8+.

Components
----------
ZobristStateHasher
    64-bit SplitMix64 Zobrist hashing for O(1)-amortised cycle/loop detection.
AffordanceDetector
    Finds frontier boundary cells, dynamic objects (small connected colour
    patches / pushable blocks / moving entities) and goal/terminal targets
    (colour-match targets, doors, exits mapped onto a goal-colour set).
MacroActionCompiler
    BFS shortest-path planning over passable terrain, translation of the path
    into a discrete action sequence, and early-break validation against
    unexpected environment transitions.
AdaptiveBudgetManager
    Step allocation under the quadratic-decay score

        Score(t) = max(0, 1 - (t / H)^2)

    switching from novelty-driven exploration (t << H) to greedy goal
    convergence once t reaches 0.6 * H.

Conventions
-----------
* Positions are ``(row, col)`` with ``row 0`` at the top and ``col 0`` at
  the left.
* Action codes:

      0 = UP     (row - 1)
      1 = DOWN   (row + 1)
      2 = LEFT   (col - 1)
      3 = RIGHT  (col + 1)
      4 = INTERACT / SPACE

* Colour token ``0`` is the default background / walkable terrain. The
  passable set is configurable so agents can learn walkable colours online.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Sequence, Set, Tuple

__all__ = [
    "ACTION_UP",
    "ACTION_DOWN",
    "ACTION_LEFT",
    "ACTION_RIGHT",
    "ACTION_INTERACT",
    "ZobristStateHasher",
    "AffordanceDetector",
    "Affordances",
    "ObjectRegion",
    "MacroActionCompiler",
    "MacroPlan",
    "StepExpectation",
    "AdaptiveBudgetManager",
]

# ---------------------------------------------------------------------------
# Action codes and geometry helpers
# ---------------------------------------------------------------------------

ACTION_UP = 0
ACTION_DOWN = 1
ACTION_LEFT = 2
ACTION_RIGHT = 3
ACTION_INTERACT = 4

_ACTION_DELTAS: Dict[int, Tuple[int, int]] = {
    ACTION_UP: (-1, 0),
    ACTION_DOWN: (1, 0),
    ACTION_LEFT: (0, -1),
    ACTION_RIGHT: (0, 1),
    ACTION_INTERACT: (0, 0),
}

Grid = List[List[int]]
Position = Tuple[int, int]


def _manhattan(a: Position, b: Position) -> int:
    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def _neighbors(r: int, c: int, rows: int, cols: int) -> Iterable[Position]:
    if r > 0:
        yield (r - 1, c)
    if r + 1 < rows:
        yield (r + 1, c)
    if c > 0:
        yield (r, c - 1)
    if c + 1 < cols:
        yield (r, c + 1)


def _delta_to_action(dr: int, dc: int) -> int:
    if dr == -1 and dc == 0:
        return ACTION_UP
    if dr == 1 and dc == 0:
        return ACTION_DOWN
    if dr == 0 and dc == -1:
        return ACTION_LEFT
    if dr == 0 and dc == 1:
        return ACTION_RIGHT
    raise ValueError(f"non-unit move delta ({dr}, {dc})")


def _copy_grid(grid: Grid) -> Grid:
    return [list(row) for row in grid]


def _grids_equal(a: Sequence, b: Sequence) -> bool:
    if a is b:
        return True
    if len(a) != len(b):
        return False
    for ra, rb in zip(a, b):
        if len(ra) != len(rb):
            return False
        for ca, cb in zip(ra, rb):
            if ca != cb:
                return False
    return True


# ---------------------------------------------------------------------------
# 1. ZobristStateHasher
# ---------------------------------------------------------------------------

class ZobristStateHasher:
    """64-bit Zobrist hashing for instant cycle/loop detection on 2D grids.

    Every ``(colour, cell)`` pair is assigned an independent 64-bit integer
    drawn from a SplitMix64 sequence. The hash of a state is the XOR of the
    entries for every cell in the grid, so:

    * hashing a state is O(rows * cols);
    * hashing a *changed* state is O(1) via :meth:`update`;
    * a revisited state yields a byte-identical hash, so keeping a ``set`` of
      hashes detects cycles/loops in constant time (see :meth:`first_repeated`).
    """

    _MASK64 = 0xFFFFFFFFFFFFFFFF

    def __init__(
        self,
        max_size: int = 64,
        num_colors: int = 16,
        seed: int = 0x9E3779B97F4A7C15,
    ) -> None:
        if max_size < 1:
            raise ValueError("max_size must be >= 1")
        if num_colors < 1:
            raise ValueError("num_colors must be >= 1")
        self.max_size = int(max_size)
        self.num_colors = int(num_colors)
        self.seed = int(seed)
        self._table: List[List[int]] = self._build_table()

    @classmethod
    def _splitmix64(cls, x: int) -> int:
        x = (x + 0x9E3779B97F4A7C15) & cls._MASK64
        x = (x ^ (x >> 30)) * 0xBF58476D1CE4E5B9 & cls._MASK64
        x = (x ^ (x >> 27)) * 0x94D049BB133111EB & cls._MASK64
        return x ^ (x >> 31)

    def _build_table(self) -> List[List[int]]:
        table: List[List[int]] = []
        state = self.seed
        cells = self.max_size * self.max_size
        for _ in range(self.num_colors):
            row: List[int] = [0] * cells
            for i in range(cells):
                state = self._splitmix64(state)
                row[i] = state
            table.append(row)
        return table

    def _entry(self, color: int, index: int) -> int:
        color = int(color)
        if 0 <= color < self.num_colors:
            return self._table[color][index]
        # Out-of-range token: derive a stable independent entry on the fly.
        return (
            self._splitmix64(
                (color * 0x9E3779B97F4A7C15) ^ (index * 0x94D049BB133111EB)
            )
            & self._MASK64
        )

    def hash_grid(self, grid: Grid) -> int:
        """Return the 64-bit Zobrist hash of *grid* (sequence of sequences)."""
        n = self.max_size
        h = 0
        for r, row in enumerate(grid):
            if r >= n:
                break
            base = r * n
            for c, color in enumerate(row):
                if c >= n:
                    break
                h ^= self._entry(color, base + c)
        # Fold dimensions in so differently-shaped grids never alias.
        h ^= self._splitmix64(len(grid))
        h ^= self._splitmix64(len(grid[0]) if grid else 0)
        return h & self._MASK64

    def update(
        self,
        current_hash: int,
        cell: Position,
        old_color: int,
        new_color: int,
    ) -> int:
        """O(1) update of *current_hash* when ``cell`` changes colour."""
        r, c = cell
        if not (0 <= r < self.max_size and 0 <= c < self.max_size):
            raise ValueError(f"cell {cell} out of range (max_size={self.max_size})")
        index = r * self.max_size + c
        h = current_hash
        h ^= self._entry(old_color, index)
        h ^= self._entry(new_color, index)
        return h & self._MASK64

    def first_repeated(self, grids: Iterable[Grid]) -> Optional[int]:
        """Return the index of the first grid that repeats an earlier state,
        or ``None`` if no cycle exists."""
        seen: Set[int] = set()
        for i, grid in enumerate(grids):
            h = self.hash_grid(grid)
            if h in seen:
                return i
            seen.add(h)
        return None


# ---------------------------------------------------------------------------
# 2. AffordanceDetector
# ---------------------------------------------------------------------------

@dataclass
class ObjectRegion:
    """A connected patch of a single non-passable colour."""

    color: int
    cells: List[Position]
    size: int
    centroid: Tuple[float, float]  # (mean_row, mean_col)
    bbox: Tuple[int, int, int, int]  # (min_r, min_c, max_r, max_c)

    @property
    def center(self) -> Position:
        return (int(round(self.centroid[0])), int(round(self.centroid[1])))


@dataclass
class Affordances:
    """Interactive targets discovered on a grid."""

    frontiers: List[Position]
    dynamic_objects: List[ObjectRegion]
    goals: List[Position]
    passable: Set[int]


class AffordanceDetector:
    """Discovers interactive entities on a 2D grid.

    Three target classes are produced:

    * **Frontier boundary cells** -- passable cells immediately adjacent to
      visited space but not yet visited themselves. These are the growth
      points for exploration.
    * **Dynamic objects** -- connected patches (4-connectivity) of
      non-passable, non-background colour whose area is at most
      ``max_dynamic_size``. Small moving entities, pushable blocks and
      distinct colour patches all fall into this bucket.
    * **Goal / terminal targets** -- cells whose colour belongs to
      ``goal_colors`` (colour-match targets, doors, exits). Map the task's
      terminal tokens into this set before calling :meth:`detect`.
    """

    def __init__(
        self,
        background: int = 0,
        passable: Optional[Iterable[int]] = None,
        goal_colors: Optional[Iterable[int]] = None,
        max_dynamic_size: int = 25,
    ) -> None:
        self.background = int(background)
        self.passable: Set[int] = (
            set(int(v) for v in passable)
            if passable is not None
            else {self.background}
        )
        self.goal_colors: Set[int] = (
            set(int(v) for v in goal_colors) if goal_colors is not None else set()
        )
        self.max_dynamic_size = max_dynamic_size

    def is_passable(self, color: int) -> bool:
        return int(color) in self.passable

    def detect(
        self,
        grid: Grid,
        agent: Position,
        visited: Optional[Set[Position]] = None,
    ) -> Affordances:
        """Detect frontiers, dynamic objects and goals around *agent*.

        ``visited`` is the set of cells the agent has already explored;
        it defaults to just the agent's own cell.
        """
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        if visited is None:
            visited = {agent}

        # --- frontier boundary cells --------------------------------------
        frontiers: List[Position] = []
        seen: Set[Position] = set()
        for (vr, vc) in visited:
            if not (0 <= vr < rows and 0 <= vc < cols):
                continue
            for (nr, nc) in _neighbors(vr, vc, rows, cols):
                if (nr, nc) in visited or (nr, nc) in seen:
                    continue
                if self.is_passable(grid[nr][nc]):
                    seen.add((nr, nc))
                    frontiers.append((nr, nc))

        # --- dynamic objects ----------------------------------------------
        dynamic = [
            comp for comp in self._components(grid) if comp.size <= self.max_dynamic_size
        ]

        # --- goal / terminal targets --------------------------------------
        goals: List[Position] = [
            (r, c)
            for r in range(rows)
            for c in range(cols)
            if int(grid[r][c]) in self.goal_colors
        ]

        return Affordances(
            frontiers=frontiers,
            dynamic_objects=dynamic,
            goals=goals,
            passable=set(self.passable),
        )

    def _components(self, grid: Grid) -> List[ObjectRegion]:
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        seen = [[False] * cols for _ in range(rows)]
        comps: List[ObjectRegion] = []
        for r in range(rows):
            for c in range(cols):
                color = int(grid[r][c])
                if color == self.background or self.is_passable(color) or seen[r][c]:
                    continue
                cells: List[Position] = []
                q = deque([(r, c)])
                seen[r][c] = True
                sum_r = 0
                sum_c = 0
                min_r = max_r = r
                min_c = max_c = c
                while q:
                    cr, cc = q.popleft()
                    cells.append((cr, cc))
                    sum_r += cr
                    sum_c += cc
                    for (nr, nc) in _neighbors(cr, cc, rows, cols):
                        if not seen[nr][nc] and int(grid[nr][nc]) == color:
                            seen[nr][nc] = True
                            q.append((nr, nc))
                            min_r = min(min_r, nr)
                            max_r = max(max_r, nr)
                            min_c = min(min_c, nc)
                            max_c = max(max_c, nc)
                size = len(cells)
                comps.append(
                    ObjectRegion(
                        color=color,
                        cells=cells,
                        size=size,
                        centroid=(sum_r / size, sum_c / size),
                        bbox=(min_r, min_c, max_r, max_c),
                    )
                )
        return comps


# ---------------------------------------------------------------------------
# 3. MacroActionCompiler
# ---------------------------------------------------------------------------

@dataclass
class StepExpectation:
    """Predicted outcome of a single action, used for early-break checks."""

    action: int
    position: Position
    grid: Grid
    validatable: bool  # False for INTERACT (outcome is environment-defined)


@dataclass
class MacroPlan:
    """A compiled macro-action: path + actions + per-step expectations."""

    start: Position
    target: Position
    path: List[Position]  # includes start, ends at the arrival cell
    actions: List[int]
    expectations: List[StepExpectation]  # aligned with ``actions``
    interact: bool

    @property
    def n_steps(self) -> int:
        return len(self.actions)


class MacroActionCompiler:
    """BFS planner + action-sequence compiler over passable terrain.

    The planner performs 4-connected BFS from the agent to the target (or,
    when the target cell itself is not passable, to the nearest passable cell
    adjacent to it). The recovered shortest path is converted into a discrete
    action sequence; an ``INTERACT`` action is appended when the target
    requires interaction.

    Execution is validated with :meth:`should_break`: after each action, if
    the observed agent position (or grid) diverges from the compiled
    expectation, the macro-action aborts early instead of blindly replaying
    a stale plan.
    """

    def __init__(
        self,
        background: int = 0,
        passable: Optional[Iterable[int]] = None,
        pushable: Optional[Iterable[int]] = None,
    ) -> None:
        self.background = int(background)
        self.passable: Set[int] = (
            set(int(v) for v in passable)
            if passable is not None
            else {self.background}
        )
        self.pushable: Set[int] = (
            set(int(v) for v in pushable) if pushable is not None else set()
        )

    def is_passable(self, color: int) -> bool:
        return int(color) in self.passable

    # -- planning ----------------------------------------------------------
    def bfs_path(
        self, grid: Grid, start: Position, target: Position
    ) -> Optional[List[Position]]:
        """Shortest 4-connected path over passable cells, or ``None``."""
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        if not (0 <= target[0] < rows and 0 <= target[1] < cols):
            return None
        if not self.is_passable(grid[target[0]][target[1]]):
            return None
        if start == target:
            return [start]
        if not self.is_passable(grid[start[0]][start[1]]):
            return None

        prev: Dict[Position, Position] = {start: start}
        q = deque([start])
        found = False
        while q:
            cur = q.popleft()
            for nb in _neighbors(cur[0], cur[1], rows, cols):
                if nb in prev:
                    continue
                if not self.is_passable(grid[nb[0]][nb[1]]):
                    continue
                prev[nb] = cur
                if nb == target:
                    found = True
                    q.clear()
                    break
                q.append(nb)
        if not found:
            return None

        path: List[Position] = [target]
        while path[-1] != start:
            path.append(prev[path[-1]])
        path.reverse()
        return path

    # -- compilation -------------------------------------------------------
    def compile(
        self,
        grid: Grid,
        agent: Position,
        target: Position,
        interact: bool = True,
    ) -> Optional[MacroPlan]:
        """Compile an optimal macro-action from *agent* to *target*.

        Returns ``None`` when the target is unreachable (or has no reachable
        adjacent cell for interaction).
        """
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        if not (0 <= agent[0] < rows and 0 <= agent[1] < cols):
            return None
        if not (0 <= target[0] < rows and 0 <= target[1] < cols):
            return None

        goal_cell = target
        if not self.is_passable(grid[target[0]][target[1]]):
            adj = [
                nb
                for nb in _neighbors(target[0], target[1], rows, cols)
                if self.is_passable(grid[nb[0]][nb[1]])
            ]
            if not adj:
                return None
            goal_cell = min(adj, key=lambda c: _manhattan(agent, c))

        path = self.bfs_path(grid, agent, goal_cell)
        if path is None:
            return None

        actions = self.path_to_actions(path)
        if interact:
            actions.append(ACTION_INTERACT)

        expectations = self.simulate(grid, agent, actions)
        return MacroPlan(
            start=agent,
            target=target,
            path=path,
            actions=actions,
            expectations=expectations,
            interact=interact,
        )

    @staticmethod
    def path_to_actions(path: Sequence[Position]) -> List[int]:
        """Translate a cell path into a discrete action sequence."""
        return [
            _delta_to_action(b[0] - a[0], b[1] - a[1])
            for a, b in zip(path, path[1:])
        ]

    # -- forward simulation for early-break -------------------------------
    def simulate(
        self, grid: Grid, start: Position, actions: Sequence[int]
    ) -> List[StepExpectation]:
        """Predict the agent position and grid after each action.

        Movement steps are validated later via :meth:`should_break`; the
        ``INTERACT`` outcome is environment-defined and therefore marked
        non-validatable. Optionally models pushing of ``pushable`` blocks.
        """
        rows = len(grid)
        cols = len(grid[0]) if rows else 0
        pos = start
        g = _copy_grid(grid)
        expectations: List[StepExpectation] = []
        for a in actions:
            if a == ACTION_INTERACT:
                expectations.append(
                    StepExpectation(a, pos, _copy_grid(g), validatable=False)
                )
                continue
            if a not in _ACTION_DELTAS:
                raise ValueError(f"unknown action code {a}")
            dr, dc = _ACTION_DELTAS[a]
            nr, nc = pos[0] + dr, pos[1] + dc
            if 0 <= nr < rows and 0 <= nc < cols:
                cell = int(g[nr][nc])
                if self.is_passable(cell):
                    pos = (nr, nc)
                elif cell in self.pushable:
                    br, bc = nr + dr, nc + dc
                    if (
                        0 <= br < rows
                        and 0 <= bc < cols
                        and self.is_passable(g[br][bc])
                    ):
                        g[br][bc] = cell  # block slides one cell forward
                        g[nr][nc] = self.background
                        pos = (nr, nc)
            expectations.append(
                StepExpectation(a, pos, _copy_grid(g), validatable=True)
            )
        return expectations

    def should_break(
        self,
        expectation: StepExpectation,
        observed_position: Position,
        observed_grid: Optional[Grid] = None,
        compare_grid: bool = True,
    ) -> bool:
        """Return ``True`` when the observed transition diverges from the
        compiled expectation (early abort of a stale macro-action)."""
        if not expectation.validatable:
            return False
        if observed_position != expectation.position:
            return True
        if compare_grid and observed_grid is not None:
            if not _grids_equal(observed_grid, expectation.grid):
                return True
        return False


# ---------------------------------------------------------------------------
# 4. AdaptiveBudgetManager
# ---------------------------------------------------------------------------

class AdaptiveBudgetManager:
    """Step allocation under the quadratic-decay score
    ``Score(t) = max(0, 1 - (t / H)^2)``.

    * For ``t << H`` the remaining score budget is large, so the manager
      favours high-novelty frontier exploration (novelty = lowest visit
      count, Manhattan distance as tie-break).
    * As ``t`` approaches ``switch_fraction * H`` (default ``0.6 * H``) the
      score headroom shrinks and the manager switches to greedy convergence
      on the nearest goal.
    """

    def __init__(self, horizon: int, switch_fraction: float = 0.6) -> None:
        if horizon <= 0:
            raise ValueError("horizon must be a positive integer")
        if not 0.0 <= switch_fraction <= 1.0:
            raise ValueError("switch_fraction must be in [0, 1]")
        self.horizon = int(horizon)
        self.switch_fraction = float(switch_fraction)
        self.switch_at = self.switch_fraction * self.horizon
        self._visit_counts: Dict[Position, int] = {}

    # -- score -------------------------------------------------------------
    def score(self, t: int) -> float:
        """Quadratic-decay score at step *t*."""
        if t < 0:
            t = 0
        if t >= self.horizon:
            return 0.0
        return max(0.0, 1.0 - (t / self.horizon) ** 2)

    def remaining(self, t: int) -> float:
        """Alias for :meth:`score` (score headroom still available)."""
        return self.score(t)

    def marginal_value(self, t: int) -> float:
        """Score lost by spending one more step at time *t*."""
        return self.score(t) - self.score(t + 1)

    # -- mode --------------------------------------------------------------
    def mode(self, t: int) -> str:
        """``"explore"`` before the switch, ``"converge"`` at/after it."""
        return "explore" if t < self.switch_at else "converge"

    def exploration_weight(self, t: int) -> float:
        """Blend factor in [0, 1]: 1 = pure exploration, 0 = pure convergence."""
        if self.switch_at <= 0:
            return 0.0
        x = t / self.switch_at
        if x >= 1.0:
            return 0.0
        return 1.0 - x

    # -- bookkeeping -------------------------------------------------------
    def record_visit(self, cell: Position) -> None:
        self._visit_counts[cell] = self._visit_counts.get(cell, 0) + 1

    def novelty(self, cell: Position) -> int:
        """Visit count; lower = more novel."""
        return self._visit_counts.get(cell, 0)

    # -- target selection --------------------------------------------------
    def select_target(
        self,
        t: int,
        agent: Position,
        frontiers: Sequence[Position],
        goals: Sequence[Position],
    ) -> Tuple[Optional[Position], str]:
        """Pick the next macro-action target and its rationale.

        Explore phase: least-visited frontier (novelty), distance tie-break.
        Converge phase: nearest goal. Falls back gracefully when a phase's
        candidate set is empty.
        """
        if self.mode(t) == "converge" and goals:
            best = min(goals, key=lambda c: (_manhattan(agent, c), c))
            return best, "goal"
        if frontiers:
            best = min(
                frontiers,
                key=lambda c: (self._visit_counts.get(c, 0), _manhattan(agent, c), c),
            )
            return best, "frontier"
        if goals:
            best = min(goals, key=lambda c: (_manhattan(agent, c), c))
            return best, "goal"
        return None, "idle"


# ---------------------------------------------------------------------------
# Inline smoke test
# ---------------------------------------------------------------------------

def _smoke_test() -> None:
    # 1. Zobrist hashing
    hasher = ZobristStateHasher(max_size=64, num_colors=16)
    g1 = [[1, 0], [0, 0]]
    g2 = [[1, 0], [0, 0]]
    g3 = [[0, 0], [0, 1]]
    assert hasher.hash_grid(g1) == hasher.hash_grid(g2), "identical states must hash equal"
    assert hasher.hash_grid(g1) != hasher.hash_grid(g3), "distinct states must hash unequal"
    h = hasher.hash_grid(g1)
    h2 = hasher.update(h, (1, 1), 0, 1)
    assert h2 == hasher.hash_grid([[1, 0], [0, 1]]), "incremental update mismatch"
    assert hasher.first_repeated([g1, g3, g1]) == 2, "cycle detection failed"

    # 2. Affordance detection
    grid = [
        [0, 0, 0, 0, 0],
        [0, 1, 0, 0, 3],
        [0, 0, 0, 2, 0],
        [0, 5, 0, 0, 0],
        [0, 0, 0, 0, 0],
    ]
    det = AffordanceDetector(background=0, passable={0}, goal_colors={5})
    aff = det.detect(grid, agent=(2, 2), visited={(2, 2)})
    assert set(aff.frontiers) == {(1, 2), (2, 1), (3, 2)}, f"frontiers {aff.frontiers}"
    assert aff.goals == [(3, 1)], f"goals {aff.goals}"
    assert len(aff.dynamic_objects) == 4, f"dynamic {aff.dynamic_objects}"

    # 3. Macro-action compilation (multi-step path to a passable target)
    mc = MacroActionCompiler(background=0, passable={0})
    plan = mc.compile(grid, agent=(2, 2), target=(0, 4), interact=False)
    assert plan is not None
    assert plan.path == [(2, 2), (1, 2), (0, 2), (0, 3), (0, 4)], plan.path
    assert plan.actions == [ACTION_UP, ACTION_UP, ACTION_RIGHT, ACTION_RIGHT], plan.actions
    assert [e.position for e in plan.expectations] == [(1, 2), (0, 2), (0, 3), (0, 4)]

    # early break: observed position diverges from expectation
    assert mc.should_break(plan.expectations[0], (2, 2)) is True
    assert mc.should_break(plan.expectations[0], (1, 2)) is False

    # interaction target: navigate adjacent then INTERACT
    plan2 = mc.compile(grid, agent=(2, 2), target=(3, 1), interact=True)
    assert plan2 is not None
    assert plan2.path == [(2, 2), (2, 1)], plan2.path
    assert plan2.actions == [ACTION_LEFT, ACTION_INTERACT], plan2.actions
    assert plan2.expectations[-1].validatable is False  # INTERACT outcome unknown

    # unreachable target -> None
    blocked = [[0, 1], [1, 0]]
    assert mc.compile(blocked, agent=(0, 0), target=(1, 1), interact=False) is None

    # 4. Adaptive budget manager
    H = 100
    bm = AdaptiveBudgetManager(horizon=H)
    assert abs(bm.score(0) - 1.0) < 1e-9
    assert abs(bm.score(H) - 0.0) < 1e-9
    assert abs(bm.score(60) - 0.64) < 1e-9
    assert bm.mode(59) == "explore"
    assert bm.mode(60) == "converge"
    assert bm.exploration_weight(0) == 1.0
    assert bm.exploration_weight(60) == 0.0
    target, why = bm.select_target(t=10, agent=(0, 0), frontiers=[(1, 0)], goals=[(5, 5)])
    assert (target, why) == ((1, 0), "frontier")
    target, why = bm.select_target(t=70, agent=(0, 0), frontiers=[(1, 0)], goals=[(5, 5)])
    assert (target, why) == ((5, 5), "goal")

    print("arc3_macro_action_compiler smoke test PASSED")


if __name__ == "__main__":
    _smoke_test()