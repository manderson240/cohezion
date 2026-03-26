"""EthericVariantOscillator (EVO) — Phase 1.

An EVO is an exotic vacuum object with a full physics biography governed by:
- TRIUNE SELF: Doer(12D) / Thinker(512D) / Knower(2048D) state vectors
- Kordylewski swarm gravity: L4/L5 cloud assignment
- HIHO stability: coherence dynamics and phase accumulation
- Exotic charge: density accumulation over journey

Physics invariants:
- TRIUNE weights renormalize to sum to 1.0 in __post_init__
- NaN coherence replaced with previous value (not propagated)
- Phase increases monotonically across steps
- Exotic charge density grows with each step

Register: journey_id sanitized (alphanumeric + _ + -, max 64 chars)
Storage: LRU eviction at max_active; .npy spillover per TRIUNE state
Export: JSON biography + .npy files for HuggingFace
"""

from __future__ import annotations

import re
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np


JOURNEY_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
JOURNEY_ID_MAX_LEN = 64


def _sanitize_journey_id(journey_id: str) -> str:
    """Sanitize journey_id: alphanumeric + _ + -, max 64 chars."""
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "", journey_id)
    if not sanitized:
        sanitized = "anonymous"
    return sanitized[:JOURNEY_ID_MAX_LEN]


@dataclass
class EthericVariantOscillator:
    """Etheric Variant Oscillator: exotic vacuum object with TRIUNE SELF biography.

    Attributes
    ----------
    journey_id : str
        Unique identifier, sanitized (alphanumeric + _ + -, max 64 chars).
    doer_state : np.ndarray
        12D action vector (float32, C-contiguous).
    thinker_state : np.ndarray
        512D reasoning vector (float32, C-contiguous).
    knower_state : np.ndarray
        2048D intent vector (float32, C-contiguous).
    doer_weight, thinker_weight, knower_weight : float
        TRIUNE dominance weights, renormalized to sum to 1.0 in __post_init__.
    kordylewski_cloud : str
        "L4" or "L5" (Kordylewski cloud assignment).
    stability_well : str
        "basin" or "hilltop" (HIHO stability classification).
    exotic_charge_density : float
        Accumulated exotic charge [0, 1].
    phase : float
        Accumulated SPIN phase (radians).
    biography : list[dict]
        Physics step history.
    """

    journey_id: str = "anonymous"
    doer_state: np.ndarray = field(default_factory=lambda: np.zeros(12, dtype=np.float32))
    thinker_state: np.ndarray = field(default_factory=lambda: np.zeros(512, dtype=np.float32))
    knower_state: np.ndarray = field(default_factory=lambda: np.zeros(2048, dtype=np.float32))
    doer_weight: float = 0.33
    thinker_weight: float = 0.33
    knower_weight: float = 0.33
    kordylewski_cloud: str = "L4"
    stability_well: str = "basin"
    exotic_charge_density: float = 0.0
    phase: float = 0.0
    biography: list[dict[str, Any]] = field(default_factory=list)
    _last_coherence: float | None = None

    @property
    def coherence(self) -> float:
        """Return the last known HIHO coherence.

        Returns 0.5 if update_physics has not been called yet.
        """
        return self._last_coherence if self._last_coherence is not None else 0.5

    def __post_init__(self) -> None:
        self.journey_id = _sanitize_journey_id(self.journey_id)
        self.doer_state = np.ascontiguousarray(self.doer_state, dtype=np.float32)
        self.thinker_state = np.ascontiguousarray(self.thinker_state, dtype=np.float32)
        self.knower_state = np.ascontiguousarray(self.knower_state, dtype=np.float32)
        self.kordylewski_cloud = np.random.choice(["L4", "L5"])
        self.stability_well = np.random.choice(["basin", "hilltop"])
        weights = [self.doer_weight, self.thinker_weight, self.knower_weight]
        weights = [max(0.0, w) for w in weights]
        total = sum(weights)
        if total > 0:
            self.doer_weight, self.thinker_weight, self.knower_weight = [w / total for w in weights]
        else:
            self.doer_weight = self.thinker_weight = self.knower_weight = 1.0 / 3.0

    def update_physics(self, coherence: float, hiho_distance: float) -> None:
        """Record a physics step in the biography.

        NaN coherence is replaced with the last known coherence (not propagated).
        Phase accumulates at 0.1 rad/step. Exotic charge grows by 0.01/step.

        Parameters
        ----------
        coherence : float
            HIHO coherence [0, 1].
        hiho_distance : float
            Distance from HIHO attractor.
        """
        if coherence is None:
            coherence = self._last_coherence if self._last_coherence is not None else 0.0
        elif np.isnan(coherence):
            if self._last_coherence is not None:
                coherence = self._last_coherence
        self._last_coherence = coherence
        self.phase += 0.1
        self.exotic_charge_density = min(1.0, self.exotic_charge_density + 0.01)
        self.biography.append(
            {
                "coherence": coherence,
                "hiho_distance": hiho_distance,
                "phase": self.phase,
                "exotic_charge_density": self.exotic_charge_density,
                "doer_weight": self.doer_weight,
                "thinker_weight": self.thinker_weight,
                "knower_weight": self.knower_weight,
            }
        )

    def export_biography(self) -> dict[str, Any]:
        """Export physics biography as JSON-serializable dict."""
        return {
            "journey_id": self.journey_id,
            "triune_weights": {
                "doer": self.doer_weight,
                "thinker": self.thinker_weight,
                "knower": self.knower_weight,
            },
            "kordylewski_cloud": self.kordylewski_cloud,
            "stability_well": self.stability_well,
            "final_phase": self.phase,
            "final_exotic_charge_density": self.exotic_charge_density,
            "biography": self.biography,
        }

    def export_evp(self, output_dir: Path) -> None:
        """Export TRIUNE states as .npy files (atomic write).

        Writes three files: {journey_id}_doer.npy, _thinker.npy, _knower.npy.
        Uses temp-file-then-rename to prevent orphan files on crash.

        Parameters
        ----------
        output_dir : Path
            Directory to write .npy files.
        """
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        prefix = self.journey_id
        for name, arr in [("doer", self.doer_state), ("thinker", self.thinker_state), ("knower", self.knower_state)]:
            dest = output_dir / f"{prefix}_{name}.npy"
            try:
                with tempfile.NamedTemporaryFile(suffix=".npy", dir=output_dir, delete=False) as f:
                    np.save(f, arr)
                    f.flush()
                Path(f.name).rename(dest)
            except Exception:
                Path(f.name).unlink(missing_ok=True)
                raise

    @staticmethod
    def build_tracker(max_active: int = 20, spill_dir: Path | None = None) -> EVOTracker:
        """Build an EVOTracker with the given capacity.

        Parameters
        ----------
        max_active : int
            Maximum active EVs before LRU eviction (default 20).
        spill_dir : Path, optional
            Directory for .npy spillover files.
        """
        return EVOTracker(max_active=max_active, spill_dir=spill_dir)


class EVOTracker:
    """LRU registry for EVOs with disk spillover.

    Tracks active EVOs. When max_active is exceeded, the least recently
    used EVO is spilled to disk as .npy files and removed from memory.
    """

    def __init__(self, max_active: int = 20, spill_dir: Path | None = None) -> None:
        self.max_active = max_active
        self.spill_dir = Path(spill_dir) if spill_dir else None
        if self.spill_dir:
            self.spill_dir.mkdir(parents=True, exist_ok=True)
        self.active_evos: dict[str, EthericVariantOscillator] = {}
        self._access_order: list[str] = []

    def register(self, evo: EthericVariantOscillator) -> None:
        """Register an EVO, evicting LRU if at capacity."""
        if evo.journey_id in self.active_evos:
            self._touch(evo.journey_id)
            return
        if len(self.active_evos) >= self.max_active:
            lru_id = self._evict_lru()
            if lru_id and self.spill_dir:
                old = self.active_evos.pop(lru_id, None)
                if old:
                    old.export_evp(self.spill_dir)
        self.active_evos[evo.journey_id] = evo
        self._touch(evo.journey_id)

    def get(self, journey_id: str) -> EthericVariantOscillator | None:
        """Get an EVO by journey_id, loading from spillover if needed."""
        if journey_id in self.active_evos:
            self._touch(journey_id)
            return self.active_evos[journey_id]
        if self.spill_dir:
            prefix = journey_id
            doer_path = self.spill_dir / f"{prefix}_doer.npy"
            if doer_path.exists():
                evo = EthericVariantOscillator(journey_id=journey_id)
                evo.doer_state = np.load(doer_path)
                thinker_path = self.spill_dir / f"{prefix}_thinker.npy"
                knower_path = self.spill_dir / f"{prefix}_knower.npy"
                if thinker_path.exists():
                    evo.thinker_state = np.load(thinker_path)
                if knower_path.exists():
                    evo.knower_state = np.load(knower_path)
                self.active_evos[journey_id] = evo
                self._touch(journey_id)
                return evo
        return None

    def _touch(self, journey_id: str) -> None:
        """Update LRU order."""
        if journey_id in self._access_order:
            self._access_order.remove(journey_id)
        self._access_order.append(journey_id)

    def _evict_lru(self) -> str | None:
        """Evict least recently used EVO from active set."""
        if not self._access_order:
            return None
        lru_id = self._access_order.pop(0)
        self.active_evos.pop(lru_id, None)
        return lru_id
