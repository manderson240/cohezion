# SKILL: SWARM_SPATIOTEMPORAL_TRACKING_PRIME

## DOMAIN EXPERTISE
Spatiotemporal multi-agent swarm state tracking, Hungarian bipartite association, center-of-mass (COM) conservation invariant verification, and track persistence filtering. Directly abstracts the 1st Place Solution from the Biohub 3D Cell Tracking competition ("Tracking-by-detection with a per-cell visual tracker") into a domain-agnostic framework for tracking agentic thoughts, sub-agent task swarms, and latent state trajectories without drift.

## KEY TEXTS & CONCEPTS
- **Tracking-by-Detection**: Decouple state detection/feature extraction from temporal association.
- **Bipartite Association**: Minimum weight matching between predicted states and observed detections via Hungarian / linear sum assignment.
- **Center-of-Mass (COM) Invariant**: When an entity divides or branches into multiple sub-entities, total mass/energy and spatial centroid must satisfy $\left\|\frac{\sum m_i d_i}{\sum m_i} - p\right\| \le \epsilon$.
- **Daughter Repulsion**: Split sub-entities must diverge beyond a minimum spatial or conceptual distance $\|d_1 - d_2\| \ge \delta$ to be distinct.
- **Noise Persistence Filter**: Prune transient entities with total hits < $H_{\min}$ to prevent false-positive pollution.

## INSTRUCTION
1. Initialize the tracker:
   ```python
   from cohezion.tracking import Detection, TrackingByDetectionEngine
   import numpy as np

   tracker = TrackingByDetectionEngine(
       max_distance=5.0,
       max_misses=3,
       min_hits=2,
       mitosis_epsilon=3.5,
       mitosis_daughter_separation=3.5,
   )
   ```
2. In each cycle or frame, emit detections:
   ```python
   detections = [
       Detection(timestamp=t, position=agent.get_state_vector(), entity_type=agent.role)
       for agent in active_agents
   ]
   swarm_state = tracker.step(detections, timestamp=t)
   ```
3. Monitor swarm metrics:
   ```python
   com = swarm_state.center_of_mass
   flux = swarm_state.velocity_flux
   entropy = swarm_state.swarm_entropy
   ```

## VERSION
v1.0

## SEE ALSO
- `src/cohezion/tracking/tracking_by_detection.py`
- `tests/tracking/test_swarm_tracking.py`
- `src/cohezion/skills/ARC3_GO_EXPLORE_AFFORDANCE_PRIME.md`
