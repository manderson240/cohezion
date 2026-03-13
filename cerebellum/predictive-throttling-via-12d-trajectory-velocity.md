---
title: "Predictive Throttling via 12D Trajectory Velocity"
date: "2026-02-22"
tags: [pattern, performance, trajectory, throttling, 12d-graph]
aspect: thinker
neural:
  activation: 0.76
  stage: growing
  synapse_in: 13
  synapse_out: 8
---

# Predictive Throttling via 12D Trajectory Velocity

## Problem

Agent sessions and simulation processes consume variable amounts of compute resources depending on the complexity of their current task. Without adaptive resource management, either: (a) resources are over-provisioned for simple tasks (waste), or (b) resources are under-provisioned for complex tasks (degradation or failure). Static resource allocation does not account for the fact that an agent's compute needs change as it moves through different phases of a task.

In the context of the Cohezion 12D trajectory system, each agent or simulation entity has a position in 12-dimensional semantic space. The velocity of movement through this space (how fast the 12D position changes per time step) correlates with computational demand: fast-moving entities are exploring new territory (high compute), while slow-moving entities are converging on a solution (low compute).

## Solution

Use the **velocity of an entity's 12D trajectory** as a predictive signal for resource throttling. The approach has three components:

### 1. Velocity Calculation
Compute the magnitude of the 12D velocity vector between consecutive trajectory snapshots:

```python
import numpy as np

def trajectory_velocity(pos_t: np.ndarray, pos_t_minus_1: np.ndarray, dt: float) -> float:
    """Calculate the speed of movement through 12D semantic space."""
    displacement = pos_t - pos_t_minus_1
    return float(np.linalg.norm(displacement) / dt)
```

### 2. Throttle Mapping
Map velocity to resource allocation using configurable thresholds:

```python
def compute_throttle_level(velocity: float, thresholds: dict) -> str:
    """Map 12D velocity to a resource throttle level.

    Low velocity → entity is converging → reduce resources
    High velocity → entity is exploring → increase resources
    """
    if velocity < thresholds["low"]:
        return "minimal"    # 25% resources — entity is nearly stationary
    elif velocity < thresholds["medium"]:
        return "standard"   # 50% resources — normal operation
    elif velocity < thresholds["high"]:
        return "elevated"   # 75% resources — active exploration
    else:
        return "maximum"    # 100% resources — rapid phase transition

# Example thresholds (calibrated from overnight simulation data)
DEFAULT_THRESHOLDS = {
    "low": 0.01,      # Converged — barely moving in latent space
    "medium": 0.1,    # Normal — steady progress
    "high": 0.5,      # Active — exploring new territory
}
```

### 3. Resource Application
Apply the throttle level to actual resource controls (concurrency limits, batch sizes, timeout budgets):

```python
RESOURCE_MAP = {
    "minimal":  {"concurrency": 1, "batch_size": 10,  "timeout_s": 30},
    "standard": {"concurrency": 2, "batch_size": 50,  "timeout_s": 60},
    "elevated": {"concurrency": 4, "batch_size": 100, "timeout_s": 120},
    "maximum":  {"concurrency": 8, "batch_size": 200, "timeout_s": 300},
}
```

## When to Use

- **Long-running simulations** where compute cost is proportional to time — throttling slow-moving entities saves significant resources
- **Multi-agent orchestration** where agents compete for shared resources — throttle converged agents to free resources for exploring agents
- **Budget-constrained environments** where total compute budget is fixed — predictive throttling maximizes useful work per dollar
- **N-body simulations** (e.g., [[universe-simulation]]) where entity density varies across the simulation space

**Prerequisites:**
- Entities must have meaningful 12D trajectory positions (semantic, not hash-based — see [[2026-02-24-anti-pattern-hash-based-journey-tracking-destroys-semantic-meaning]])
- Sufficient trajectory history for velocity calculation (minimum 2 snapshots)
- Calibrated thresholds from representative data (e.g., [[2026-02-23-overnight-simulation-data-characterization-55m-trajectories]])

## Related Patterns

- [[momentum-based-trajectory-prediction-with-counterfactual-branching]] — the complementary trajectory prediction pattern; where this pattern throttles, that pattern branches into futures
- [[structured-experience-vector-layout]] — the 12D vector layout that defines the semantic space through which trajectories move
- [[12d-graph-implementation]] — the visualization system that displays the trajectories being throttled

## Related Decisions

- [[2026-02-24-anti-pattern-hash-based-journey-tracking-destroys-semantic-meaning]] — trajectory velocity throttling is meaningless if 12D positions are hash-based; semantic coordinates are a prerequisite
- [[2026-02-23-overnight-simulation-data-characterization-55m-trajectories]] — the data characterization study that informs velocity thresholds

## Related Concepts

- [[universe-simulation]] — the N-body simulation that produces the 12D trajectories used as input
- [[machine-learning-optimization]] — predictive throttling is a form of adaptive resource optimization
- [[anomaly-detection]] — sudden velocity spikes may indicate anomalous agent behavior worth investigating
