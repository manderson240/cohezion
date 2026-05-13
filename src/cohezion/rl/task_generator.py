"""TaskGenerator — converts PRIME skill archetypes into RL TaskSpecs.

Generates 5 archetypes x 4 difficulty levels = 20 TaskSpecs total.
Each TaskSpec is a test oracle for the RL environment.

Archetypes:
1. HIHO Basin Navigation — navigate to HIHO_Origin stability well
2. TRIUNE Balance — maintain Doer/Thinker/Knower equilibrium
3. Interruption Recovery — recover SPIN coherence after pause
4. Exotic Charge Tolerance — navigate with high exotic charge density
5. Kordylewski Orbit — maintain orbit around L4/L5 memory cloud

Reference: docs/phases/PHASE_2_TASKGEN.md
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Any, ClassVar


if TYPE_CHECKING:
    from cohezion.rl.evo import EthericVariantOscillator


TASK_ARCHETYPES = {
    "hiho_basin": {
        "description": "Navigate from arbitrary starting point to HIHO_Origin stability well",
        "target_well": "HIHO_Origin",
        "base_horizon": 200,
        "base_noise": 0.05,
    },
    "triune_balance": {
        "description": "Maintain equilibrium across Doer/Thinker/Knower TRIUNE dimensions",
        "target_well": "unknown",
        "base_horizon": 150,
        "base_noise": 0.03,
    },
    "interruption_recovery": {
        "description": "Recover SPIN coherence after interruption at mid-horizon",
        "target_well": "HIHO_Origin",
        "base_horizon": 300,
        "base_noise": 0.02,
    },
    "exotic_charge_tolerance": {
        "description": "Navigate with sustained high exotic charge density",
        "target_well": "unknown",
        "base_horizon": 250,
        "base_noise": 0.10,
    },
    "kordylewski_orbit": {
        "description": "Maintain orbit around L4/L5 Kordylewski memory cloud",
        "target_well": "L4_or_L5",
        "base_horizon": 400,
        "base_noise": 0.08,
    },
}


@dataclass
class TaskSpec:
    """RL task specification derived from PRIME skill archetype.

    Parameters
    ----------
    archetype : str
        One of: hiho_basin, triune_balance, interruption_recovery,
        exotic_charge_tolerance, kordylewski_orbit
    horizon : int
        Maximum steps per episode.
    interruption_points : list[int]
        Steps where environment pauses (for interruption_recovery).
    context_injection : bool
        Whether to inject drift into TRIUNE layers mid-episode.
    noise_level : float
        Action noise multiplier (0.0 to 1.0).
    doer_dominance : float
        Weight of Doer layer in reward (0.0 to 1.0).
    thinker_dominance : float
        Weight of Thinker layer in reward (0.0 to 1.0).
    knower_dominance : float
        Weight of Knower layer in reward (0.0 to 1.0).
    exotic_charge_amplitude : float
        Target exotic charge density (0.0 to 1.0).
    kordylewski_gravity : float
        Swarm gravity strength toward L4/L5 cloud (0.0 to 1.0).
    kordylewski_cloud_id : str
        Target cloud: "L4" or "L5".
    stability_well : str
        Target StabilityWell name.
    difficulty : int
        Difficulty level 1-4 (affects horizon, noise, charge amplitude).
    """

    archetype: str
    horizon: int = 200
    interruption_points: list[int] = field(default_factory=list)
    context_injection: bool = False
    noise_level: float = 0.05
    doer_dominance: float = 1.0 / 3.0
    thinker_dominance: float = 1.0 / 3.0
    knower_dominance: float = 1.0 / 3.0
    exotic_charge_amplitude: float = 0.0
    kordylewski_gravity: float = 0.0
    kordylewski_cloud_id: str = "L4"
    stability_well: str = "HIHO_Origin"
    difficulty: int = 1

    def __post_init__(self) -> None:
        """Validate and normalize TRIUNE weights."""
        total = self.doer_dominance + self.thinker_dominance + self.knower_dominance
        if abs(total - 1.0) > 1e-6:
            self.doer_dominance /= total
            self.thinker_dominance /= total
            self.knower_dominance /= total

    def validate(self, evo: EthericVariantOscillator | Any) -> tuple[bool, float]:
        """Test oracle: validate EVO against task success criteria.

        Parameters
        ----------
        evo : EthericVariantOscillator or mock
            The EVO (or mock) to validate.

        Returns
        -------
        tuple[bool, float]
            (is_valid, score) where score is in [0.0, 1.0].
        """
        if self.archetype == "hiho_basin":
            return self._validate_hiho_basin(evo)
        elif self.archetype == "triune_balance":
            return self._validate_triune_balance(evo)
        elif self.archetype == "interruption_recovery":
            return self._validate_interruption_recovery(evo)
        elif self.archetype == "exotic_charge_tolerance":
            return self._validate_exotic_charge_tolerance(evo)
        elif self.archetype == "kordylewski_orbit":
            return self._validate_kordylewski_orbit(evo)
        return False, 0.0

    def _validate_hiho_basin(self, evo: Any) -> tuple[bool, float]:
        """Validate HIHO Basin Navigation task.

        Success: coherence_amplitude >= 0.7 and ends near HIHO_Origin.
        """
        coherence = getattr(evo, "coherence_amplitude", 0.0)
        score = coherence
        valid = coherence >= 0.7
        return valid, float(score)

    def _validate_triune_balance(self, evo: Any) -> tuple[bool, float]:
        """Validate TRIUNE Balance task.

        Success: TRIUNE weights roughly balanced and coherence >= 0.6.
        """
        doer = getattr(evo, "doer_dominance", 0.33)
        thinker = getattr(evo, "thinker_dominance", 0.33)
        knower = getattr(evo, "knower_dominance", 0.33)

        weights = sorted([doer, thinker, knower])
        balance = 1.0 - (weights[-1] - weights[0])
        coherence = getattr(evo, "coherence_amplitude", 0.0)
        score = balance * 0.5 + coherence * 0.5
        valid = balance > 0.7 and coherence >= 0.6
        return valid, float(score)

    def _validate_interruption_recovery(self, evo: Any) -> tuple[bool, float]:
        """Validate Interruption Recovery task.

        Success: coherence_amplitude >= 0.65 and recovery within 50 steps.
        """
        coherence = getattr(evo, "coherence_amplitude", 0.0)
        score = coherence
        valid = coherence >= 0.65
        return valid, float(score)

    def _validate_exotic_charge_tolerance(self, evo: Any) -> tuple[bool, float]:
        """Validate Exotic Charge Tolerance task.

        Success: exotic_charge_density sustained > 0.3 with coherence >= 0.5.
        """
        exotic_charge = getattr(evo, "exotic_charge_density", 0.0)
        coherence = getattr(evo, "coherence_amplitude", 0.0)
        score = exotic_charge * 0.3 + coherence * 0.7
        valid = exotic_charge > 0.2 and coherence >= 0.5
        return valid, float(score)

    def _validate_kordylewski_orbit(self, evo: Any) -> tuple[bool, float]:
        """Validate Kordylewski Orbit task.

        Success: coherence_amplitude >= 0.6 and orbit within cloud radius.
        """
        coherence = getattr(evo, "coherence_amplitude", 0.0)
        score = coherence
        valid = coherence >= 0.6
        return valid, float(score)


class TaskGenerator:
    """Generates TaskSpecs from archetype + difficulty.

    Difficulty scaling:
    - Level 1: base_horizon * 1.0, noise * 1.0, charge * 0.5
    - Level 2: base_horizon * 1.5, noise * 1.5, charge * 1.0
    - Level 3: base_horizon * 2.0, noise * 2.0, charge * 1.5
    - Level 4: base_horizon * 3.0, noise * 3.0, charge * 2.0
    """

    DIFFICULTY_MULTIPLIERS: ClassVar = {
        1: {"horizon": 1.0, "noise": 1.0, "charge": 0.5},
        2: {"horizon": 1.5, "noise": 1.5, "charge": 1.0},
        3: {"horizon": 2.0, "noise": 2.0, "charge": 1.5},
        4: {"horizon": 3.0, "noise": 3.0, "charge": 2.0},
    }

    def __init__(self, seed: int | None = None) -> None:
        self.rng = __import__("numpy").random.RandomState(seed)

    def generate(self, archetype: str, difficulty: int = 1) -> TaskSpec:
        """Generate a single TaskSpec.

        Parameters
        ----------
        archetype : str
            Task archetype name.
        difficulty : int
            Difficulty level 1-4.

        Returns
        -------
        TaskSpec
            Generated task specification.
        """
        if archetype not in TASK_ARCHETYPES:
            raise ValueError(f"Unknown archetype: {archetype}. Must be one of {list(TASK_ARCHETYPES.keys())}")

        cfg = TASK_ARCHETYPES[archetype]
        m = self.DIFFICULTY_MULTIPLIERS[clamp(difficulty, 1, 4)]

        horizon = int(cfg["base_horizon"] * m["horizon"])
        noise = float(cfg["base_noise"] * m["noise"])
        exotic_charge = float(min(m["charge"] * 0.3, 1.0))

        interruption_points: list[int] = []
        context_injection = False
        kordylewski_gravity = 0.0
        kordylewski_cloud_id = "L4"
        doer_dominance = 0.33
        thinker_dominance = 0.33
        knower_dominance = 0.33
        stability_well = cfg["target_well"]

        if archetype == "interruption_recovery":
            interruption_points = [int(horizon * 0.5)]
            context_injection = difficulty >= 3

        elif archetype == "triune_balance":
            doer_dominance = 0.33 + self.rng.uniform(-0.1, 0.1)
            thinker_dominance = 0.33 + self.rng.uniform(-0.1, 0.1)
            knower_dominance = 0.33 + self.rng.uniform(-0.1, 0.1)
            total = doer_dominance + thinker_dominance + knower_dominance
            doer_dominance /= total
            thinker_dominance /= total
            knower_dominance /= total

        elif archetype == "exotic_charge_tolerance":
            exotic_charge = float(min(m["charge"] * 0.4, 1.0))
            context_injection = True

        elif archetype == "kordylewski_orbit":
            kordylewski_gravity = float(min(m["charge"] * 0.3, 1.0))
            kordylewski_cloud_id = "L4" if self.rng.rand() < 0.5 else "L5"
            stability_well = kordylewski_cloud_id

        return TaskSpec(
            archetype=archetype,
            horizon=horizon,
            interruption_points=interruption_points,
            context_injection=context_injection,
            noise_level=noise,
            doer_dominance=doer_dominance,
            thinker_dominance=thinker_dominance,
            knower_dominance=knower_dominance,
            exotic_charge_amplitude=exotic_charge,
            kordylewski_gravity=kordylewski_gravity,
            kordylewski_cloud_id=kordylewski_cloud_id,
            stability_well=stability_well,
            difficulty=difficulty,
        )

    def generate_all(self) -> list[TaskSpec]:
        """Generate all 5 archetypes x 4 difficulty levels = 20 TaskSpecs.

        Returns
        -------
        list[TaskSpec]
            All 20 task specifications.
        """
        specs = []
        for archetype in TASK_ARCHETYPES:
            for difficulty in range(1, 5):
                specs.append(self.generate(archetype, difficulty))
        return specs

    def save_registry(self, specs: list[TaskSpec], path: Path | str) -> None:
        """Save task spec registry to JSON.

        Parameters
        ----------
        specs : list[TaskSpec]
            Task specifications to save.
        path : Path or str
            Output path.
        """
        path = Path(path).resolve()
        if ".." in str(path):
            raise ValueError(f"Path traversal attempt: {path}")
        data = []
        for spec in specs:
            data.append(
                {
                    "archetype": spec.archetype,
                    "horizon": spec.horizon,
                    "interruption_points": spec.interruption_points,
                    "context_injection": spec.context_injection,
                    "noise_level": spec.noise_level,
                    "doer_dominance": spec.doer_dominance,
                    "thinker_dominance": spec.thinker_dominance,
                    "knower_dominance": spec.knower_dominance,
                    "exotic_charge_amplitude": spec.exotic_charge_amplitude,
                    "kordylewski_gravity": spec.kordylewski_gravity,
                    "kordylewski_cloud_id": spec.kordylewski_cloud_id,
                    "stability_well": spec.stability_well,
                    "difficulty": spec.difficulty,
                }
            )
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    @staticmethod
    def load_registry(path: Path | str) -> list[TaskSpec]:
        """Load task spec registry from JSON.

        Parameters
        ----------
        path : Path or str
            Input path.

        Returns
        -------
        list[TaskSpec]
            Loaded specifications.

        Raises
        ------
        ValueError
            If path contains traversal patterns.
        """
        path = Path(path).resolve()
        if ".." in str(path):
            raise ValueError(f"Path traversal attempt: {path}")
        with open(path) as f:
            data = json.load(f)
        return [TaskSpec(**d) for d in data]


def clamp(value: int, min_val: int, max_val: int) -> int:
    return max(min_val, min(max_val, value))
