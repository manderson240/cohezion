"""
Universe Telemetry: Unified schema for physical manifold capture.
Integrates 12D axiomatic states, stability shifts, and causal linkage to agent journeys.
"""

from __future__ import annotations

import time

from pydantic import BaseModel, ConfigDict, Field, field_validator


class UniverseStateEvent(BaseModel):
    """
    Telemetry event representing a significant shift in the physical universe manifold.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "event_id": "ue_123",
                "universe_id": "uni_prime_001",
                "state_12d": [0.5] * 12,
                "coherence": 0.5002,
                "stability_shift": 0.07,
                "trigger_journey_id": "journey_alpha_001",
            }
        }
    )

    event_id: str
    universe_id: str
    timestamp: float = Field(default_factory=time.time)

    # 12D Axiomatic State [X,Y,Z,T,Mass,Sent,Comp,Fact,Conn,Stab,Nov,Precip]
    state_12d: list[float] = Field(..., description="12D axiomatic state vector")

    # Stability and Coherence
    coherence: float = Field(..., description="Current HIHO coherence (Target: 0.5)")
    stability_shift: float = Field(0.0, description="Stability delta since last emission")

    # Causal Linkage (Geometric Overlap)
    trigger_journey_id: str | None = Field(
        None, description="The agentic journey that triggered this shift"
    )

    @field_validator("state_12d")
    @classmethod
    def validate_12d_length(cls, v: list[float]) -> list[float]:
        if len(v) != 12:
            raise ValueError("state_12d must have exactly 12 dimensions")
        return v
