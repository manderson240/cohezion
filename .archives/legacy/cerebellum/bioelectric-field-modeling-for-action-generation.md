---
title: "Bioelectric Field Modeling for Action Generation"
date: "2026-02-24"
tags: [pattern]
aspect: thinker
neural:
  activation: 0.71
  stage: growing
  synapse_in: 6
  synapse_out: 6
---

## Problem

Agent action generation needs to encode competing drives, motivations, and contextual attractors in a way that produces smooth, coherent behavior rather than discrete mode-switches. Standard softmax over action logits treats actions as independent options and doesn't capture spatial relationships between options or the concept of "momentum toward" a goal.

## Solution

Model the agent's action space as a bioelectric field where potential wells represent attractors (goals, drives, habitual behaviors). Action generation becomes gradient descent in this field — the agent moves toward the nearest potential well, modulated by the field topology.

Key components:
- **Potential wells**: Represent goals or motivational states as regions of low potential energy in action space
- **Field topology**: The landscape of potentials across action space; shaped by current state, context, and history
- **Action gradient**: The direction of steepest descent in the field; agent follows this gradient
- **Inertia/momentum**: Previous gradient direction partially determines next step (continuity)

This produces actions that are:
- Smooth transitions between goals (no abrupt switches)
- Influenced by multiple simultaneous attractors (blending)
- History-dependent (momentum)

## Code Example

```python
class BioelectricField:
    """Action generation as gradient descent in a potential field."""

    def __init__(self, action_dim: int, n_wells: int = 8):
        self.action_dim = action_dim
        self.well_centers = nn.Parameter(torch.randn(n_wells, action_dim))
        self.well_depths = nn.Parameter(torch.ones(n_wells))
        self.momentum = None
        self.momentum_decay = 0.9

    def potential(self, position: Tensor) -> Tensor:
        """Compute potential energy at a position in action space."""
        dists = torch.cdist(position.unsqueeze(0), self.well_centers)
        return -(self.well_depths * torch.exp(-dists.squeeze(0))).sum()

    def gradient_step(self, current_action: Tensor, context: Tensor) -> Tensor:
        """Generate next action via gradient descent in field."""
        # Compute gradient of potential at current position
        pos = current_action.requires_grad_(True)
        potential = self.potential(pos)
        gradient = torch.autograd.grad(potential, pos)[0]

        # Apply momentum
        if self.momentum is None:
            self.momentum = gradient
        else:
            self.momentum = self.momentum_decay * self.momentum + gradient

        # Step toward potential minimum
        return current_action + 0.1 * self.momentum
```

## When to Use

- Agent needs to blend between multiple simultaneous goals
- Behavior continuity is important (no jarring mode switches)
- You want action generation to encode motivational dynamics, not just state-to-action mapping
- Interpretability matters: potential wells can be visualized and inspected

**Not appropriate for:** Discrete action spaces with many unrelated options, real-time systems where gradient computation is too expensive, or simple reactive agents where goal blending isn't needed.

**Note:** This pattern was explored as `bioelectric_field.py` and found theoretically interesting but removed as an orphan module. Worth revisiting when FLUME trajectory modeling is mature enough to define meaningful potential wells from latent space structure.

## Related

- [[2026-02-23-enforce-no-orphan-modules-policy]]
- [[2026-02-24-anti-pattern-disconnected-modules-without-consumers]] — this pattern is the vault preservation of an orphan module (bioelectric_field.py)
- [[morphospace-stability-wells]]
- [[neural-network-architecture]] — gradient descent in potential fields builds on neural network optimization fundamentals
- [[machine-learning]] — agent action generation as gradient-based optimization in a learned field
- [[levin-bioelectrics]] — Michael Levin's actual bioelectric research program that inspired this pattern; voltage gradients as morphogenetic code, gap junctions as COHESION channels
