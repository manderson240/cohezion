"""
Audio Telemetry: Unified schema for bioacoustic monitoring.
Aligned with BirdCLEF 2026 requirements and Cohezion V-Model standards.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, List, Optional

import numpy as np
from pydantic import BaseModel, Field


class TaxonomyLevel(str, Enum):
    CLASS = "class"
    ORDER = "order"
    FAMILY = "family"
    GENUS = "genus"
    SPECIES = "species"


class BirdSpeciesNode(BaseModel):
    """SurrealDB node representation for a bird species."""
    
    species_code: str = Field(..., description="Unique code (e.g., 'rubthr1')")
    scientific_name: str
    common_name: str
    inat_taxon_id: Optional[int] = None
    taxonomy: dict[TaxonomyLevel, str] = Field(default_factory=dict)
    
    def to_surreal_record(self) -> dict[str, Any]:
        return {
            "id": f"bird_species:{self.species_code}",
            **self.model_dump()
        }


class AudioSegmentMetadata(BaseModel):
    """Metadata for a 5-second audio window."""
    
    filename: str
    offset_seconds: float
    duration_seconds: float = 5.0
    sample_rate: int = 32000
    primary_label: str
    secondary_labels: List[str] = Field(default_factory=list)
    latitude: float
    longitude: float
    date: str


class SpectrogramConfig(BaseModel):
    """Configuration for mel-spectrogram generation."""
    
    n_mels: int = 128
    fmin: int = 0
    fmax: int = 16000
    hop_length: int = 512
    n_fft: int = 2048


@dataclass
class AudioTelemetryEvent:
    """Event emitted during audio processing/inference."""
    
    metadata: AudioSegmentMetadata
    timestamp: str = field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    event_type: str = "audio_inference"
    predictions: dict[str, float] = field(default_factory=dict)
    coherence: float = 0.0
    hardware_tier: str = "cpu"
    
    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "metadata": self.metadata.model_dump(),
            "predictions": self.predictions,
            "coherence": self.coherence,
            "hardware_tier": self.hardware_tier,
        }
