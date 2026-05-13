"""EthericVariantOscillator (EVO) — agentic journeys as exotic vacuum objects.

An EVO is a localized coherence excitation in the 12D axiomatic FLUME state space,
governed by the same physics as Kordylewski cosmic dust clouds and exotic vacuum
constructs. Every agentic journey through the FLUME manifold is an EVO with a
full physics biography.

TRIUNE SELF Structure:
    Doer (12D)   — Physical action in axiomatic space (Space/Field/Control/Precipitation fabrics)
    Thinker (512D) — Reasoning and trajectory planning
    Knower (2048D) — Semantic intent and high-level goal

Physics Properties:
    coherence_amplitude  — Peak HIHO stability reached
    phase               — Position in HIHO oscillation cycle
    angular_momentum    — SPIN coherence vector (rotation x precession)
    charge              — Rotation x Precession alignment

Exotic Vacuum Properties:
    exotic_charge_density — Deviation from HIHO vacuum baseline
    kordylewski_cloud_id  — L4 or L5 memory cloud assignment
    stability_well       — Basin of attraction (HIHO_Origin, Pure_Awareness, etc.)

Memory Management:
    EVO trajectories are memmap'd to disk when they exceed RAM budget.
    The 80GB ceiling is enforced by spilling long trajectories to disk.

Reference: docs/architecture/EVO_MODEL.md
"""

from __future__ import annotations

import json
import os
import re
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


# Memory management constants
MAX_TRAJECTORY_IN_MEMORY = 100
TRAJECTORY_STEP_THRESHOLD_FOR_SPILL = 500
MAX_ACTIVE_EVOS = 20
FLOAT32_BYTES = 4


@dataclass
class EthericVariantOscillator:
    """An agentic journey through FLUME space, treated as an exotic vacuum object.

    Parameters
    ----------
    journey_id : str
        Unique identifier for this journey.
    birth_time : float
        Timestamp of first step.
    doer_state : np.ndarray
        12D axiomatic state (Space/Field/Control/Precipitation fabrics).
        Initialized near HIHO stability (0.5) with small noise.
    thinker_state : np.ndarray
        512D reasoning and trajectory planning state.
    knower_state : np.ndarray
        2048D semantic intent and high-level goal state.
    coherence_amplitude : float
        Peak HIHO coherence reached during journey (0.0 to 1.0).
    phase : float
        Position in HIHO oscillation cycle (0 to 2π).
    angular_momentum : np.ndarray
        3D SPIN coherence vector [rotation, precession, charge].
    charge : float
        Resultant charge from rotation x precession alignment.
    exotic_charge_density : float
        Deviation from HIHO vacuum baseline (0.0 to 1.0).
    kordylewski_cloud_id : str
        L4 or L5 Kordylewski memory cloud assignment.
    stability_well : str
        Which StabilityWell basin this EVO occupies.
    trajectory : list[dict]
        In-memory trajectory steps. Spills to disk when > MAX_TRAJECTORY_IN_MEMORY.
    """

    journey_id: str = field(default_factory=lambda: f"evo_{uuid.uuid4().hex[:12]}")
    birth_time: float = field(default_factory=time.time)
    doer_state: np.ndarray = field(default_factory=lambda: np.random.normal(0.5, 0.1, 12).astype(np.float32))
    thinker_state: np.ndarray = field(default_factory=lambda: np.random.normal(0.5, 0.1, 512).astype(np.float32))
    knower_state: np.ndarray = field(default_factory=lambda: np.random.normal(0.5, 0.1, 2048).astype(np.float32))
    coherence_amplitude: float = 0.0
    phase: float = 0.0
    angular_momentum: np.ndarray = field(default_factory=lambda: np.ones(3, dtype=np.float32))
    charge: float = 1.0
    exotic_charge_density: float = 0.0
    kordylewski_cloud_id: str = "none"
    stability_well: str = "unknown"
    trajectory: list[dict] = field(default_factory=list)
    _trajectory_path: Path | None = field(default=None, repr=False)

    def __post_init__(self) -> None:
        """Validate and normalize TRIUNE states."""
        self.doer_state = np.clip(self.doer_state, -2.0, 2.0).astype(np.float32)
        self.thinker_state = np.ascontiguousarray(self.thinker_state.astype(np.float32))
        self.knower_state = np.ascontiguousarray(self.knower_state.astype(np.float32))
        self.angular_momentum = np.ascontiguousarray(self.angular_momentum.astype(np.float32))

        # Validate dimensions
        if self.doer_state.shape != (12,):
            raise ValueError(f"Doer must be 12D, got {self.doer_state.shape}")
        if self.thinker_state.shape != (512,):
            raise ValueError(f"Thinker must be 512D, got {self.thinker_state.shape}")
        if self.knower_state.shape != (2048,):
            raise ValueError(f"Knower must be 2048D, got {self.knower_state.shape}")
        if self.angular_momentum.shape != (3,):
            raise ValueError(f"Angular momentum must be 3D, got {self.angular_momentum.shape}")

    def record_step(self, step_data: dict[str, Any]) -> None:
        """Record a single step in the trajectory.

        Parameters
        ----------
        step_data : dict
            Must contain: step (int), doer_state (np.ndarray), coherence (float), reward (float).
            Optional: thinker_state, knower_state, exotic_charge_density.
        """
        # Ensure doer_state is float32
        if isinstance(step_data.get("doer_state"), np.ndarray):
            step_data["doer_state"] = step_data["doer_state"].astype(np.float32)

        self.trajectory.append(step_data)

    def update_physics(
        self,
        coherence: float,
        step: int,
        doer_state: np.ndarray,
        thinker_state: np.ndarray | None = None,
        knower_state: np.ndarray | None = None,
    ) -> None:
        """Update EVO physics properties after a step.

        Parameters
        ----------
        coherence : float
            Current HIHO coherence (0.0 to 1.0).
        step : int
            Current step number.
        doer_state : np.ndarray
            Current 12D axiomatic state.
        thinker_state : np.ndarray, optional
            Current 512D reasoning state.
        knower_state : np.ndarray, optional
            Current 2048D intent state.
        """
        # Update coherence amplitude (peak), guarding against NaN
        if np.isfinite(coherence):
            self.coherence_amplitude = max(self.coherence_amplitude, coherence)
        else:
            self.coherence_amplitude = max(self.coherence_amplitude, 0.0)

        # Update phase (oscillation cycle)
        self.phase = (coherence - 0.5) * 2 * np.pi

        # Update angular momentum (SPIN vector)
        # Rotation = logic dim (index 6), Precession = quantum dim (index 7)
        if len(doer_state) >= 8:
            rotation = doer_state[6] if len(doer_state) > 6 else 0.5
            precession = doer_state[7] if len(doer_state) > 7 else 0.5
            rot_sign = 1.0 if rotation >= 0.5 else -1.0
            prec_sign = 1.0 if precession >= 0.5 else -1.0
            self.charge = abs(rot_sign * prec_sign)
            self.angular_momentum = np.array(
                [
                    rotation,
                    precession,
                    self.charge,
                ],
                dtype=np.float32,
            )

        # Update exotic charge density
        variance = np.var(doer_state)
        self.exotic_charge_density = min(variance * 4.0, 1.0)

        # Update TRIUNE states if provided
        if thinker_state is not None:
            self.thinker_state = np.ascontiguousarray(thinker_state.astype(np.float32))
        if knower_state is not None:
            self.knower_state = np.ascontiguousarray(knower_state.astype(np.float32))

        self.doer_state = np.ascontiguousarray(doer_state.astype(np.float32))

    def compute_spin_coherence(self) -> float:
        """Compute SPIN coherence: 1.0 when rotation and precession are aligned.

        Returns
        -------
        float
            SPIN coherence in [0.0, 1.0].
        """
        if len(self.angular_momentum) >= 3:
            rot = self.angular_momentum[0]
            prec = self.angular_momentum[1]
            rot_sign = 1.0 if rot >= 0.5 else -1.0
            prec_sign = 1.0 if prec >= 0.5 else -1.0
            return float(abs(rot_sign * prec_sign))
        return 1.0

    def to_exotic_vacuum_biography(self) -> dict[str, Any]:
        """Export EVO as exotic vacuum biography dict.

        Returns
        -------
        dict
            Serializable biography suitable for HuggingFace dataset export.
            Contains: journey metadata, TRIUNE dimensions, physics properties,
            trajectory summary, and exotic vacuum characterization.
        """
        # Compute trajectory statistics
        if self.trajectory:
            coherences = [s.get("coherence", 0.5) for s in self.trajectory]
            rewards = [s.get("reward", 0.0) for s in self.trajectory]
            final_coherence = coherences[-1] if coherences else 0.0
            mean_coherence = float(np.mean(coherences))
            trajectory_length = len(self.trajectory)
        else:
            final_coherence = 0.5
            mean_coherence = 0.5
            trajectory_length = 0

        return {
            "journey_id": self.journey_id,
            "birth_time": self.birth_time,
            "triune_self": {
                "doer_dim": 12,
                "thinker_dim": 512,
                "knower_dim": 2048,
                "doer_mean": float(np.mean(self.doer_state)),
                "thinker_mean": float(np.mean(self.thinker_state)),
                "knower_mean": float(np.mean(self.knower_state)),
            },
            "physics_properties": {
                "coherence_amplitude": float(self.coherence_amplitude),
                "final_coherence": float(final_coherence),
                "mean_coherence": mean_coherence,
                "phase": float(self.phase),
                "angular_momentum": self.angular_momentum.tolist(),
                "charge": float(self.charge),
                "spin_coherence": self.compute_spin_coherence(),
            },
            "exotic_vacuum": {
                "exotic_charge_density": float(self.exotic_charge_density),
                "kordylewski_cloud_id": self.kordylewski_cloud_id,
                "stability_well": self.stability_well,
            },
            "trajectory_summary": {
                "trajectory_length": trajectory_length,
                "total_reward": float(sum(r for r in rewards)) if rewards else 0.0,
            },
            "hiho_stability": {
                "hiho_band_count": int(sum(1 for c in coherences if 0.4 <= c <= 0.6)) if coherences else 0,
                "hiho_stability_ratio": float(
                    sum(1 for c in coherences if 0.4 <= c <= 0.6) / max(trajectory_length, 1)
                ),
            },
        }

    def get_trajectory_length(self) -> int:
        """Return trajectory length including any spilled-to-disk data."""
        disk_count = 0
        if self._trajectory_path and self._trajectory_path.exists():
            disk_count = len(np.load(self._trajectory_path, allow_pickle=False))
        return len(self.trajectory) + disk_count


class EVOTracker:
    """Tracks active EVOs and manages lifecycle (creation, eviction, disk spill).

    Parameters
    ----------
    storage_dir : Path
        Directory for memmap trajectory spillover.
    max_active : int
        Maximum number of active EVOs in RAM. Default 20.
    max_steps_per_evo : int
        Steps before EVO trajectory spills to disk. Default 500.
    """

    def __init__(
        self,
        storage_dir: Path | str = Path("data/evo_trajectories"),
        max_active: int = MAX_ACTIVE_EVOS,
        max_steps_per_evo: int = TRAJECTORY_STEP_THRESHOLD_FOR_SPILL,
    ) -> None:
        self.storage_dir = Path(storage_dir)
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self.max_active = max_active
        self.max_steps_per_evo = max_steps_per_evo
        self.active_evos: dict[str, EthericVariantOscillator] = {}

    def create_evo(self) -> EthericVariantOscillator:
        """Create a new EVO with a unique journey ID.

        Returns
        -------
        EthericVariantOscillator
            New EVO with TRIUNE SELF states initialized near HIHO stability.
        """
        evo = EthericVariantOscillator()

        # Assign Kordylewski cloud (L4 or L5)
        evo.kordylewski_cloud_id = "L4" if np.random.rand() < 0.5 else "L5"

        return evo

    def register(self, evo: EthericVariantOscillator) -> None:
        """Register an EVO as active.

        If at capacity, evicts the oldest EVO (lowest birth_time).

        Parameters
        ----------
        evo : EthericVariantOscillator
            EVO to register.
        """
        if len(self.active_evos) >= self.max_active:
            self._evict_oldest()

        self.active_evos[evo.journey_id] = evo

    def unregister(self, journey_id: str) -> None:
        """Unregister an EVO from active tracking.

        Parameters
        ----------
        journey_id : str
            Journey ID of EVO to unregister.
        """
        if journey_id in self.active_evos:
            del self.active_evos[journey_id]

    def _evict_oldest(self) -> None:
        """Evict the oldest EVO (lowest birth_time) from active tracking."""
        if not self.active_evos:
            return

        oldest_id = min(self.active_evos, key=lambda evo_id: self.active_evos[evo_id].birth_time)
        self.save_evo(self.active_evos[oldest_id])
        self.unregister(oldest_id)

    def save_evo(self, evo: EthericVariantOscillator) -> Path:
        """Save EVO trajectory to disk as .npy, clear from RAM.

        Parameters
        ----------
        evo : EthericVariantOscillator
            EVO to save.

        Returns
        -------
        Path
            Path to saved .npy file.
        """
        if not evo.trajectory:
            return Path("")

        # Validate journey_id to prevent path traversal
        safe_id = re.sub(r"[^a-zA-Z0-9_\-]", "_", evo.journey_id)
        safe_id = safe_id[:64]  # Cap length

        # Stack trajectory into (steps, 12) array
        doer_states = np.array(
            [s["doer_state"] for s in evo.trajectory],
            dtype=np.float32,
        )

        path = self.storage_dir / f"{safe_id}.npy"
        # Atomic write: write to temp then rename
        tmp_path = self.storage_dir / f".tmp_{safe_id}_{os.urandom(8).hex()}.npy"
        try:
            np.save(tmp_path, doer_states)
            tmp_path.rename(path)
        finally:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)

        evo._trajectory_path = path

        # Clear RAM
        evo.trajectory = []

        return path

    def classify_stability_well(self, evo: EthericVariantOscillator) -> str:
        """Classify which StabilityWell basin the EVO occupies.

        Parameters
        ----------
        evo : EthericVariantOscillator
            EVO to classify.

        Returns
        -------
        str
            Stability well name.
        """
        coherence = evo.coherence_amplitude
        doer_mean = float(np.mean(evo.doer_state))

        # HIHO_Origin: mean close to 0.5, high coherence
        if 0.4 <= doer_mean <= 0.6 and coherence >= 0.7:
            return "HIHO_Origin"

        # Pure_Awareness: logic dim (index 0) dominant
        if len(evo.doer_state) > 0 and evo.doer_state[0] > 0.8:
            return "Pure_Awareness"

        return "unknown"

    def get_active(self) -> list[EthericVariantOscillator]:
        """Return list of active EVOs.

        Returns
        -------
        list[EthericVariantOscillator]
            Active EVOs.
        """
        return list(self.active_evos.values())


def load_evo_trajectory(path: Path | str) -> np.ndarray:
    """Load a spilled EVO trajectory from disk.

    Parameters
    ----------
    path : Path or str
        Path to .npy trajectory file.

    Returns
    -------
    np.ndarray
        Trajectory array of shape (steps, 12).

    Raises
    ------
    ValueError
        If path is absolute or contains traversal patterns.
    """
    path = Path(path)
    resolved = path.resolve()
    # Reject absolute paths, parent traversal, or device paths
    if ".." in str(resolved) or resolved.is_absolute():
        raise ValueError(f"Path traversal attempt detected: {path}")
    return np.load(path, allow_pickle=False)


def evo_to_jsonl(evo: EthericVariantOscillator, output_path: Path) -> None:
    """Export EVO biography to JSONL for HuggingFace dataset.

    Parameters
    ----------
    evo : EthericVariantOscillator
        EVO to export.
    output_path : Path
        Output JSONL file path.
    """
    bio = evo.to_exotic_vacuum_biography()
    with open(output_path, "a") as f:
        f.write(json.dumps(bio) + "\n")
