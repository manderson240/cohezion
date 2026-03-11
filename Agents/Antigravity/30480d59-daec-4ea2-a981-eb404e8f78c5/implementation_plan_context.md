---
type: antigravity-artifact
session_id: 30480d59-daec-4ea2-a981-eb404e8f78c5
date: 2026-03-04
title: "Implementation Plan Context"
aspect: doer
neural:
  activation: 0.337
  stage: embryo
  cluster: Agents
---

# Scalar Context & Session Handoff Optimization

Optimize the RLM (Recursive Language Model) context management system with scalar importance and implement automated session handoffs for long-horizon continuity.

## User Review Required

> [!IMPORTANT]
> This plan involves moving from keyword-based heuristics to **embedding-based importance** using `nomic-embed-text`. 
> It also introduces a `HandoffAgent` that will automatically synthesize session snapshots.

## Proposed Changes

### [RLM & Context]

#### [MODIFY] [scalar_context_manager.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/rlm/scalar_context_manager.py)
- Upgrade `calculate_importance` to use `FlumeEncoder.similarity(query, segment)`.
- Integrate **12D Physics State**: Boost segments where `stability > 0.9` correlate with the query.
- Implement `recursive_summarize`: Sub-call `phi3:mini` for segments with `scalar < 0.6`.

#### [MODIFY] [rlm_reasoning_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/rlm_reasoning_agent.py)
- Integrate `ScalarContextManager` into the reasoning loop.
- Use scalar scores to decide which segments to "DIVE" (full text) vs "SUMMARIZE".
- Pass `12d_state` to context manager for relativistic weighting.

### [Memory & Handoffs]

#### [NEW] [handoff_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/handoff_agent.py)
- Create an agent specialized in "Session Synthesis".
- Generates `SESSION_SNAPSHOT` nodes in SurrealDB.
- Captures: Key Discoveries, Blockers, 12D Trajectory Summary, and Next Steps.
- Uses `deepseek-r1:70b` for high-quality synthesis.

#### [MODIFY] [controller_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/controller_agent.py)
- Add `handoff` node to the LangGraph state machine.
- Set `handoff` as the penultimate node before `END`.
- Automatically trigger if `state["urgency"] == "high"` or session time exceeds 1 hour.

### [Visualization]

#### [MODIFY] [journey_tracker.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/journey_tracker.py)
- Add "Historical Context" links to `JourneyStep`.
- Allow the visualizer to trace back to previous session anchors.

## Verification Plan

### Automated Tests
- `tests/test_scalar_context.py`: Verify that "High Relevance" segments are prioritized and embeddings are correctly calculated.
- `tests/test_handoff.py`: Verify that `SESSION_SNAPSHOT` is correctly generated and retrieved by a "fresh" agent.

### Manual Verification
- Run a deep-dive research query and inspect the RLM logs to see importance-based summarization in action.
