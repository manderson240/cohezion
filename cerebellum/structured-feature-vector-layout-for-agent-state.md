---
title: "Structured Feature Vector Layout for Agent State"
date: "2026-02-24"
tags: [pattern]
aspect: thinker
neural:
  activation: 0.67
  stage: growing
  synapse_in: 4
  synapse_out: 4
---

## Problem

When encoding agent state as a fixed-size vector for neural network input, ad-hoc feature ordering creates problems:
- Different pipeline components expect features in different orders
- Adding new features breaks existing model checkpoints
- Features of different scales and types are interleaved without structure
- No clear way to mask or zero-out specific feature groups for ablations

## Solution

Define a canonical feature vector layout with named segments, each containing semantically related features. Use class-level constants to document segment boundaries and provide slice access.

Typical segments for FLUME agent state:
- **Identity** (agent type, spawn context) — categorical encoded
- **Position** (spatial location, normalized to environment bounds) — continuous
- **Resources** (energy, health, held items, normalized to [0,1]) — continuous
- **Goals** (current goal embedding, priority weight) — continuous
- **History** (recent action embedding, step count) — continuous + ordinal
- **Context** (local environment features visible to agent) — continuous

## Code Example

```python
from dataclasses import dataclass
import numpy as np
from typing import ClassVar

@dataclass
class AgentStateLayout:
    """Canonical feature vector layout. Total: 64 features."""

    IDENTITY_SLICE: ClassVar[slice] = slice(0, 4)    # agent type, context
    POSITION_SLICE: ClassVar[slice] = slice(4, 10)   # x, y, z, orientation (3D)
    RESOURCES_SLICE: ClassVar[slice] = slice(10, 18) # energy, health, 6 resource types
    GOALS_SLICE: ClassVar[slice] = slice(18, 34)     # 16D goal embedding
    HISTORY_SLICE: ClassVar[slice] = slice(34, 50)   # 16D recent-action embedding
    CONTEXT_SLICE: ClassVar[slice] = slice(50, 64)   # local environment features

    TOTAL_DIM: ClassVar[int] = 64
    VERSION: ClassVar[int] = 1  # increment when layout changes

    @staticmethod
    def from_agent(agent) -> np.ndarray:
        vec = np.zeros(AgentStateLayout.TOTAL_DIM, dtype=np.float32)
        vec[AgentStateLayout.IDENTITY_SLICE] = agent.identity_features()
        vec[AgentStateLayout.POSITION_SLICE] = agent.position_features()
        vec[AgentStateLayout.RESOURCES_SLICE] = agent.resource_features()
        vec[AgentStateLayout.GOALS_SLICE] = agent.goal_features()
        vec[AgentStateLayout.HISTORY_SLICE] = agent.history_features()
        vec[AgentStateLayout.CONTEXT_SLICE] = agent.context_features()
        return vec

    @staticmethod
    def ablate(vec: np.ndarray, segment: str) -> np.ndarray:
        """Zero out a named segment for ablation studies."""
        seg = getattr(AgentStateLayout, f"{segment.upper()}_SLICE")
        result = vec.copy()
        result[seg] = 0.0
        return result
```

## When to Use

- Multiple pipeline components consume the same agent state vectors
- You need ablation studies (which feature groups matter?)
- Models are checkpointed and must stay compatible across minor changes
- New contributors need to understand the feature vector structure

**Evolution protocol**: When adding features, append new segments at the end and increment `VERSION`. Never reorder existing features without a migration plan and version bump.

## Related

- [[structured-experience-vector-layout]]
- [[vae-checkpoint-format-with-config]]
- [[agent-journey-tracking]] — the 12D journey tracking system consumes structured agent state vectors as position data
- [[neural-network-architecture]] — canonical feature vector layouts ensure compatibility across model architectures and checkpoints
