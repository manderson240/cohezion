"""Cohezion Dogfooding Framework.

Production-ready dogfooding infrastructure including:
- Daily automation cycles
- Production hardening checks
- CI/CD integration
- Performance monitoring
- Disaster recovery

Usage:
    # Daily cycle
    python -m cohezion.dogfooding.daily_cycle

    # Production hardening
    python -m cohezion.dogfooding.production_hardening
"""

__version__ = "1.0.0"
__all__ = [
    "CIIntegration",
    "DailyDogfoodingCycle",
    "DisasterRecovery",
    "PerformanceMonitor",
    "ProductionHardening",
]

from .daily_cycle import DailyDogfoodingCycle
from .production_hardening import (
    CIIntegration,
    DisasterRecovery,
    PerformanceMonitor,
    ProductionHardening,
)
