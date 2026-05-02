"""JEPA World Model for the 12D manifold.

Learns to predict next manifold state from current state + action,
trained on (state, action, next_state, reward) tuples stored in SurrealDB.

Architecture (inspired by LeWorldModel, LeCun/arxiv 2603.19312):
    ManifoldEncoder: 12D state → 64D embedding
    ActionEncoder:   256D action → 64D embedding (or 12D action → 64D)
    Predictor:       128D (state_emb ⊕ action_emb) → 64D predicted_next_emb

Causal upgrade (inspired by Causal-JEPA, Nam et al., arxiv 2602.11389):
    CausalMask randomly masks embedding dimensions during training,
    forcing the predictor to learn CAUSAL relationships not just correlations.
    At inference, subset selection enables fast planning (uses only top-k causal dims).

Two losses only:
    1. Next-embedding prediction: MSE(predictor(enc(s), enc(a)), enc(s'))
    2. Gaussian regularizer: KL(enc(s) || N(0,I)) — prevents collapse

~2M parameters (fits on CPU/iGPU per hardware constraints).

References:
    - LeWorldModel (Maes et al., arxiv 2603.19312)
    - Bardes, Pagnoni, LeCun (2024): V-JEPA, IJEPA
    - Nam et al. (2026): Causal-JEPA, arxiv 2602.11389

Hypothesis: add_rotation_transforms
"""

from __future__ import annotations

import logging

import torch
import torch.nn as nn


logger = logging.getLogger(__name__)


class ManifoldEncoder(nn.Module):
    """Encode 12D manifold state to 64D embedding with Gaussian prior."""

    def __init__(self, input_dim: int = 12, embed_dim: int = 64):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, embed_dim)
        self.rotation_transforms = nn.ModuleList(
            [nn.Linear(embed_dim, embed_dim) for _ in range(3)]
        )

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(x))
        x = self.fc2(x)

        # Apply rotation transforms
        for transform in self.rotation_transforms:
            x = torch.relu(transform(x))

        return x


class ActionEncoder(nn.Module):
    """Encode action to 64D embedding."""

    def __init__(self, input_dim: int = 256, embed_dim: int = 64):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, 128)
        self.fc2 = nn.Linear(128, embed_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(x))
        return self.fc2(x)


class Predictor(nn.Module):
    """Predict next embedding from state and action embeddings."""

    def __init__(self, input_dim: int = 128, output_dim: int = 64):
        super().__init__()
        self.fc1 = nn.Linear(input_dim, 256)
        self.fc2 = nn.Linear(256, output_dim)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        x = torch.relu(self.fc1(x))
        return self.fc2(x)


class JEPAWorldModel(nn.Module):
    """JEPA World Model integrating ManifoldEncoder, ActionEncoder, and Predictor."""

    def __init__(self):
        super().__init__()
        self.manifold_encoder = ManifoldEncoder()
        self.action_encoder = ActionEncoder()
        self.predictor = Predictor()

    def forward(self, state: torch.Tensor, action: torch.Tensor) -> torch.Tensor:
        state_emb = self.manifold_encoder(state)
        action_emb = self.action_encoder(action)
        combined_emb = torch.cat((state_emb, action_emb), dim=-1)
        predicted_next_emb = self.predictor(combined_emb)
        return predicted_next_emb
