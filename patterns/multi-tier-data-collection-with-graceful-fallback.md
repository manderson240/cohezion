---
title: "Multi-Tier Data Collection with Graceful Fallback"
date: "2026-02-24"
tags: [pattern]
---

## Problem

Data collection pipelines for agent training often have multiple possible sources with different quality, cost, and availability tradeoffs:
- **Hot**: Real-time agent interactions (ideal quality, expensive, may be unavailable)
- **Warm**: Recent simulation runs (good quality, fast, may be stale)
- **Cold**: Historical archive (lower quality, always available, very large)

A rigid pipeline that requires a specific source fails completely when that source is unavailable. A pipeline without fallback logic doesn't use cheaper sources when they're sufficient.

## Solution

Implement a tiered collector that tries sources in priority order, falling back gracefully when a source is unavailable or returns insufficient data. Track which tier was used so callers can make informed decisions about data quality.

## Code Example

```python
from dataclasses import dataclass
from enum import Enum
from typing import Callable
import logging

logger = logging.getLogger(__name__)

class DataTier(Enum):
    HOT = "hot"      # Real-time
    WARM = "warm"    # Recent simulation
    COLD = "cold"    # Historical archive

@dataclass
class CollectionResult:
    data: list
    tier: DataTier
    count: int
    source: str

class MultiTierCollector:
    def __init__(self, min_samples: int = 1000):
        self.min_samples = min_samples
        self._tiers: list[tuple[DataTier, Callable, str]] = []

    def register(self, tier: DataTier, collector_fn: Callable, source_name: str):
        """Register a collector at a given tier, in priority order."""
        self._tiers.append((tier, collector_fn, source_name))
        self._tiers.sort(key=lambda x: x[0].value)

    def collect(self, n_samples: int) -> CollectionResult:
        """Collect n_samples, falling back through tiers as needed."""
        for tier, collector_fn, source in self._tiers:
            try:
                data = collector_fn(n_samples)
                if len(data) >= self.min_samples:
                    logger.info(f"Collected {len(data)} samples from {tier.value} tier ({source})")
                    return CollectionResult(data=data, tier=tier, count=len(data), source=source)
                else:
                    logger.warning(
                        f"Tier {tier.value} returned {len(data)} samples (need {self.min_samples}), "
                        f"falling back"
                    )
            except Exception as e:
                logger.warning(f"Tier {tier.value} ({source}) failed: {e}, falling back")

        raise RuntimeError(f"All data collection tiers exhausted, could not collect {n_samples} samples")


# Usage
collector = MultiTierCollector(min_samples=500)
collector.register(DataTier.HOT, lambda n: live_agent_client.get_recent(n), "live-flume-agents")
collector.register(DataTier.WARM, lambda n: sim_cache.load_recent(n), "overnight-sim-cache")
collector.register(DataTier.COLD, lambda n: archive.sample(n), "historical-archive")

result = collector.collect(10_000)
print(f"Using {result.tier.value} data from {result.source} ({result.count} samples)")
```

## When to Use

- Data collection has multiple sources with different availability/quality/cost
- Production pipelines that must not fail completely when a preferred source is down
- Research pipelines where you want to use real data when available, simulation as fallback
- When callers need to know which data tier was used (quality-sensitive decisions)

**Monitoring**: Log which tier is used in each collection run. Frequent fallback to COLD tier is a signal that HOT/WARM sources need attention.

**Quality gates**: Consider refusing to train when data quality drops below a threshold (e.g., if only COLD data is available and the task is sensitive to distribution shift).

## Related

- [[experiments/2026-02-24-overnight-simulation-data-characterization-55m-trajectories]]
- [[decisions/2026-02-23-never-train-vae-on-random-noise-as-synthetic-data]]
