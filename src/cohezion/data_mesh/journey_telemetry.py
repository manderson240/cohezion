"""
Journey Telemetry: Unified schema for agentic journey capture.
Integrates FLUME latent states, 12D trajectories, and JEPA prediction errors.
Aligned with Google Labs Stitch and Cohezion V-Model standards.
"""

from __future__ import annotations

import time
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, Field


class HardwareTier(StrEnum):
    NPU = "npu"
    IGPU = "igpu"
    CPU = "cpu"
    CLOUD = "cloud"


class SwarmExpert(StrEnum):
    ARCHITECT = "architect"
    ENGINEER = "engineer"
    BIOLOGIST = "biologist"
    QUANTUM_HW = "quantum_hw"
    QUANTUM_ALGO = "quantum_algo"


class QuadratureFabrics(BaseModel):
    space: float = Field(..., description="Geometric substrate stability")
    field: float = Field(..., description="Latent energy density")
    control: float = Field(..., description="Orchestration overhead")
    precipitation: float = Field(..., description="Value/Artifact generation")


class RZeroMetrics(BaseModel):
    success_rate: float
    iteration_count: int
    difficulty_adjustment: float


class FlumeJourneyEvent(BaseModel):
    """
    The 'Akashic Record' of a single agentic decision node.
    Captures the full 2048D -> 256D -> 12D manifold descent.
    """

    event_id: str
    journey_id: str
    timestamp: float = Field(default_factory=time.time)

    # 1. Latent State (The Knower)
    z_vector: list[float] = Field(..., description="256-dim FLUME latent thought vector")
    predicted_z_vector: list[float] | None = Field(None, description="JEPA world-model prediction")
    prediction_error: float = Field(
        0.0, description="Surprise/L2 delta between actual and predicted z"
    )

    # 2. Axiomatic State (The Doer)
    state_12d: list[float] = Field(
        ..., description="12D down-projected state [X,Y,Z,T,Coh,Ent,Awa,Int,Per,Mem,Nov,Int]"
    )
    coherence: float = Field(0.5, description="HIHO stability metric (Target: 0.5)")

    # 3. Fabric & Awareness (The Thinker)
    fabrics: QuadratureFabrics
    awareness_parameter: float = Field(..., description="The 1st parameter of the Quadrature Model")

    # 4. Routing & Execution
    expert_stream: SwarmExpert
    hardware_tier: HardwareTier
    latency_ms: float

    # 5. Evolutionary Metrics
    r_zero: RZeroMetrics

    metadata: dict[str, Any] = Field(default_factory=dict)

    class Config:
        json_schema_extra = {
            "example": {
                "journey_id": "journey_alpha_001",
                "z_vector": [0.1] * 256,
                "state_12d": [0.5] * 12,
                "coherence": 0.5008,
                "awareness_parameter": 0.95,
                "hardware_tier": "npu",
                "expert_stream": "architect",
            }
        }
