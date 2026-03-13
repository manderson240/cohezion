---
title: "Structured Experience Vector Layout"
date: "2026-02-23"
tags: [pattern]
aspect: thinker
neural:
  activation: 0.67
  stage: growing
  synapse_in: 12
  synapse_out: 7
---

## Problem

Reinforcement learning experience replay requires storing (state, action, reward, next_state, done) tuples. When the agent state is a high-dimensional structured vector, naive concatenation creates experience vectors that are hard to inspect, debug, and consume correctly in training.

## Solution

Define an experience vector as a structured concatenation with explicit named offsets. Provide accessors that slice the experience vector back into its components without requiring callers to remember offsets.

An experience record contains:
- **current_state**: agent state at time t (D_state features)
- **action_embedding**: embedding of the action taken (D_action features)
- **reward**: scalar reward, normalized (1 feature)
- **next_state**: agent state at time t+1 (D_state features)
- **done**: episode termination flag (1 feature)
- **metadata**: step count, episode ID, agent ID (M features)

## Code Example

```python
import numpy as np
from typing import ClassVar, NamedTuple

class ExperienceVector:
    """Structured experience vector for FLUME agent training.

    Layout: [current_state | action_embedding | reward | next_state | done | metadata]
    """
    STATE_DIM: ClassVar[int] = 64
    ACTION_DIM: ClassVar[int] = 16
    META_DIM: ClassVar[int] = 4
    TOTAL_DIM: ClassVar[int] = 64 + 16 + 1 + 64 + 1 + 4  # = 150

    # Segment slices
    CURRENT_STATE: ClassVar[slice] = slice(0, 64)
    ACTION: ClassVar[slice] = slice(64, 80)
    REWARD: ClassVar[int] = 80
    NEXT_STATE: ClassVar[slice] = slice(81, 145)
    DONE: ClassVar[int] = 145
    META: ClassVar[slice] = slice(146, 150)

    def __init__(self, current_state, action_embedding, reward, next_state, done, metadata=None):
        self._vec = np.zeros(self.TOTAL_DIM, dtype=np.float32)
        self._vec[self.CURRENT_STATE] = current_state
        self._vec[self.ACTION] = action_embedding
        self._vec[self.REWARD] = reward
        self._vec[self.NEXT_STATE] = next_state
        self._vec[self.DONE] = float(done)
        if metadata is not None:
            self._vec[self.META] = metadata

    @classmethod
    def from_vec(cls, vec: np.ndarray) -> 'ExperienceVector':
        obj = cls.__new__(cls)
        obj._vec = vec
        return obj

    def get_current_state(self) -> np.ndarray:
        return self._vec[self.CURRENT_STATE]

    def get_action(self) -> np.ndarray:
        return self._vec[self.ACTION]

    def get_reward(self) -> float:
        return float(self._vec[self.REWARD])

    def get_next_state(self) -> np.ndarray:
        return self._vec[self.NEXT_STATE]

    def is_done(self) -> bool:
        return bool(self._vec[self.DONE])

    def to_numpy(self) -> np.ndarray:
        return self._vec
```

## When to Use

- Building replay buffers for agent training
- Logging experiences for offline analysis or FLUME training data collection
- Any pipeline where (s, a, r, s', done) needs to be stored and retrieved efficiently as numpy arrays

**Storage**: Store as float32 numpy arrays in a pre-allocated ring buffer. For 150-dimensional experiences, 1M experiences = ~600 MB. The flat numpy format allows efficient batch sampling with `buffer[indices]`.

## Related

- [[structured-feature-vector-layout-for-agent-state]]
- [[vae-checkpoint-format-with-config]]
- [[machine-learning]] — experience vectors serve as training data for reinforcement learning and VAE models
- [[agent-journey-tracking]] — journey tracking produces the state observations that become experience vector components
- [[experience-feedback-loop]] — structured experience vectors are the data format that closes the feedback loop from execution to training
- [[2026-02-24-flume-vae-v2-training-results]] — FLUME VAE v2 training consumes these structured experience vectors as input data
- [[neural-network-architecture]] — the vector layout (state/action/reward/next_state/done) follows standard neural network RL training data conventions
