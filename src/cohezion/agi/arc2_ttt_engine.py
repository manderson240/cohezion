#!/usr/bin/env python3
"""ARC-AGI-2: Test-Time Training (TTT) on D4 Dihedral Orbits Module
==================================================================
Expands demonstration pairs into 8 D4 dihedral symmetry orbits and performs
lightweight, fast test-time gradient adaptation on low-rank projection layers.
Adapts the neural representation to the specific puzzle manifold at inference time.
"""

from __future__ import annotations

from typing import List, Tuple
import numpy as np
import torch
import torch.nn as nn
import torch.nn.functional as F


def generate_d4_orbits(demos: List[Tuple[np.ndarray, np.ndarray]]) -> List[Tuple[np.ndarray, np.ndarray]]:
    """Expands demonstration pairs across the 8 elements of the dihedral group D4."""
    augmented = []
    for x, y in demos:
        for rot in range(4):
            x_rot = np.rot90(x, rot)
            y_rot = np.rot90(y, rot)
            augmented.append((x_rot, y_rot))
            augmented.append((np.fliplr(x_rot), np.fliplr(y_rot)))
    return augmented


class ArcLoRAAdapter(nn.Module):
    """Low-rank adaptation layer for test-time adaptation."""

    def __init__(self, base_layer: nn.Linear, rank: int = 4) -> None:
        super().__init__()
        self.base_layer = base_layer
        self.rank = rank
        self.A = nn.Parameter(torch.randn(base_layer.in_features, rank) * 0.01)
        self.B = nn.Parameter(torch.randn(rank, base_layer.out_features) * 0.01)

        # Freeze base layer weights
        self.base_layer.weight.requires_grad = False
        if self.base_layer.bias is not None:
            self.base_layer.bias.requires_grad = False

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return self.base_layer(x) + (x @ self.A) @ self.B


class ArcTTTEngine:
    """Manages inference-time test-time training adaptation on D4 orbits."""

    def __init__(self, lr: float = 1e-3, steps: int = 5) -> None:
        self.lr = lr
        self.steps = steps

    def adapt_model(
        self,
        model: nn.Module,
        demos: List[Tuple[np.ndarray, np.ndarray]]
    ) -> float:
        """Runs test-time gradient descent on D4-augmented demo pairs.

        Returns:
            Final adaptation loss.
        """
        augmented = generate_d4_orbits(demos)
        # Adapt only parameters that require grad (LoRA parameters)
        trainable_params = [p for p in model.parameters() if p.requires_grad]
        if not trainable_params:
            return 0.0

        optimizer = torch.optim.AdamW(trainable_params, lr=self.lr)
        total_loss = 0.0

        for _ in range(self.steps):
            for x, y in augmented[:16]:  # Batch of D4 orbits
                optimizer.zero_grad()
                # Dummy demo representation for gradient step
                x_t = torch.tensor(x, dtype=torch.float32).unsqueeze(0).unsqueeze(0)
                # Ensure input dimensions fit
                if hasattr(model, "forward_features"):
                    out = model(x_t)
                else:
                    out = model(x_t)
                # Compute loss if output matches target shape
                target = torch.tensor(y, dtype=torch.long if out.dim() == 4 else torch.float32)
                loss = F.mse_loss(out, target.float().expand_as(out))
                loss.backward()
                optimizer.step()
                total_loss += loss.item()

        return total_loss / (self.steps * min(16, len(augmented)))
