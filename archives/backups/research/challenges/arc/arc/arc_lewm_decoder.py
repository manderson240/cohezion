"""ARC-specific CNN decoder for LeWM JEPA.

Decodes latent embeddings back to variable-sized ARC grids (0-9 colors).
Reverse of the encoder architecture with transposed convolutions.
"""

from __future__ import annotations

import logging

import torch
import torch.nn as nn
import torch.nn.functional as F


logger = logging.getLogger(__name__)


class ARCGridDecoder(nn.Module):
    """CNN decoder for reconstructing ARC grids from latent embeddings.

    Architecture (reverse of encoder):
    1. Project embedding to latent features
    2. Reshape to spatial features
    3. Upsampling blocks: 256 -> 128 -> 64 -> 32
    4. Final conv: 32 -> NUM_COLORS (10)
    5. Resize to target size if specified

    Can output variable sizes based on target dimensions.
    """

    NUM_COLORS: int = 10

    def __init__(
        self,
        embed_dim: int = 64,
        latent_dim: int = 256,
        num_res_blocks: int = 2,
        dropout: float = 0.1,
    ):
        """Initialize ARC decoder.

        Args:
            embed_dim: Input embedding dimension (default 64)
            latent_dim: Intermediate latent dimension (default 256)
            num_res_blocks: Number of residual blocks per stage
            dropout: Dropout rate
        """
        super().__init__()
        self.embed_dim = embed_dim
        self.latent_dim = latent_dim

        # Project embedding to spatial features
        # Shape: (B, latent_dim) -> (B, 256 * 4 * 4)
        self.fc = nn.Sequential(
            nn.Linear(embed_dim, latent_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(latent_dim, 256 * 4 * 4),
            nn.GELU(),
        )

        # Stage 1: 256 -> 128 (upsample x2)
        self.stage1_res = nn.ModuleList(
            [ResidualBlockTranspose(256, dropout=dropout) for _ in range(num_res_blocks)]
        )
        self.stage1_up = nn.Sequential(
            nn.ConvTranspose2d(256, 128, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(128),
            nn.GELU(),
        )

        # Stage 2: 128 -> 64 (upsample x2)
        self.stage2_res = nn.ModuleList(
            [ResidualBlockTranspose(128, dropout=dropout) for _ in range(num_res_blocks)]
        )
        self.stage2_up = nn.Sequential(
            nn.ConvTranspose2d(128, 64, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(64),
            nn.GELU(),
        )

        # Stage 3: 64 -> 32 (upsample x2)
        self.stage3_res = nn.ModuleList(
            [ResidualBlockTranspose(64, dropout=dropout) for _ in range(num_res_blocks)]
        )
        self.stage3_up = nn.Sequential(
            nn.ConvTranspose2d(64, 32, kernel_size=4, stride=2, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.GELU(),
        )

        # Final output conv
        self.output_conv = nn.Sequential(
            nn.Conv2d(32, 32, kernel_size=3, padding=1, bias=False),
            nn.BatchNorm2d(32),
            nn.GELU(),
            nn.Conv2d(32, self.NUM_COLORS, kernel_size=1),
        )

        self._init_weights()

    def _init_weights(self) -> None:
        """Initialize weights for stable training."""
        for m in self.modules():
            if isinstance(m, (nn.Conv2d, nn.ConvTranspose2d)):
                nn.init.kaiming_normal_(m.weight, mode="fan_out", nonlinearity="relu")
                if m.bias is not None:
                    nn.init.zeros_(m.bias)
            elif isinstance(m, nn.BatchNorm2d):
                nn.init.constant_(m.weight, 1)
                nn.init.constant_(m.bias, 0)
            elif isinstance(m, nn.Linear):
                nn.init.normal_(m.weight, 0, 0.01)
                if m.bias is not None:
                    nn.init.constant_(m.bias, 0)

    def forward(
        self,
        z: torch.Tensor,
        target_size: tuple[int, int] | None = None,
    ) -> torch.Tensor:
        """Decode latent embedding to ARC grid.

        Args:
            z: Latent embedding of shape (B, embed_dim) or (embed_dim,)
            target_size: Optional (H, W) to resize output to. If None,
                        output will be 32x32 (4 * 2^3 from initial 4x4)

        Returns:
            Grid tensor of shape (B, NUM_COLORS, H, W) with logits
            where NUM_COLORS = 10
        """
        # Handle single sample
        if z.dim() == 1:
            z = z.unsqueeze(0)

        # Project and reshape to spatial
        x = self.fc(z)
        x = x.view(-1, 256, 4, 4)

        # Stage 1 (256 -> 128, 4x4 -> 8x8)
        for block in self.stage1_res:
            x = block(x)
        x = self.stage1_up(x)

        # Stage 2 (128 -> 64, 8x8 -> 16x16)
        for block in self.stage2_res:
            x = block(x)
        x = self.stage2_up(x)

        # Stage 3 (64 -> 32, 16x16 -> 32x32)
        for block in self.stage3_res:
            x = block(x)
        x = self.stage3_up(x)

        # Output conv
        x = self.output_conv(x)

        # Resize to target size if specified
        if target_size is not None:
            target_h, target_w = target_size
            x = F.interpolate(
                x,
                size=(target_h, target_w),
                mode="bilinear",
                align_corners=False,
            )

        return x

    def decode_to_grid(
        self,
        z: torch.Tensor,
        target_size: tuple[int, int] | None = None,
    ) -> list[list[int]]:
        """Decode latent embedding to ARC grid (list format).

        Args:
            z: Latent embedding
            target_size: Optional (H, W) for output

        Returns:
            2D list of integers (0-9) representing the grid
        """
        with torch.no_grad():
            logits = self.forward(z, target_size)
            colors = logits.argmax(dim=1).squeeze(0).cpu().numpy()
            return colors.tolist()

    @property
    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())


class ResidualBlockTranspose(nn.Module):
    """Residual block for transposed convolutions."""

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


class ARCWorldModel(nn.Module):
    """Complete ARC LeWM world model.

    Combines encoder, action encoder, predictor, causal mask, and decoder
    for end-to-end ARC grid transformation learning.
    """

    def __init__(
        self,
        embed_dim: int = 64,
        action_dim: int = 64,
        latent_dim: int = 256,
        num_res_blocks: int = 2,
        dropout: float = 0.1,
        causal_mask_ratio: float = 0.3,
    ):
        """Initialize complete ARC world model.

        Args:
            embed_dim: Embedding dimension
            action_dim: Action dimension
            latent_dim: Latent dimension
            num_res_blocks: Number of residual blocks
            dropout: Dropout rate
            causal_mask_ratio: Causal mask ratio for training
        """
        super().__init__()
        self.embed_dim = embed_dim
        self.action_dim = action_dim

        self.encoder = ARCGridEncoder(
            embed_dim=embed_dim,
            latent_dim=latent_dim,
            num_res_blocks=num_res_blocks,
            dropout=dropout,
        )

        self.action_encoder = ARCActionEncoder(
            action_dim=action_dim,
            embed_dim=embed_dim,
            dropout=dropout,
        )

        self.predictor = ARCPredictor(
            embed_dim=embed_dim,
            dropout=dropout,
        )

        self.causal_mask = ARCCausalMask(
            embed_dim=embed_dim,
            mask_ratio=causal_mask_ratio,
        )

        self.decoder = ARCGridDecoder(
            embed_dim=embed_dim,
            latent_dim=latent_dim,
            num_res_blocks=num_res_blocks,
            dropout=dropout,
        )

    def forward(
        self,
        grid: torch.Tensor,
        action: torch.Tensor,
    ) -> dict[str, torch.Tensor]:
        """Forward pass through full model.

        Args:
            grid: Input grid (B, NUM_COLORS, H, W)
            action: Action tensor (B, action_dim)

        Returns:
            Dict with embeddings and predictions
        """
        # Encode
        z, mu, logvar = self.encoder(grid)
        z_masked = self.causal_mask(z, training=self.training)

        # Encode action
        action_emb = self.action_encoder(action)

        # Predict next
        z_pred = self.predictor(z_masked, action_emb)

        # Decode
        grid_pred = self.decoder(z_pred)

        return {
            "z": z,
            "mu": mu,
            "logvar": logvar,
            "z_masked": z_masked,
            "action_emb": action_emb,
            "z_pred": z_pred,
            "grid_pred": grid_pred,
        }

    def encode(self, grid: torch.Tensor) -> torch.Tensor:
        """Encode grid to embedding."""
        z, _, _ = self.encoder(grid)
        return z

    def decode(self, z: torch.Tensor, target_size: tuple[int, int] | None = None) -> torch.Tensor:
        """Decode embedding to grid."""
        return self.decoder(z, target_size)

    def predict(
        self,
        grid: torch.Tensor,
        action: torch.Tensor,
    ) -> torch.Tensor:
        """Predict next grid from current grid and action.

        Args:
            grid: Current grid
            action: Transformation action

        Returns:
            Predicted next grid
        """
        self.eval()
        with torch.no_grad():
            outputs = self.forward(grid, action)
        return outputs["grid_pred"]

    def transform_grid(
        self,
        grid: list[list[int]],
        action: torch.Tensor | None = None,
    ) -> list[list[int]]:
        """Transform an ARC grid to a new grid.

        Args:
            grid: Input ARC grid (2D list)
            action: Optional action tensor. If None, uses auto-encoded action.

        Returns:
            Transformed grid (2D list)
        """
        from .arc_dataset import ARCGridTokenizer

        tokenizer = ARCGridTokenizer()
        grid_tensor = tokenizer.grid_to_tensor(grid).unsqueeze(0)

        if action is None:
            # Auto-encode to learn identity transformation
            z = self.encode(grid_tensor)
            output_grid = self.decode_to_grid(z, tokenizer.get_grid_size(grid))
        else:
            if action.dim() == 1:
                action = action.unsqueeze(0)
            pred_grid = self.predict(grid_tensor, action)
            colors = pred_grid.argmax(dim=1).squeeze().cpu().numpy()
            output_grid = colors.tolist()

        return output_grid

    def decode_to_grid(
        self,
        z: torch.Tensor,
        target_size: tuple[int, int] | None = None,
    ) -> list[list[int]]:
        """Decode embedding to grid list."""
        grid_tensor = self.decoder(z, target_size)
        colors = grid_tensor.argmax(dim=1).squeeze().cpu().numpy()
        if colors.ndim == 0:
            return [[int(colors)]]
        return colors.tolist()

    @property
    def n_parameters(self) -> int:
        return sum(p.numel() for p in self.parameters())


# Import here to avoid circular dependency
from .arc_lewm_encoder import ARCActionEncoder, ARCCausalMask, ARCPredictor


__all__ = [
    "ARCGridDecoder",
    "ARCWorldModel",
    "ResidualBlockTranspose",
]
