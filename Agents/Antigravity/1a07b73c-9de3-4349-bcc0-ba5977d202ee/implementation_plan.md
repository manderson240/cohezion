---
type: antigravity-artifact
session_id: 1a07b73c-9de3-4349-bcc0-ba5977d202ee
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.64
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# Implementation Plan: Journey Substrate Hardening

The Cohezion "Journey 3.0 (EVO Cosmology)" implementation caused a full system crash due to resource exhaustion during high-fidelity simulations. This plan hardens the substrate by introducing sliding windows for event storage, caching expensive truth anchors (git hash), and optimizing hardware vitals polling.

## Proposed Changes

### Swarm Perception

#### [MODIFY] [perception.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/perception.py)

- **Sliding Window**: Implement `MAX_EVENTS = 1000` for `JourneyPerception.events` to prevent OOM during million-epoch simulations.
- **Git Hash Caching**: Cache the git hash in `JourneyPerception.__init__` instead of calling `subprocess` in every `perceive_step`.
- **Rust Manifold Bridge**: Offload the 2048D -> 256D "Filament" collapse to the `cohezion_core_rs` Rust bridge to reduce Python overhead.
- **Optimization**: Use `np.mean` more efficiently and ensure `CosmologicalPoint` doesn't hold references to larger-than-necessary arrays.

### Universe Engine

#### [MODIFY] [engine.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/universe/engine.py)

- **Vitals Caching**: Implement a 1-second TTL cache for `ResourceMonitor.get_vitals()` calls to reduce I/O and CPU overhead in tight loops.
- **Singleton Physics**: Cache the `FlumePhysics` instance to avoid redundant initialization overhead.
- **Apoptosis Pulse**: Integrate with `ResourceMonitor` to trigger an immediate `events.clear()` or sharding event if system RAM exceeds a "Critical Coherence" threshold (e.g., 90%).

---

### Reliability Monitor

#### [MODIFY] [monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/monitor.py)

- **Throttle `get_vitals`**: Add a small internal cache or recommend callers to use a cached version.

## Verification Plan

### Automated Tests

- **Performance Regression**:
  ```bash
  pytest tests/unit/test_universe_engine.py
  pytest tests/test_journey_tracker.py
  ```
- **OOM Stress Test**:
  Create `scripts/tests/test_perception_oom.py` to run 100,000 `perceive_step` calls and verify memory stays stable.
- **Subprocess Efficiency**:
  Verify zero logic change, but measure execution time of `perceive_step` before and after.

### Manual Verification

- **Tsunami Resume**:
  Run `scripts/drivers/tsunami_simulator.py` for 10,000 epochs and verify the "📍 Epoch" logs appear without system slowdown.
- **Resource Hub**:
  Observe `logs/system_heartbeat.log` to ensure it continues to record without being flooded by `engine.py` requests.

## Related Vault Notes

- [[cohezion]]
- [[cosmology]]
