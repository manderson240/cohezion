---
title: "Momentum-Based Trajectory Prediction with Counterfactuals"
date: "2026-02-24"
tags: [pattern]
aspect: thinker
neural:
  activation: 0.68
  stage: growing
  synapse_in: 7
  synapse_out: 7
---

## Problem

Predicting where an agent's trajectory will go next requires capturing directional momentum (where is it heading?) not just current position (where is it now?). A purely position-based predictor can't distinguish between an agent that just arrived at a state vs. one that has been approaching it for several steps with momentum.

Additionally, useful prediction isn't just "where will the agent go?" but "what would happen if the agent made a different decision?" — counterfactual branches.

## Solution

Maintain a **momentum vector** in latent space as a running weighted average of recent trajectory steps. Use this to predict the next position. Generate counterfactual branches by perturbing the momentum vector in orthogonal directions and propagating forward.

Components:
1. **Momentum estimation**: Exponential moving average of step vectors in latent space
2. **Next-step prediction**: `predicted_next = current + α * momentum`
3. **Counterfactual branches**: Perturb momentum with orthogonal noise vectors; each perturbation = one counterfactual branch
4. **Branch evaluation**: Use FLUME to score coherence/stability of each branch

## Code Example

```python
import torch
from torch import Tensor

class MomentumTrajectoryPredictor:
    def __init__(self, latent_dim: int, momentum_decay: float = 0.8, step_size: float = 0.1):
        self.latent_dim = latent_dim
        self.momentum_decay = momentum_decay
        self.step_size = step_size
        self.momentum = torch.zeros(latent_dim)
        self.prev_position = None

    def update(self, current_position: Tensor) -> None:
        """Update momentum from new position observation."""
        if self.prev_position is not None:
            step = current_position - self.prev_position
            self.momentum = self.momentum_decay * self.momentum + (1 - self.momentum_decay) * step
        self.prev_position = current_position.clone()

    def predict_next(self) -> Tensor:
        """Predict next position using current momentum."""
        return self.prev_position + self.step_size * self.momentum

    def counterfactual_branches(self, n_branches: int = 4, perturbation_scale: float = 0.3) -> list[Tensor]:
        """Generate counterfactual trajectory branches.

        Each branch is a predicted next position if momentum were perturbed
        in a different direction.
        """
        branches = []
        # Generate random orthogonal perturbations
        for _ in range(n_branches):
            noise = torch.randn_like(self.momentum)
            # Project noise perpendicular to current momentum
            if self.momentum.norm() > 0:
                proj = (noise @ self.momentum) / (self.momentum @ self.momentum)
                noise = noise - proj * self.momentum
            noise = noise / (noise.norm() + 1e-8) * perturbation_scale
            perturbed_momentum = self.momentum + noise
            branch_next = self.prev_position + self.step_size * perturbed_momentum
            branches.append(branch_next)
        return branches
```

## When to Use

- Trajectory monitoring where you want to predict where an agent will be in N steps
- Counterfactual analysis: "what if the agent had chosen differently at step T?"
- Early warning systems: detect when predicted trajectory is heading toward an anomalous region before it arrives
- Intervention planning: find the perturbation needed to redirect an agent toward a desired stability well

**Prerequisites**: Sufficient trajectory history to establish meaningful momentum (~5-10 steps minimum). Works best in a latent space where nearby points have similar semantics (i.e., requires FLUME or similar embedding).

## Related

- [[morphospace-stability-wells]]
- [[momentum-based-trajectory-prediction-with-counterfactual-branching]]

## Related Concepts

- [[agent-journey-tracking]] — the 12D journey tracking system whose trajectory data this pattern predicts
- [[anomaly-detection]] — early warning capability: predict whether momentum carries the agent toward an anomalous region before arrival

## Related Decisions

- [[2026-02-09-12d-graph-next-steps|Decision: 12D Graph — Compound Engineering Next Steps]] — decision that established 12D trajectory space as the target for this pattern
- [[2026-02-23-hash-based-journey-tracking-produces-meaningless-12d-trajectories|Decision: Hash-based journey tracking produces meaningless 12D trajectories]] — anti-pattern showing why momentum-based (not hash-based) tracking is required
- [[2026-02-24-anti-pattern-hash-based-journey-tracking-destroys-semantic-meaning|Anti-pattern: Hash-based journey tracking destroys semantic meaning]]
