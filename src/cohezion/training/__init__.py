"""Distributed training support for FLUME models.

Provides FSDP, DeepSpeed, and Accelerate integration.
"""

from .distributed import (
    DistributedConfig,
    DistributedTrainer,
    is_available,
    setup_from_environment,
)


__all__ = [
    "DistributedConfig",
    "DistributedTrainer",
    "is_available",
    "setup_from_environment",
]
