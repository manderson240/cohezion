#!/usr/bin/env python3
"""ARC-AGI-3 LevelBudget & Anytime Liveness Watchdog (Fable Invariants G1, G2, G3).
Guarantees action emission every <= t_idle seconds to evade Kaggle container timeout
and caps actions per level to preserve budget for solvable levels.
"""
import time
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

class LevelBudget:
    """Per-level action accounting with abandonment and an idle watchdog."""
    def __init__(self, baseline_actions: Optional[List[int]] = None, k: float = 3.0, fixed: int = 60, t_idle: float = 20.0):
        self.base = baseline_actions or []
        self.k = k
        self.fixed = fixed
        self.t_idle = t_idle
        self.level = 0
        self.level_start = 0
        self.per_level: List[int] = []
        self.last_emit = time.monotonic()

    def cap_for(self, level: int) -> int:
        return int(self.k * self.base[level]) if level < len(self.base) else self.fixed

    def on_step(self, step: int, levels_completed: int) -> bool:
        """Return True to ABANDON the game (current level over budget)."""
        if levels_completed > self.level:
            self.per_level.append(step + 1 - self.level_start)
            self.level_start, self.level = step + 1, levels_completed
        self.last_emit = time.monotonic()
        return (step + 1 - self.level_start) > self.cap_for(self.level)

    def must_emit(self) -> bool:
        """G2 Invariant: Never go silent for > 80% of idle threshold."""
        return (time.monotonic() - self.last_emit) > (0.8 * self.t_idle)

class GameScheduler:
    """G3 Invariant: Easiest-first knapsack over games under wall-clock budget W."""
    def __init__(self, games: List[str], W: float, probe_actions: int = 60):
        self.W = W
        self.t0 = time.monotonic()
        self.probe = probe_actions
        self.progress: Dict[str, Tuple[int, int]] = defaultdict(lambda: (0, 1))
        self.order = list(games)

    def rank(self) -> None:
        self.order.sort(key=lambda g: -self.progress[g][0] / self.progress[g][1])

    def remaining(self) -> float:
        return 0.9 * self.W - (time.monotonic() - self.t0)
