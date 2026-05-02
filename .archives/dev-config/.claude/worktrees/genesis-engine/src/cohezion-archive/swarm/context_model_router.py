"""Context-aware model router with profiles for memory optimization.

Provides ModelContextProfile for managing model configurations
and optimal context window calculations.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass
class ModelContextProfile:
    """Context-aware model profile for memory optimization.

    Defines model characteristics and computes optimal context windows
    based on available memory.
    """

    name: str
    total_params_b: float  # Total parameters in billions
    size_gb: float = 0.0  # Model size in GB
    quantization: str = "Q4"  # Quantization type (Q4, Q8, FP16)
    is_moe: bool = False  # Whether model is Mixture of Experts
    active_params_b: float | None = None  # Active parameters for MoE

    def __post_init__(self):
        """Initialize computed fields."""
        if self.active_params_b is None:
            self.active_params_b = self.total_params_b

    def to_dict(self) -> dict[str, Any]:
        """Convert profile to dictionary."""
        return {
            "name": self.name,
            "total_params_b": self.total_params_b,
            "size_gb": self.size_gb,
            "quantization": self.quantization,
            "is_moe": self.is_moe,
            "active_params_b": self.active_params_b,
        }
