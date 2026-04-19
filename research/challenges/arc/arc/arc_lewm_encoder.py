"""ARC-specific CNN encoder for LeWM JEPA.

Encodes variable-sized ARC grids (0-9 colors, up to 30x30) into
fixed-dimensional latent embeddings suitable for JEPA world model training.
"""

from __future__ import annotations

import logging
from typing import Callable

import torch
import torch.nn as nn
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class AdaptiveGridPool(nn.Module):
    """Adaptive pooling for variable-sized grids.

    Pools any input size down to a fixed output size.
    """

    def __init__(self, output_size: tuple[int, int] = (4, 4)):
        super().__init__()
        self.output_size = output_size

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        return F.adaptive_avg_pool2d(x, self.output_size)


class ResidualBlock(nn.Module):
    """Residual block with Conv2d, BN, GELU."""

    def __init__(
        self,
        channels: int,
        kernel_size: int = 3,
        dropout: float = 0.1,
    ):
        super().__init__()
        self.conv1 = nn.Conv2d(
            channels, channels, kernel_size, padding=kernel_size // 2, bias=False
        )
        self.bn1 = nn.BatchNorm2d(channels)
        self.conv2 = nn.Conv2d(
            channels, channels, kernel_size, padding=kernel_size // 2, bias=False
        )
        self.bn2 = nn.BatchNorm2d(channels)
        self.dropout = nn.Dropout2d(dropout)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        residual = x
        x = F.gelu(self.bn1(self.conv1(x)))
        x = self.dropout(x)
        x = self.bn2(self.conv2(x))
        return F.gelu(x + residual)


class ARCGridEncoder(nn.Module):
    """CNN encoder for ARC grids to latent embeddings.

    Architecture:
    1. Conv stem: (NUM_COLORS -> 32) with kernel 3
    2. Downsampling stages: 32 -> 64 -> 128 -> 256
    3. Global adaptive pooling to fixed size
    4. FC layers: pooled features -> latent embedding

    Handles variable input sizes via adaptive pooling.
    """

    NUM_COLORS: int = 10  # ARC uses colors 0-9

    def __init__(
        self,
        embed_dim: int = 64,
        latent_dim: int = 256,
        num_res_blocks: int = 2,
        dropout: float = 0.1,
    ):
        """Initialize ARC encoder.

        Args:
            embed_dim: Output embedding dimension (default 64)
            latent_dim: Intermediate latent dimension (default 256)
            num_res_blocks: Number of residual blocks per stage
            dropout: Dropout rate
        """
        super().__init__()
        self.embed_dim = embed_dim
        self.latent_dim = latent_dim

        # Input stem
        self.stem = nn.Sequential(
            nn.Conv2d(self.NUM_COLORS, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.GELU(),
        )

        # Stage 1: 32 -> 64 (stride 2)
        self.stage1_down = nn.Sequential(
            nn.Conv2d(32, 64, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.GELU(),
        )
        self.stage1_res = nn.ModuleList(
            [ResidualBlock(64, dropout=dropout) for _ in range(num_res_blocks)]
        )

        # Stage 2: 64 -> 128 (stride 2)
        self.stage2_down = nn.Sequential(
            nn.Conv2d(64, 128, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.GELU(),
        )
        self.stage2_res = nn.ModuleList(
            [ResidualBlock(128, dropout=dropout) for _ in range(num_res_blocks)]
        )

        # Stage 3: 128 -> 256 (stride 2)
        self.stage3_down = nn.Sequential(
            nn.Conv2d(128, 256, kernel_size=3, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(256),
            nn.GELU(),
        )
        self.stage3_res = nn.ModuleList(
            [ResidualBlock(256, dropout=dropout) for _ in range(num_res_blocks)]
        )

        # Adaptive pooling to fixed size (4x4 = 4096 features @ 256 channels)
        self.global_pool = AdaptiveGridPool(output_size=(4, 4))

        # Flatten and project to latent
        pooled_features = 256 * 4 * 4
        self.fc = nn.Sequential(
            nn.Linear(pooled_features, latent_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        )

        # Variational encoding heads
        self.mu_head = nn.Linear(latent_dim, embed_dim)
        self.logvar_head = nn.Linear(latent_dim, embed_dim)

        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize weights for stable training."""
        for m in self.modules():
            if isinstance(m, nn.Conv2d):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(
        self, x: torch.Tensor
    ) -> tuple[torch.Tensor, torch.Tensor, torch.Tensor]:
        """Encode ARC grid tensor to latent embedding.

        Args:
            x: Input tensor of shape (B, NUM_COLORS, H, W) or (NUM_COLORS, H, W)
               where NUM_COLORS = 10 (one-hot encoded colors)

        Returns:
            Tuple of (z, mu, logvar) where z is sampled via reparameterization,
            mu and logvar are learned distribution parameters.
        """
        # Handle single sample
        if x.dim() == 3:
            x = x.unsqueeze(0)

        # Stem
        x = self.stem(x)

        # Stage 1
        x = self.stage1_down(x)
        for block in self.stage1_res:
            x = block(x)

        # Stage 2
        x = self.stage2_down(x)
        for block in self.stage2_res:
            x = block(x)

        # Stage 3
        x = self.stage3_down(x)
        for block in self.stage3_res:
            x = block(x)

        # Global pooling (handles variable input sizes)
        x = self.global_pool(x)

        # Flatten and project
        x = x.flatten(1)
        h = self.fc(x)

        # Variational encoding
        mu = self.mu_head(h)
        logvar = self.logvar_head(h)

        # Reparameterization trick
        std = torch.exp(0.5 * logvar)
        eps = torch.randn_like(std)
        z = mu + std * eps

        return z, mu, logvar

    def encode_mu(self, x: torch.Tensor) -> torch.Tensor:
        """Deterministic encoding (use mu only, no sampling).

        Args:
            x: Input tensor

        Returns:
            Mu (deterministic embedding)
        """
        with torch.no_grad():
            _, mu, _ = self.forward(x)
        return mu

    @property
    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())


class ARCActionEncoder(nn.Module):
    """Encode ARC transformations (actions) to embedding space.

    For ARC, actions encode:
    - Size change ratios
    - Color distribution changes
    - Spatial transformation hints
    """

    def __init__(
        self,
        action_dim: int = 64,
        embed_dim: int = 64,
        hidden_dim: int = 128,
        dropout: float = 0.1,
    ):
        """Initialize action encoder.

        Args:
            action_dim: Input action dimension (default 64)
            embed_dim: Output embedding dimension (default 64)
            hidden_dim: Hidden layer dimension (default 128)
            dropout: Dropout rate
        """
        super().__init__()
        self.action_dim = action_dim
        self.embed_dim = embed_dim

        self.net = nn.Sequential(
            nn.Linear(action_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, embed_dim),
        )

        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(self, action: torch.Tensor) -> torch.Tensor:
        """Encode action to embedding.

        Args:
            action: Action tensor of shape (B, action_dim) or (action_dim,)

        Returns:
            Action embedding of shape (B, embed_dim) or (embed_dim,)
        """
        if action.dim() == 1:
            action = action.unsqueeze(0)
        return self.net(action)


class ARCPredictor(nn.Module):
    """Predict next-state embedding from (state_emb, action_emb).

    Similar to JEPAWorldModel predictor but adapted for ARC.
    """

    def __init__(
        self,
        embed_dim: int = 64,
        hidden_dim: int = 128,
        num_layers: int = 3,
        dropout: float = 0.1,
    ):
        """Initialize predictor.

        Args:
            embed_dim: Embedding dimension
            hidden_dim: Hidden layer dimension
            num_layers: Number of hidden layers
            dropout: Dropout rate
        """
        super().__init__()
        self.embed_dim = embed_dim

        layers = [
            nn.Linear(embed_dim * 2, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
        ]

        for _ in range(num_layers - 1):
            layers.extend([
                nn.Linear(hidden_dim, hidden_dim),
                nn.LayerNorm(hidden_dim),
                nn.GELU(),
                nn.Dropout(dropout),
            ])

        layers.append(nn.Linear(hidden_dim, embed_dim))

        self.net = nn.Sequential(*layers)

        self._init_weights()

    def _init_weights(self) -> None:
        for m in self.modules():
            if isinstance(m, nn.Linear):
                nn.init.xavier_uniform_(m.weight)
                if m.bias is not None:
                    nn.init.zeros_(m.bias)

    def forward(
        self, state_emb: torch.Tensor, action_emb: torch.Tensor
    ) -> torch.Tensor:
        """Predict next embedding.

        Args:
            state_emb: State embedding (B, embed_dim)
            action_emb: Action embedding (B, embed_dim)

        Returns:
            Predicted next embedding (B, embed_dim)
        """
        combined = torch.cat([state_emb, action_emb], dim=-1)
        return self.net(combined)


class ARCCausalMask(nn.Module):
    """Causal masking for ARC embeddings (Causal-JEPA inspired).

    During training, randomly masks a fraction of embedding dimensions.
    This forces the predictor to learn causal relationships.
    """

    def __init__(
        self,
        embed_dim: int = 64,
        mask_ratio: float = 0.3,
    ):
        """Initialize causal mask.

        Args:
            embed_dim: Embedding dimension
            mask_ratio: Fraction of dimensions to mask during training
        """
        super().__init__()
        self.embed_dim = embed_dim
        self.mask_ratio = mask_ratio
        self.importance = nn.Parameter(torch.ones(embed_dim))

    def forward(self, x: torch.Tensor, training: bool = True) -> torch.Tensor:
        """Apply causal masking.

        Args:
            x: Input embeddings
            training: Whether in training mode

        Returns:
            Masked embeddings
        """
        if training and self.mask_ratio > 0:
            mask = torch.bernoulli(
                torch.full((x.shape[-1],), 1.0 - self.mask_ratio, device=x.device)
            )
            scale = 1.0 / max(1.0 - self.mask_ratio, 0.1)
            return x * mask * scale

        # Inference: weight by learned importance
        importance_weights = torch.sigmoid(self.importance)
        return x * importance_weights

    def causal_importance_scores(self) -> torch.Tensor:
        """Return normalized importance scores."""
        with torch.no_grad():
            scores = torch.sigmoid(self.importance)
        return scores / (scores.sum() + 1e-8)

    def top_k_causal_dims(self, k: int | None = None) -> list[int]:
        """Return indices of top-k most important dimensions."""
        if k is None:
            k = max(1, self.embed_dim // 10)
        scores = self.causal_importance_scores().numpy()
        return list(scores.argsort()[-k:][::-1])


__all__ = [
    "ARCGridEncoder",
    "ARCActionEncoder",
    "ARCPredictor",
    "ARCCausalMask",
    "AdaptiveGridPool",
    "ResidualBlock",
]
