---
title: "Morphospace Stability Wells"
date: "2026-02-24"
tags: [pattern]
aspect: thinker
neural:
  activation: 0.67
  stage: growing
  synapse_in: 13
  synapse_out: 6
---

## Problem

In a high-dimensional latent space (e.g., the FLUME 12D universe), agent trajectories tend to cluster in certain regions corresponding to stable behavioral modes. Without a way to identify and characterize these stable regions, it's difficult to:
- Detect when an agent has drifted away from a known-good behavioral mode
- Identify the behavioral repertoire of a trained agent
- Define "normal" vs. "anomalous" regions of trajectory space

## Solution

Model stable behavioral regions as **stability wells** in the morphospace (the geometric space of possible agent states). A stability well is a region in latent space where:
1. Trajectories spend more time than expected by chance
2. Trajectories that enter are slow to leave
3. Local trajectory curvature is low (smooth, consistent behavior)

Implementation approach:
1. **Identify wells**: Run KDE (kernel density estimation) on historical trajectories; peaks are well centers
2. **Characterize wells**: Compute average dwell time, entry/exit rates, trajectory curvature inside each well
3. **Assign semantics**: Associate each well with the agent behaviors that generate trajectories through it
4. **Monitor in real-time**: Track which well an agent's current trajectory is in; flag exits as potential drift

## Code Example

```python
from sklearn.neighbors import KernelDensity
import numpy as np

class MorphospaceStabilityWells:
    def __init__(self, bandwidth: float = 0.5, min_density: float = 0.01):
        self.kde = KernelDensity(bandwidth=bandwidth, kernel='gaussian')
        self.min_density = min_density
        self.well_centers = None
        self.well_radii = None

    def fit(self, trajectories: np.ndarray):
        """Fit to a set of trajectories (N, T, D) in latent space."""
        points = trajectories.reshape(-1, trajectories.shape[-1])
        self.kde.fit(points)

        # Find density peaks (potential well centers)
        # Use gradient ascent from random starts
        self.well_centers = self._find_density_peaks(points)

    def well_membership(self, point: np.ndarray) -> int:
        """Return index of nearest stability well, or -1 if in open space."""
        if self.well_centers is None:
            raise ValueError("Must fit before predicting")

        log_density = self.kde.score_samples(point.reshape(1, -1))
        if log_density < np.log(self.min_density):
            return -1  # In open space, no well

        dists = np.linalg.norm(self.well_centers - point, axis=1)
        return np.argmin(dists)

    def is_drifting(self, trajectory_segment: np.ndarray) -> bool:
        """Detect if a recent trajectory segment shows drift from stable well."""
        wells = [self.well_membership(p) for p in trajectory_segment]
        # Drift: started in a well, now outside or in different well
        return wells[0] != -1 and wells[-1] != wells[0]
```

## When to Use

- You have a corpus of historical agent trajectories and want to understand the behavioral landscape
- You need drift detection that's sensitive to behavioral mode changes, not just position changes
- You want to characterize agent behavior in interpretable terms (which stability wells does it visit?)
- Anomaly detection: trajectories outside all known wells are candidates for inspection

**Prerequisites**: Sufficient trajectory data to estimate density reliably (~10K+ trajectory points). The well structure is only as good as the coverage of the training trajectories.

**Not appropriate for**: Early training when trajectory data is sparse, or agents with continuously evolving behavior where stable wells don't exist.

## Related

- [[bioelectric-field-modeling-for-action-generation]]
- [[momentum-based-trajectory-prediction-with-counterfactuals]]
- [[2026-02-23-enforce-no-orphan-modules-policy]]
- [[2026-02-24-anti-pattern-disconnected-modules-without-consumers]] — this pattern is the vault preservation of an orphan module (morphospace.py)
- [[anomaly-detection]] — stability wells define "normal" behavioral regions; trajectories outside all known wells are anomaly candidates
- [[agent-journey-tracking]] — the 12D journey tracking system whose trajectories form the input data for well identification
