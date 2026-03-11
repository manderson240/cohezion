"""Universe State API Service.

Exposes real HIHO physics engine state (coherence, EVO states, CA grid)
via FastAPI endpoints for the Anima Dashboard.

The service holds a singleton physics simulation that advances on each
tick, driven by the actual HIHOUnifiedEngine with its CA, MHD, Chaos,
and HIHO stabilization engines.
"""

from __future__ import annotations

import asyncio
import json
import logging
from collections import deque
from typing import Any

import numpy as np
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from cohezion.compound.topological_persistence import TopologicalPersistence
from cohezion.universe.hiho_unified_engine import (
    CellularAutomataEngine,
    CellularAutomataState,
    ChaosTheoryEngine,
    ChaosTheoryParameters,
    EVOInitializationFactory,
    EvoState,
    HIHOStabilizationEngine,
    MagnetohydrodynamicsEngine,
)


logger = logging.getLogger(__name__)

universe_router = APIRouter(tags=["universe"])


# --- Response Models ---


class UniverseStateResponse(BaseModel):
    """Snapshot of the universe physics state."""

    tick: int = Field(description="Current simulation tick")
    coherence: float = Field(description="Mean coherence across all EVOs")
    ca_grid: list[int] = Field(description="Cellular automata grid state (256 cells)")
    evo_states: list[dict[str, Any]] = Field(description="EVO charge cluster states")
    time: float = Field(description="Simulation time")


class EvoHealthEntry(BaseModel):
    id: int
    coherence: float
    charge_density: float
    charge_status: str
    magnetic_helicity: float
    toroidal_moment: float


class HIHOStatusReport(BaseModel):
    mean_coherence: float
    stability: str
    deviation_from_target: float
    target: float = 0.5


class CAAnalysis(BaseModel):
    density: float
    active_cells: int
    total_cells: int
    rule: int


class TopologyPairEntry(BaseModel):
    birth: float
    death: float
    dimension: int
    persistence: float


class TopologyData(BaseModel):
    """Persistent homology summary of universe trajectory."""

    persistence_pairs: list[TopologyPairEntry]
    entropy: float = Field(description="Persistence entropy (topological complexity)")
    n_clusters: int = Field(description="Significant H0 features")
    n_loops: int = Field(description="Significant H1 features")


class SynthesisReport(BaseModel):
    """Full physics synthesis report for the Anima Dashboard."""

    tick: int
    time: float
    hiho_status: HIHOStatusReport
    ca_analysis: CAAnalysis
    evo_health: list[EvoHealthEntry]
    summary: str
    topology: TopologyData | None = None


VALID_PERTURBATIONS = {"coherence_spike", "coherence_collapse", "charge_injection", "ca_reset"}


class PerturbRequest(BaseModel):
    kind: str = Field(description="Type of perturbation to apply")
    magnitude: float = Field(default=0.2, description="Strength of perturbation (0.0-1.0)")


# --- Service ---


class UniverseStateService:
    """Manages a live HIHO universe simulation.

    Instantiates real physics engines (CA, MHD, Chaos, HIHO) and a swarm
    of EVOs.  Each tick advances the simulation synchronously — no
    external Plasma MCP dependency required for the dashboard.
    """

    def __init__(self, num_evos: int = 8, ca_rule: int = 30) -> None:
        self._tick = 0
        self._time = 0.0
        self._dt = 0.01
        self._max_history = 1000
        self._history: deque[UniverseStateResponse] = deque(maxlen=1000)

        # Physics engines (same ones used in HIHOUnifiedEngine)
        self._ca = CellularAutomataEngine(CellularAutomataState(rule=ca_rule))
        self._chaos = ChaosTheoryEngine(ChaosTheoryParameters(lyapunov_exponent=0.05))
        self._mhd = MagnetohydrodynamicsEngine()
        self._hiho = HIHOStabilizationEngine()

        # Initialize EVOs at the HIHO boundary (coherence = 0.5)
        self._evos: list[EvoState] = [
            EVOInitializationFactory.create_evo(seed=i) for i in range(num_evos)
        ]
        # 12D latent vectors for each EVO
        self._vectors: list[np.ndarray] = [
            np.random.default_rng(i).standard_normal(12) for i in range(num_evos)
        ]

    def tick(self) -> UniverseStateResponse:
        """Advance the simulation by one step and return the new state."""
        self._tick += 1
        self._time += self._dt

        # 1. Evolve the CA fabric
        self._ca.evolve()

        # 2. Apply physics to each EVO
        for i, (evo, vec) in enumerate(zip(self._evos, self._vectors, strict=True)):
            # Chaos butterfly effect
            vec = self._chaos.apply_butterfly_effect(vec, self._time)
            # MHD plasma stability
            vec = self._mhd.apply_mhd_forces(evo, vec, self._dt)
            # HIHO coherence restoring force
            evo, vec = self._hiho.apply_hiho_loop(evo, vec, self._dt)
            self._vectors[i] = vec

        state = self.get_state()
        self._history.append(state)
        return state

    def get_history(self, limit: int = 100) -> list[UniverseStateResponse]:
        """Return the last N tick snapshots from the bounded history."""
        entries = list(self._history)
        return entries[-limit:]

    def get_history_summary(self) -> dict[str, Any]:
        """Summarize recent history for Re-Entry Narrative (FR13)."""
        history = list(self._history)
        if not history:
            return {
                "ticks_elapsed": 0,
                "mean_coherence": 0.5,
                "coherence_range": {"min": 0.5, "max": 0.5},
                "alert_count": 0,
                "ca_density_trend": 0.0,
                "narrative": "No history yet. The universe awaits its first tick.",
            }
        coherences = [h.coherence for h in history]
        mean_c = float(np.mean(coherences))
        min_c = float(min(coherences))
        max_c = float(max(coherences))
        std_c = float(np.std(coherences))
        alert_count = sum(1 for c in coherences if c < 0.3 or c > 0.7)
        ca_densities = [sum(h.ca_grid) / len(h.ca_grid) if h.ca_grid else 0 for h in history]
        ca_trend = float(ca_densities[-1] - ca_densities[0]) if len(ca_densities) > 1 else 0.0

        narrative = (
            f"Welcome back. While you were away, {len(history)} ticks elapsed. "
            f"Coherence held at {mean_c:.4f} +/- {std_c:.4f}. "
        )
        if alert_count > 0:
            narrative += f"{alert_count} coherence alert(s) were detected. "
        narrative += f"CA density settled at {ca_densities[-1] * 100:.1f}%."

        return {
            "ticks_elapsed": len(history),
            "mean_coherence": mean_c,
            "coherence_range": {"min": min_c, "max": max_c},
            "alert_count": alert_count,
            "ca_density_trend": ca_trend,
            "narrative": narrative,
        }

    def get_state(self) -> UniverseStateResponse:
        """Return the current universe state without advancing."""
        mean_coherence = float(np.mean([e.coherence for e in self._evos]))
        evo_dicts = [
            {
                "charge_density": e.charge_density,
                "magnetic_helicity": e.magnetic_helicity,
                "toroidal_moment": e.toroidal_moment,
                "coherence": e.coherence,
            }
            for e in self._evos
        ]
        return UniverseStateResponse(
            tick=self._tick,
            coherence=mean_coherence,
            ca_grid=list(self._ca.config.state),
            evo_states=evo_dicts,
            time=self._time,
        )

    def get_report(self) -> SynthesisReport:
        """Generate a synthesis report analyzing current physics state."""
        coherences = [e.coherence for e in self._evos]
        mean_c = float(np.mean(coherences))
        deviation = abs(mean_c - 0.5)

        if deviation < 0.1:
            stability = "stable"
        elif deviation < 0.3:
            stability = "warning"
        else:
            stability = "critical"

        ca_grid = self._ca.config.state
        active = sum(ca_grid)
        total = len(ca_grid)
        density = active / total if total > 0 else 0.0

        evo_health = []
        for i, evo in enumerate(self._evos):
            if evo.charge_density > 0.8:
                charge_status = "nominal"
            elif evo.charge_density > 0.4:
                charge_status = "decaying"
            else:
                charge_status = "depleted"
            evo_health.append(
                EvoHealthEntry(
                    id=i,
                    coherence=evo.coherence,
                    charge_density=evo.charge_density,
                    charge_status=charge_status,
                    magnetic_helicity=evo.magnetic_helicity,
                    toroidal_moment=evo.toroidal_moment,
                )
            )

        nominal_count = sum(1 for e in evo_health if e.charge_status == "nominal")
        summary = (
            f"HIHO {stability.upper()}: {mean_c:.4f} coherence "
            f"(deviation {deviation:.4f} from 0.5 target). "
            f"CA Rule {self._ca.config.rule}: {active}/{total} cells active "
            f"({density * 100:.1f}% density). "
            f"{nominal_count}/{len(self._evos)} EVOs nominal."
        )

        # Compute topology from EVO coherence trajectory
        topology = self._compute_topology()

        return SynthesisReport(
            tick=self._tick,
            time=self._time,
            hiho_status=HIHOStatusReport(
                mean_coherence=mean_c,
                stability=stability,
                deviation_from_target=deviation,
            ),
            ca_analysis=CAAnalysis(
                density=density,
                active_cells=active,
                total_cells=total,
                rule=self._ca.config.rule,
            ),
            evo_health=evo_health,
            summary=summary,
            topology=topology,
        )

    def _compute_topology(self) -> TopologyData | None:
        """Compute persistent homology from EVO coherence trajectory."""
        history = list(self._history)
        if len(history) < 3:
            return None

        # Build point cloud: each tick's EVO coherences as a vector
        points = np.array(
            [
                [e["coherence"] for e in snap.evo_states]
                for snap in history[-50:]  # Last 50 ticks max
            ]
        )
        if points.shape[0] < 3:
            return None

        try:
            topo = TopologicalPersistence(max_dimension=1)
            dgm = topo.compute_persistence(points)
            pairs = [
                TopologyPairEntry(
                    birth=p.birth,
                    death=p.death if not np.isinf(p.death) else 999.0,
                    dimension=p.dimension,
                    persistence=p.persistence if not np.isinf(p.persistence) else 999.0,
                )
                for p in dgm.pairs
            ]
            return TopologyData(
                persistence_pairs=pairs,
                entropy=dgm.persistence_entropy(),
                n_clusters=dgm.n_significant_features(0, threshold=0.01),
                n_loops=dgm.n_significant_features(1, threshold=0.01),
            )
        except Exception:
            logger.debug("Topology computation failed", exc_info=True)
            return None

    def perturb(self, kind: str, magnitude: float) -> UniverseStateResponse:
        """Apply a perturbation to the universe and return the new state."""
        mag = max(0.0, min(1.0, magnitude))  # Clamp to safe range

        if kind == "coherence_spike":
            for evo in self._evos:
                evo.coherence = min(1.0, evo.coherence + mag)
        elif kind == "coherence_collapse":
            for evo in self._evos:
                evo.coherence = max(0.0, evo.coherence - mag)
        elif kind == "charge_injection":
            for evo in self._evos:
                evo.charge_density += mag
        elif kind == "ca_reset":
            grid_size = self._ca.config.grid_size
            self._ca.config.state = [0] * grid_size
            self._ca.config.state[grid_size // 2] = 1

        return self.get_state()


# --- Singleton ---

_service: UniverseStateService | None = None


def get_universe_service() -> UniverseStateService:
    global _service
    if _service is None:
        _service = UniverseStateService()
    return _service


# --- Endpoints ---


@universe_router.get("/state", response_model=UniverseStateResponse)
async def get_universe_state() -> UniverseStateResponse:
    """Return the current universe physics state."""
    return get_universe_service().get_state()


@universe_router.post("/tick", response_model=UniverseStateResponse)
async def tick_universe() -> UniverseStateResponse:
    """Advance the universe by one physics tick and return the new state."""
    return get_universe_service().tick()


@universe_router.get("/report", response_model=SynthesisReport)
async def get_synthesis_report() -> SynthesisReport:
    """Generate a synthesis report analyzing the current universe physics state."""
    return get_universe_service().get_report()


@universe_router.post("/perturb", response_model=UniverseStateResponse)
async def perturb_universe(req: PerturbRequest) -> UniverseStateResponse:
    """Inject a perturbation into the universe to study HIHO recovery dynamics."""
    if req.kind not in VALID_PERTURBATIONS:
        from fastapi import HTTPException

        raise HTTPException(
            status_code=422,
            detail=f"Invalid perturbation kind: {req.kind!r}. Valid: {sorted(VALID_PERTURBATIONS)}",
        )
    return get_universe_service().perturb(req.kind, req.magnitude)


@universe_router.get("/history")
async def get_universe_history(
    limit: int = Query(default=100, ge=1, le=1000),
) -> list[dict[str, Any]]:
    """Return recent tick history from the bounded deque."""
    svc = get_universe_service()
    return [s.model_dump() for s in svc.get_history(limit)]


@universe_router.get("/history/summary")
async def get_history_summary() -> dict[str, Any]:
    """Re-Entry Narrative: summarize recent history for returning users."""
    return get_universe_service().get_history_summary()


@universe_router.get("/stream")
async def stream_universe(
    max_ticks: int | None = Query(default=None, ge=1),
) -> StreamingResponse:
    """SSE endpoint streaming live universe ticks.

    Each tick emits an ``event: tick`` with the universe state JSON.
    Every 10th tick also emits an ``event: report`` with the synthesis report.
    Alerts fire when coherence exits the [0.3, 0.7] range.
    Pass ``max_ticks`` to limit the stream (useful for testing).
    """
    svc = get_universe_service()

    async def event_generator():  # type: ignore[no-untyped-def]
        ticks_sent = 0
        while max_ticks is None or ticks_sent < max_ticks:
            state = svc.tick()
            payload = state.model_dump()
            yield f"event: tick\ndata: {json.dumps(payload)}\n\n"
            ticks_sent += 1

            # Report every 10th tick
            if state.tick % 10 == 0:
                report = svc.get_report()
                yield f"event: report\ndata: {json.dumps(report.model_dump())}\n\n"

            # Alert when coherence exits safe band
            if state.coherence < 0.3 or state.coherence > 0.7:
                zone = "low" if state.coherence < 0.3 else "high"
                alert = {
                    "kind": f"coherence_{zone}",
                    "message": f"Coherence {state.coherence:.4f} outside [0.3, 0.7]",
                }
                yield f"event: alert\ndata: {json.dumps(alert)}\n\n"

            await asyncio.sleep(0.1)  # 10 Hz tick rate

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "Connection": "keep-alive"},
    )
