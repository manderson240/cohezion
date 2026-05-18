"""Cellular automata engine — complexity emergence from deterministic rules.

Maps Wolfram elementary CAs (1D) and totalistic 2D CAs to the 10-step
cosmogony chain. Kolmogorov complexity approximated via zlib compression.
LemonadeCAAdvisor queries local NPU inference for RL-guided rule search.
"""

from __future__ import annotations

import zlib
from dataclasses import dataclass, field
from enum import IntEnum

import numpy as np


# Wolfram complexity classes: I=fixed, II=periodic, III=chaotic, IV=complex(Turing-complete)
class WolframClass(IntEnum):
    FIXED = 1
    PERIODIC = 2
    CHAOTIC = 3
    COMPLEX = 4  # Rule 110 lives here — Turing complete


@dataclass
class CARule:
    """A Wolfram elementary CA rule (1D, 2 states, radius 1 → 8-bit table)."""

    number: int  # 0–255 (Wolfram convention)

    def __post_init__(self) -> None:
        if not 0 <= self.number <= 255:
            raise ValueError(f"Rule number must be 0-255, got {self.number}")
        self._table: dict[tuple[int, int, int], int] = {
            (l, c, r): (self.number >> (l * 4 + c * 2 + r)) & 1
            for l in (0, 1)
            for c in (0, 1)
            for r in (0, 1)
        }

    def apply(self, left: int, center: int, right: int) -> int:
        return self._table[(left, center, right)]

    def mutate(self, bit: int) -> CARule:
        """Flip one rule output bit; returns new rule."""
        return CARule(self.number ^ (1 << bit))

    @classmethod
    def turing_complete(cls) -> CARule:
        return cls(110)

    @classmethod
    def hiho(cls) -> CARule:
        """Rule 90 — self-similar Sierpinski pattern, coherence = 0.5 density."""
        return cls(90)


@dataclass
class CAState:
    """Immutable snapshot of a 1D or 2D CA grid."""

    grid: np.ndarray  # bool or uint8 array

    @classmethod
    def random(cls, width: int, seed: int | None = None) -> CAState:
        rng = np.random.default_rng(seed)
        return cls(rng.integers(0, 2, size=width, dtype=np.uint8))

    @classmethod
    def single_center(cls, width: int) -> CAState:
        g = np.zeros(width, dtype=np.uint8)
        g[width // 2] = 1
        return cls(g)

    @property
    def density(self) -> float:
        return float(np.mean(self.grid))

    @property
    def coherence(self) -> float:
        """HIHO-aligned: distance from 0.5 density, mapped to [0,1]."""
        return 1.0 - 2.0 * abs(self.density - 0.5)

    def as_bytes(self) -> bytes:
        return self.grid.tobytes()


@dataclass
class ComplexityMetrics:
    """Empirical complexity measures for a CA history."""

    lz_complexity: float  # len(compress(history)) / len(history) — Kolmogorov proxy
    attractor_period: int  # 0 = none detected within window
    wolfram_class: WolframClass
    mean_density: float
    coherence: float  # HIHO coherence at final state

    @classmethod
    def from_history(cls, history: list[CAState], window: int = 50) -> ComplexityMetrics:
        raw = b"".join(s.as_bytes() for s in history)
        compressed = zlib.compress(raw, level=9)
        lz = len(compressed) / max(len(raw), 1)

        attractor = _detect_attractor(history[-window:])
        mean_d = float(np.mean([s.density for s in history]))
        coherence = history[-1].coherence if history else 0.5

        wclass = _wolfram_classify(lz, attractor, mean_d)
        return cls(
            lz_complexity=lz,
            attractor_period=attractor,
            wolfram_class=wclass,
            mean_density=mean_d,
            coherence=coherence,
        )


def _detect_attractor(states: list[CAState]) -> int:
    """Return cycle length if a repeated state is found, else 0."""
    seen: dict[bytes, int] = {}
    for i, s in enumerate(states):
        key = s.as_bytes()
        if key in seen:
            return i - seen[key]
        seen[key] = i
    return 0


def _wolfram_classify(lz: float, attractor: int, density: float) -> WolframClass:
    if attractor > 0 and attractor <= 2:
        return WolframClass.FIXED
    if attractor > 0:
        return WolframClass.PERIODIC
    if lz > 0.85:
        return WolframClass.CHAOTIC
    return WolframClass.COMPLEX


class CAEngine:
    """Runs a Wolfram 1D CA for N steps with periodic boundary conditions."""

    def __init__(self, rule: CARule, width: int = 64) -> None:
        self.rule = rule
        self.width = width

    def step(self, state: CAState) -> CAState:
        g = state.grid
        w = self.width
        new = np.zeros(w, dtype=np.uint8)
        for i in range(w):
            l, c, r = g[(i - 1) % w], g[i], g[(i + 1) % w]
            new[i] = self.rule.apply(int(l), int(c), int(r))
        return CAState(new)

    def run(self, initial: CAState, steps: int) -> list[CAState]:
        history = [initial]
        state = initial
        for _ in range(steps):
            state = self.step(state)
            history.append(state)
        return history

    def complexity(self, initial: CAState, steps: int = 100) -> ComplexityMetrics:
        history = self.run(initial, steps)
        return ComplexityMetrics.from_history(history)


@dataclass
class CosmogonyStep:
    """One step in the 10-stage cosmogony chain mapped to a CA rule + transition."""

    stage: int
    name: str
    rule: CARule
    target_wolfram_class: WolframClass
    target_coherence: float  # expected HIHO coherence after this step
    initial: CAState = field(default_factory=lambda: CAState.single_center(64))


# The 10-step chain: each step refines the rule toward HIHO attractor at 0.5 coherence
COSMOGONY_CHAIN: list[CosmogonyStep] = [
    CosmogonyStep(0, "Nothing/Void", CARule(0), WolframClass.FIXED, 0.0),
    CosmogonyStep(1, "Quadrature Nexus", CARule(90), WolframClass.COMPLEX, 0.5),
    CosmogonyStep(2, "12 Parameters", CARule(110), WolframClass.COMPLEX, 0.5),
    CosmogonyStep(3, "4 Fabrics", CARule(30), WolframClass.CHAOTIC, 0.3),
    CosmogonyStep(4, "Phase/LENR", CARule(54), WolframClass.COMPLEX, 0.4),
    CosmogonyStep(5, "Symmetry Breaking/EVO", CARule(18), WolframClass.PERIODIC, 0.5),
    CosmogonyStep(6, "SPIN Discretization", CARule(150), WolframClass.PERIODIC, 0.5),
    CosmogonyStep(7, "HIHO Attractor", CARule(90), WolframClass.COMPLEX, 0.5),
    CosmogonyStep(8, "COHESION/Diaelectric", CARule(4), WolframClass.FIXED, 0.5),
    CosmogonyStep(9, "Reality Precipitates", CARule(110), WolframClass.COMPLEX, 0.5),
]


class CosmogonyCA:
    """Runs the 10-step cosmogony chain as sequential CA generations."""

    def __init__(self, steps_per_stage: int = 50) -> None:
        self.steps_per_stage = steps_per_stage
        self._history: list[tuple[int, ComplexityMetrics]] = []

    def run(self, width: int = 64, seed: int = 42) -> list[tuple[int, ComplexityMetrics]]:
        self._history.clear()
        # Stage 0 (Void) uses random fluctuations — vacuum is not static
        state = CAState.random(width, seed=seed)
        for step in COSMOGONY_CHAIN:
            engine = CAEngine(step.rule, width)
            metrics = engine.complexity(state, self.steps_per_stage)
            self._history.append((step.stage, metrics))
            history = engine.run(state, self.steps_per_stage)
            final = history[-1]
            # Inject vacuum fluctuation at each phase boundary to prevent collapse
            if final.density < 0.05 or final.density > 0.95:
                rng = np.random.default_rng(seed + step.stage)
                noise = rng.integers(0, 2, size=width, dtype=np.uint8)
                state = CAState(
                    np.maximum(final.grid, noise * (rng.random(width) < 0.1).astype(np.uint8))
                )
            else:
                state = final
        return self._history

    @property
    def history(self) -> list[tuple[int, ComplexityMetrics]]:
        return self._history


class LemonadeCAAdvisor:
    """Queries local NPU (port 13306) to propose CA rule mutations.

    The LLM acts as policy network for RL rule search: given current rule
    number and target Wolfram class, suggest a rule bit to flip.
    Falls back silently if Lemonade is unreachable.
    """

    NPU_URL = "http://localhost:13306/v1"
    MODEL = "llama3.2-1b-FLM"

    def __init__(self, npu_url: str = NPU_URL, timeout: float = 5.0) -> None:
        self._url = npu_url
        self._timeout = timeout
        self._available: bool | None = None

    def _check_available(self) -> bool:
        if self._available is not None:
            return self._available
        try:
            import urllib.request

            urllib.request.urlopen(f"{self._url}/models", timeout=2)
            self._available = True
        except Exception:
            self._available = False
        return self._available

    def propose_mutation(
        self,
        rule: CARule,
        target_class: WolframClass,
        evidence: ComplexityMetrics,
    ) -> int:
        """Return a bit index (0-7) to flip in the rule table.

        Falls back to the bit with highest information gain (flipping the
        output bit most likely to increase complexity) if Lemonade is down.
        """
        if not self._check_available():
            return self._greedy_bit(rule, evidence)

        try:
            import json
            import urllib.request

            prompt = (
                f"CA rule {rule.number} (binary: {rule.number:08b}). "
                f"Current complexity: {evidence.lz_complexity:.3f}, "
                f"class: {evidence.wolfram_class.name}, "
                f"target class: {target_class.name}. "
                f"Which bit (0-7) should I flip to increase complexity? "
                f"Reply with a single integer 0-7."
            )
            body = json.dumps(
                {
                    "model": self.MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 4,
                    "temperature": 0.0,
                }
            ).encode()
            req = urllib.request.Request(
                f"{self._url}/chat/completions",
                data=body,
                headers={"Content-Type": "application/json"},
            )
            with urllib.request.urlopen(req, timeout=self._timeout) as resp:
                data = json.loads(resp.read())
                text = data["choices"][0]["message"]["content"].strip()
                bit = int("".join(c for c in text if c.isdigit())[:1])
                return max(0, min(7, bit))
        except Exception:
            return self._greedy_bit(rule, evidence)

    def _greedy_bit(self, rule: CARule, evidence: ComplexityMetrics) -> int:
        """Pick the bit whose flip moves lz_complexity closest to 0.5 (COMPLEX zone)."""
        best_bit, best_score = 0, float("inf")
        for bit in range(8):
            candidate = rule.mutate(bit)
            # Approximate: rules in 65-150 range tend toward Class III/IV
            distance = abs(candidate.number - 110) / 110.0
            if distance < best_score:
                best_score = distance
                best_bit = bit
        return best_bit


def ca_rl_step(
    rule: CARule,
    target_class: WolframClass,
    width: int = 64,
    steps: int = 50,
    advisor: LemonadeCAAdvisor | None = None,
) -> tuple[CARule, ComplexityMetrics, float]:
    """One RL episode: advisor proposes mutation, evaluate reward.

    Reward: 1.0 if Wolfram class matches target, else lz_complexity (higher = better).
    Returns (new_rule, metrics, reward).
    """
    engine = CAEngine(rule, width)
    initial = CAState.random(width, seed=42)
    metrics = engine.complexity(initial, steps)

    adv = advisor or LemonadeCAAdvisor()
    bit = adv.propose_mutation(rule, target_class, metrics)
    new_rule = rule.mutate(bit)

    new_engine = CAEngine(new_rule, width)
    new_metrics = new_engine.complexity(initial, steps)

    reward = 1.0 if new_metrics.wolfram_class == target_class else new_metrics.lz_complexity
    return new_rule, new_metrics, reward


# ---------------------------------------------------------------------------
# 2D Totalistic CA — EVO emergence patterns
# ---------------------------------------------------------------------------


@dataclass
class TotalisticRule2D:
    """Conway-style 2D totalistic rule, parameterized by survive/born neighbor counts.

    Totalistic means the next state depends only on the SUM of live Moore neighbors,
    not their arrangement. Conway's Life is survive_counts={2,3}, born_counts={3}.

    Parameters
    ----------
    survive_counts : set[int]
        Live cell survives if its live-neighbor count is in this set.
    born_counts : set[int]
        Dead cell becomes live if its live-neighbor count is in this set.
    radius : int
        Moore neighborhood radius (1 = 8 neighbors, 2 = 24 neighbors, …).
    """

    survive_counts: frozenset[int] = field(default_factory=lambda: frozenset({2, 3}))
    born_counts: frozenset[int] = field(default_factory=lambda: frozenset({3}))
    radius: int = 1

    def __post_init__(self) -> None:
        # Coerce to frozenset for hashability
        object.__setattr__(self, "survive_counts", frozenset(self.survive_counts))
        object.__setattr__(self, "born_counts", frozenset(self.born_counts))

    @classmethod
    def conway(cls) -> TotalisticRule2D:
        """Conway's Game of Life — the canonical EVO emergence substrate."""
        return cls(survive_counts=frozenset({2, 3}), born_counts=frozenset({3}))

    @classmethod
    def hiho_2d(cls) -> TotalisticRule2D:
        """HIHO-tuned rule: survive on 3-4 neighbors, born on 2-3.

        Produces denser, more persistent clusters (charge-cluster analogs).
        """
        return cls(survive_counts=frozenset({3, 4}), born_counts=frozenset({2, 3}))

    def neighbor_sum(self, grid: np.ndarray) -> np.ndarray:
        """Compute Moore neighborhood live-cell counts via np.roll (CPU, no scipy)."""
        total = np.zeros_like(grid, dtype=np.int32)
        for di in range(-self.radius, self.radius + 1):
            for dj in range(-self.radius, self.radius + 1):
                if di == 0 and dj == 0:
                    continue
                total += np.roll(np.roll(grid, di, axis=0), dj, axis=1)
        return total

    def apply(self, grid: np.ndarray) -> np.ndarray:
        """Apply totalistic rule to a 2D uint8 grid; returns new grid."""
        nbrs = self.neighbor_sum(grid)
        survive_mask = np.isin(nbrs, list(self.survive_counts)) & (grid == 1)
        born_mask = np.isin(nbrs, list(self.born_counts)) & (grid == 0)
        return (survive_mask | born_mask).astype(np.uint8)


class CAGrid2D:
    """2D CA grid with step/run interface and HIHO coherence metrics.

    Parameters
    ----------
    rule : TotalisticRule2D
        The 2D totalistic rule to apply each step.
    rows, cols : int
        Grid dimensions (minimum 20×20 required by EVO tests).
    """

    def __init__(self, rule: TotalisticRule2D, rows: int = 20, cols: int = 20) -> None:
        self.rule = rule
        self.rows = rows
        self.cols = cols
        self._grid = np.zeros((rows, cols), dtype=np.uint8)

    @classmethod
    def random(
        cls,
        rule: TotalisticRule2D,
        rows: int = 20,
        cols: int = 20,
        seed: int | None = None,
        density: float = 0.3,
    ) -> CAGrid2D:
        """Create a grid seeded with random live cells at the given density."""
        rng = np.random.default_rng(seed)
        g = cls(rule, rows, cols)
        g._grid = (rng.random((rows, cols)) < density).astype(np.uint8)
        return g

    @property
    def grid(self) -> np.ndarray:
        return self._grid.copy()

    @property
    def density(self) -> float:
        """Fraction of live cells."""
        return float(np.mean(self._grid))

    @property
    def coherence(self) -> float:
        """HIHO coherence: 1.0 at density=0.5, 0.0 at density=0 or 1."""
        return 1.0 - 2.0 * abs(self.density - 0.5)

    def step(self) -> CAGrid2D:
        """Advance one generation in-place; returns self for chaining."""
        self._grid = self.rule.apply(self._grid)
        return self

    def run(self, steps: int) -> list[np.ndarray]:
        """Run for `steps` generations; returns list of grid snapshots."""
        snapshots: list[np.ndarray] = [self._grid.copy()]
        for _ in range(steps):
            self.step()
            snapshots.append(self._grid.copy())
        return snapshots

    def as_bytes(self) -> bytes:
        return self._grid.flatten().tobytes()


@dataclass
class EVOPattern:
    """A detected stable structure in a 2D CA — oscillator or glider.

    Detection: compare grid at time t with grid at time t+period,
    allowing for spatial shifts (gliders move, oscillators stay put).

    Attributes
    ----------
    pattern_type : str
        "oscillator" (no shift) or "glider" (non-zero shift).
    period : int
        Steps for the pattern to recur.
    shift : tuple[int, int]
        (row_shift, col_shift) per period; (0,0) for oscillators.
    bounding_box : tuple[int, int, int, int]
        (row_min, col_min, row_max, col_max) of the pattern at detection time.
    coherence : float
        HIHO coherence of the sub-grid inside the bounding box.
    """

    pattern_type: str  # "oscillator" or "glider"
    period: int
    shift: tuple[int, int]
    bounding_box: tuple[int, int, int, int]
    coherence: float

    @classmethod
    def detect(
        cls,
        snapshots: list[np.ndarray],
        max_shift: int = 3,
        check_periods: tuple[int, ...] = (1, 2, 4),
    ) -> list[EVOPattern]:
        """Scan the snapshot history for oscillators and gliders.

        For each pair (t, t+period), checks if rolling the grid by (dr, dc)
        produces an exact match. Oscillators match at shift=(0,0).
        """
        patterns: list[EVOPattern] = []
        seen: set[tuple[int, int, int, int, int]] = set()  # (period, dr, dc, r0, c0)

        for period in check_periods:
            for t in range(len(snapshots) - period):
                g_t = snapshots[t]
                g_tp = snapshots[t + period]

                # Candidate shifts: (0,0) first (oscillators), then offsets (gliders)
                shifts = [(0, 0)]
                shifts += [
                    (dr, dc)
                    for dr in range(-max_shift, max_shift + 1)
                    for dc in range(-max_shift, max_shift + 1)
                    if (dr, dc) != (0, 0)
                ]

                for dr, dc in shifts:
                    rolled = np.roll(np.roll(g_t, dr, axis=0), dc, axis=1)
                    if not np.array_equal(rolled, g_tp):
                        continue
                    # Both grids must be non-trivial (at least one live cell)
                    if g_t.sum() == 0:
                        continue

                    # Compute bounding box of live cells at time t
                    live = np.argwhere(g_t)
                    if len(live) == 0:
                        continue
                    r0, c0 = int(live[:, 0].min()), int(live[:, 1].min())
                    r1, c1 = int(live[:, 0].max()), int(live[:, 1].max())

                    key = (period, dr, dc, r0, c0)
                    if key in seen:
                        continue
                    seen.add(key)

                    sub = g_t[r0 : r1 + 1, c0 : c1 + 1]
                    sub_density = float(sub.mean()) if sub.size > 0 else 0.0
                    coherence = 1.0 - 2.0 * abs(sub_density - 0.5)

                    ptype = "oscillator" if (dr == 0 and dc == 0) else "glider"
                    patterns.append(
                        cls(
                            pattern_type=ptype,
                            period=period,
                            shift=(dr, dc),
                            bounding_box=(r0, c0, r1, c1),
                            coherence=coherence,
                        )
                    )

        return patterns


@dataclass
class ComplexityMetrics2D:
    """Complexity measures for a 2D CA run — EVO emergence analog.

    Attributes
    ----------
    lz_complexity : float
        Kolmogorov complexity proxy: compressed_size / raw_size.
    pattern_count : int
        Number of distinct EVO-like stable structures detected.
    oscillator_count : int
        Subset of pattern_count that are oscillators (in-place periodic).
    glider_count : int
        Subset of pattern_count that are gliders (moving periodic).
    mean_density : float
        Average live-cell density across all steps.
    coherence : float
        HIHO coherence at final grid state.
    evo_emergence_score : float
        Composite: pattern_count × coherence × (1 − lz_complexity).
        Higher means more structured EVO-analog emergence.
    """

    lz_complexity: float
    pattern_count: int
    oscillator_count: int
    glider_count: int
    mean_density: float
    coherence: float
    evo_emergence_score: float

    @classmethod
    def from_run(
        cls,
        snapshots: list[np.ndarray],
        patterns: list[EVOPattern],
    ) -> ComplexityMetrics2D:
        raw = b"".join(g.flatten().tobytes() for g in snapshots)
        compressed = zlib.compress(raw, level=9)
        lz = len(compressed) / max(len(raw), 1)

        densities = [float(np.mean(g)) for g in snapshots]
        mean_d = float(np.mean(densities))
        final_d = densities[-1] if densities else 0.5
        coherence = 1.0 - 2.0 * abs(final_d - 0.5)

        n_osc = sum(1 for p in patterns if p.pattern_type == "oscillator")
        n_gli = sum(1 for p in patterns if p.pattern_type == "glider")

        score = len(patterns) * coherence * max(0.0, 1.0 - lz)
        return cls(
            lz_complexity=lz,
            pattern_count=len(patterns),
            oscillator_count=n_osc,
            glider_count=n_gli,
            mean_density=mean_d,
            coherence=coherence,
            evo_emergence_score=score,
        )


class EVOEmergence:
    """Runs a 2D CA from a random seed and detects EVO-like emergence patterns.

    Maps Shoulders' Exotic Vacuum Object charge-cluster formation to CA emergence:
    - Random vacuum fluctuations → structured charge clusters (oscillators/gliders)
    - HIHO threshold (density ≈ 0.5) → maximum emergence probability
    - Witness marks → detected patterns logged as EVOPattern instances

    Usage
    -----
    >>> evo = EVOEmergence(rows=20, cols=20, steps=20)
    >>> metrics = evo.run(seed=42)
    >>> print(metrics.evo_emergence_score)
    """

    def __init__(
        self,
        rule: TotalisticRule2D | None = None,
        rows: int = 20,
        cols: int = 20,
        steps: int = 20,
        seed_density: float = 0.3,
    ) -> None:
        self.rule = rule or TotalisticRule2D.conway()
        self.rows = rows
        self.cols = cols
        self.steps = steps
        self.seed_density = seed_density
        self._last_patterns: list[EVOPattern] = []

    def run(self, seed: int | None = 42) -> ComplexityMetrics2D:
        """Seed a random grid, evolve for `steps`, detect EVO patterns, return metrics."""
        grid = CAGrid2D.random(
            self.rule,
            rows=self.rows,
            cols=self.cols,
            seed=seed,
            density=self.seed_density,
        )
        snapshots = grid.run(self.steps)
        self._last_patterns = EVOPattern.detect(snapshots)
        return ComplexityMetrics2D.from_run(snapshots, self._last_patterns)

    @property
    def patterns(self) -> list[EVOPattern]:
        """Patterns detected in the most recent run."""
        return list(self._last_patterns)
