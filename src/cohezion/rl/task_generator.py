"""TaskGenerator — Phase 2.

Produces TaskSpecs from 5 archetypes × 4 difficulty levels = 20 TaskSpecs.
Each TaskSpec configures FlumeNavEnv with TRIUNE weights, interruption points,
exotic vacuum conditions, and a validate(evo) oracle.

Archetypes:
1. HIHO_BASIN — navigate to HIHO stability (coherence 0.5)
2. TRIUNE_BALANCE — maintain equal Doer/Thinker/Knower activation
3. INTERRUPTION_RECOVERY — resume after pause + drift injection
4. EXOTIC_CHARGE — survive exotic_charge_density > 0.9
5. KORDYLEWSKI_ORBIT — maintain stable orbit around L4/L5 point

Difficulty scales: horizon, noise, TRIUNE weights, interruption points.
"""

from __future__ import annotations

import json
import random
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


ARCHETYPES = [
    "HIHO_BASIN",
    "TRIUNE_BALANCE",
    "INTERRUPTION_RECOVERY",
    "EXOTIC_CHARGE",
    "KORDYLEWSKI_ORBIT",
]

DIFFICULTIES = [1, 2, 3, 4]


@dataclass
class TaskSpec:
    """RL task specification from PRIME skill archetypes.

    Attributes
    ----------
    name : str
        Unique name "{archetype}-d{difficulty}".
    archetype : str
        One of the 5 archetype names.
    difficulty : int
        1 (easy) to 4 (extreme).
    horizon : int
        Max steps per episode.
    noise_level : float
        Action noise multiplier.
    doer_dominance, thinker_dominance, knower_dominance : float
        TRIUNE weights (sum to 1.0).
    interruption_points : list[int]
        Steps where env.pause() is called.
    exotic_charge_threshold : float
        Threshold for EXOTIC_CHARGE archetype.
    kordylewski_cloud : str
        "L4" or "L5" for KORDYLEWSKI_ORBIT.
    validate_fn : callable, optional
        Test oracle: validate(evo_or_state) → (bool, score 0-1).
    """

    name: str
    archetype: str
    difficulty: int
    horizon: int = 200
    noise_level: float = 0.01
    doer_dominance: float = 1.0 / 3.0
    thinker_dominance: float = 1.0 / 3.0
    knower_dominance: float = 1.0 / 3.0
    interruption_points: list[int] = field(default_factory=list)
    exotic_charge_threshold: float = 0.9
    kordylewski_cloud: str = "L4"
    validate_fn: Callable | None = None

    def __post_init__(self) -> None:
        doer = max(0.0, self.doer_dominance)
        thinker = max(0.0, self.thinker_dominance)
        knower = max(0.0, self.knower_dominance)
        total = doer + thinker + knower
        if total > 0:
            self.doer_dominance = doer / total
            self.thinker_dominance = thinker / total
            self.knower_dominance = knower / total
        else:
            self.doer_dominance = self.thinker_dominance = self.knower_dominance = 1.0 / 3.0

    def validate(self, evo_or_state: Any) -> tuple[bool, float]:
        """Test oracle: returns (success, score 0-1).

        Uses archetype-specific logic if validate_fn not set.
        """
        if self.validate_fn is not None:
            return self.validate_fn(evo_or_state)
        return self._default_oracle(evo_or_state)

    def _default_oracle(self, evo_or_state: Any) -> tuple[bool, float]:
        """Default oracle: coherence-based success."""
        if evo_or_state is None:
            return False, 0.0
        coherence = getattr(evo_or_state, "biography", [{}])
        if isinstance(coherence, list) and len(coherence) > 0:
            coherence = coherence[-1].get("coherence", 0.0)
        elif isinstance(coherence, dict):
            coherence = coherence.get("coherence", 0.0)
        else:
            coherence = float(evo_or_state)
        success = coherence > 0.4
        return success, max(0.0, min(1.0, coherence))


class TaskGenerator:
    """Registry of 20 TaskSpecs (5 archetypes × 4 difficulties).

    Methods:
    - all_specs() → list of all 20 TaskSpecs
    - sample() → random TaskSpec
    - get(name) → TaskSpec or None
    - save(path) / load(path) → JSON roundtrip
    """

    _registry: list[TaskSpec] = field(default_factory=list)

    def __init__(self, specs: list[TaskSpec] | None = None) -> None:
        self._registry = specs if specs is not None else self._build_registry()

    @staticmethod
    def _build_registry() -> list[TaskSpec]:
        """Build 20 TaskSpecs across 5 archetypes × 4 difficulties."""
        specs: list[TaskSpec] = []
        for archetype in ARCHETYPES:
            for difficulty in DIFFICULTIES:
                spec = _build_spec(archetype, difficulty)
                specs.append(spec)
        return specs

    def all_specs(self) -> list[TaskSpec]:
        """Return all 20 TaskSpecs."""
        return self._registry

    def sample(
        self,
        difficulty: int | None = None,
        archetype: str | None = None,
    ) -> TaskSpec:
        """Return a random TaskSpec.

        Parameters
        ----------
        difficulty : int, optional
            Filter by difficulty (1-4).
        archetype : str, optional
            Filter by archetype name.
        """
        pool = self._registry
        if difficulty is not None:
            pool = [s for s in pool if s.difficulty == difficulty]
        if archetype is not None:
            pool = [s for s in pool if s.archetype == archetype]
        if not pool:
            return random.choice(self._registry)
        return random.choice(pool)

    def get(self, name: str) -> TaskSpec | None:
        """Return TaskSpec by name, or None if not found."""
        for spec in self._registry:
            if spec.name == name:
                return spec
        return None

    def save(self, path: Path | str) -> None:
        """Save registry as JSON."""
        path = Path(path)
        tasks = [
            {
                "name": s.name,
                "archetype": s.archetype,
                "difficulty": s.difficulty,
                "horizon": s.horizon,
                "noise_level": s.noise_level,
                "doer_dominance": s.doer_dominance,
                "thinker_dominance": s.thinker_dominance,
                "knower_dominance": s.knower_dominance,
                "interruption_points": s.interruption_points,
                "exotic_charge_threshold": s.exotic_charge_threshold,
                "kordylewski_cloud": s.kordylewski_cloud,
            }
            for s in self._registry
        ]
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        try:
            with open(tmp, "w") as f:
                json.dump({"tasks": tasks, "version": "1.0"}, f, indent=2)
            tmp.rename(path)
        except Exception:
            if tmp.exists():
                tmp.unlink()
            raise

    @classmethod
    def load(cls, path: Path | str) -> TaskGenerator:
        """Load registry from JSON.

        Raises ValueError if path escapes data/ directory.
        """
        raw = Path(path)
        resolved = raw.resolve()
        data_root = Path("data").resolve()
        # Security: reject if resolved path escapes data_root
        try:
            resolved.relative_to(data_root)
        except ValueError:
            raise ValueError(f"Path must be within {data_root}: {raw}")
        with open(resolved) as f:
            data = json.load(f)
        tasks = []
        for d in data.get("tasks", []):
            tasks.append(
                TaskSpec(
                    name=d["name"],
                    archetype=d["archetype"],
                    difficulty=d["difficulty"],
                    horizon=d.get("horizon", 200),
                    noise_level=d.get("noise_level", 0.01),
                    doer_dominance=d.get("doer_dominance", 1.0 / 3.0),
                    thinker_dominance=d.get("thinker_dominance", 1.0 / 3.0),
                    knower_dominance=d.get("knower_dominance", 1.0 / 3.0),
                    interruption_points=d.get("interruption_points", []),
                    exotic_charge_threshold=d.get("exotic_charge_threshold", 0.9),
                    kordylewski_cloud=d.get("kordylewski_cloud", "L4"),
                )
            )
        return cls(specs=tasks)


def _build_spec(archetype: str, difficulty: int) -> TaskSpec:
    """Build a TaskSpec for archetype × difficulty."""
    noise = 0.01 * (1 + 0.25 * (difficulty - 1))
    horizon = int(200 * (1 + 0.25 * (difficulty - 1)))
    interruptions = [25 * difficulty, 50 * difficulty] if archetype == "INTERRUPTION_RECOVERY" else []

    if archetype == "HIHO_BASIN":
        name = f"HIHO_BASIN-d{difficulty}"
        noise = 0.005 * difficulty
        horizon = 150 + 50 * difficulty
        doer, thinker, knower = 0.6, 0.3, 0.1

    elif archetype == "TRIUNE_BALANCE":
        name = f"TRIUNE_BALANCE-d{difficulty}"
        spread = 0.05 * (difficulty - 1)
        doer = 0.333 + random.uniform(-spread, spread)
        thinker = 0.333 + random.uniform(-spread, spread)
        knower = 1.0 - doer - thinker
        horizon = 100 + 50 * difficulty

    elif archetype == "INTERRUPTION_RECOVERY":
        name = f"INTERRUPTION_RECOVERY-d{difficulty}"
        horizon = 150 + 30 * difficulty
        doer, thinker, knower = 0.4, 0.4, 0.2

    elif archetype == "EXOTIC_CHARGE":
        name = f"EXOTIC_CHARGE-d{difficulty}"
        horizon = 100 + 100 * difficulty
        doer, thinker, knower = 0.7, 0.2, 0.1

    elif archetype == "KORDYLEWSKI_ORBIT":
        name = f"KORDYLEWSKI_ORBIT-d{difficulty}"
        horizon = 200 + 50 * difficulty
        cloud = "L4" if difficulty % 2 == 0 else "L5"
        doer, thinker, knower = 0.3, 0.4, 0.3
    else:
        name = f"{archetype}-d{difficulty}"
        doer, thinker, knower = 0.33, 0.33, 0.34

    return TaskSpec(
        name=name,
        archetype=archetype,
        difficulty=difficulty,
        horizon=horizon,
        noise_level=noise,
        doer_dominance=doer,
        thinker_dominance=thinker,
        knower_dominance=knower,
        interruption_points=interruptions,
        exotic_charge_threshold=0.9 if archetype == "EXOTIC_CHARGE" else 0.95,
        kordylewski_cloud=cloud if archetype == "KORDYLEWSKI_ORBIT" else "L4",
    )
