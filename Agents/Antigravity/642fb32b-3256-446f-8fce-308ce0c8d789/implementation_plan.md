---
type: antigravity-artifact
session_id: 642fb32b-3256-446f-8fce-308ce0c8d789
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.62
  stage: embryo
  synapse_in: 0
  synapse_out: 1
---

# Automated Model Replacement (LRU Swap)

The goal of this phase is to implement a "Smarter Swap" mechanism that automatically unloads the least recently used (LRU) models when the 96GB aggregate model load budget is reached.

## Proposed Changes

### [Component] Reliability & Monitoring

#### [MODIFY] [monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/monitor.py)
- **Usage Tracking**: Add a dictionary to track the last usage timestamp for each loaded model.
- **`track_model_usage(model_name: str)`**: Provide a method to update the usage timestamp when a model is called.
- **Timestamp Persistence**: Ensure timestamps are updated within the heartbeat loop by checking running models against the Ollama API.

### [Component] Swarm Agents

#### [MODIFY] [model_wrangler_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/model_wrangler_agent.py)
- **`unload_lru_model()`**: Implement logic to identify and unload the model with the oldest usage timestamp that is NOT protected (e.g., router).
- **Automated Swap**: Integrate the LRU swap into the budget enforcement logic. If a new model load would exceed the 96GB budget, proactively unload the LRU model(s) until space is available.
- **Usage Signals**: Ensure that all LLM calls from any agent signal the `ResourceMonitor` to update the usage timestamp for the active model.

## Verification Plan

### Automated Tests
1. **LRU Eviction Test**: Simulate several model loads that exceed the budget and verify that the oldest model is evicted first.
2. **Usage Tracking Test**: Verify that calling `track_model_usage` correctly updates the timestamp and influences the eviction order.

### Manual Verification
1. **Load Stress Test**: Load several large models manually and verify that the system automatically unloads the oldest one when the 96GB limit is hit.
2. **Log Inspection**: Check `logs/system_heartbeat.log` to see if LRU evictions are logged correctly.

## Related Vault Notes

- [[cohezion]]
