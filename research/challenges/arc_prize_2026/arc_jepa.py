import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np

class ARCGameEncoder(nn.Module):
    """CNN-based encoder for 64x64 ARC grids."""
    def __init__(self, latent_dim=256):
        super().__init__()
        self.conv = nn.Sequential(
            nn.Conv2d(1, 32, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2), # 32x32
            nn.Conv2d(32, 64, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2), # 16x16
            nn.Conv2d(64, 128, kernel_size=3, padding=1),
            nn.ReLU(),
            nn.MaxPool2d(2), # 8x8
            nn.Flatten(),
            nn.Linear(128 * 8 * 8, 512),
            nn.ReLU(),
            nn.Linear(512, latent_dim)
        )

    def forward(self, x):
        """
        Args:
            x: Input grid tensor of shape (batch, 1, 64, 64)
        Returns:
            Latent vector of shape (batch, latent_dim)
        """
        # Normalize input 0-15 to 0-1
        x = x.float() / 15.0
        return self.conv(x)

class ARCPredictor(nn.Module):
    """JEPA-style predictor for ARC-AGI-3."""
    def __init__(self, latent_dim=256):
        super().__init__()
        self.action_emb = nn.Embedding(7, 32)
        self.x_emb = nn.Embedding(64, 32)
        self.y_emb = nn.Embedding(64, 32)
        
        self.net = nn.Sequential(
            nn.Linear(latent_dim + 32 + 32 + 32, 512),
            nn.ReLU(),
            nn.Linear(512, 512),
            nn.ReLU(),
            nn.Linear(512, latent_dim)
        )

    def forward(self, z, action, x, y):
        """
        Args:
            z: Latent vector (batch, latent_dim)
            action: Action index (batch,)
            x: X coordinate (batch,)
            y: Y coordinate (batch,)
        """
        a_e = self.action_emb(action)
        x_e = self.x_emb(x)
        y_e = self.y_emb(y)
        feat = torch.cat([z, a_e, x_e, y_e], dim=-1)
        return self.net(feat)

class ARCWorldModel(nn.Module):
    """JEPA World Model for ARC Prize 2026."""
    def __init__(self, latent_dim=256):
        super().__init__()
        self.encoder = ARCGameEncoder(latent_dim)
        self.predictor = ARCPredictor(latent_dim)
        # Target encoder (EMA of encoder or separate for JEPA)
        self.target_encoder = ARCGameEncoder(latent_dim)
        self._update_target_encoder(tau=1.0) # Init with same weights

    def _update_target_encoder(self, tau=0.01):
        for param, target_param in zip(self.encoder.parameters(), self.target_encoder.parameters()):
            target_param.data.copy_(tau * param.data + (1.0 - tau) * target_param.data)

    def forward(self, grid_curr, action, x, y, grid_next=None):
        z_curr = self.encoder(grid_curr)
        z_pred = self.predictor(z_curr, action, x, y)
        
        if grid_next is not None:
            with torch.no_grad():
                z_target = self.target_encoder(grid_next)
            loss = F.mse_loss(z_pred, z_target)
            return z_pred, loss
        
        return z_pred, None

    def compute_surprise(self, z_pred, grid_actual):
        """Calculate actual surprise (prediction error) after taking an action."""
        with torch.no_grad():
            z_actual = self.target_encoder(grid_actual)
            return F.mse_loss(z_pred, z_actual).item()

    @torch.no_grad()
    def evaluate_actions(self, grid_curr, x_coord, y_coord):
        """
        Evaluate all 7 actions and return predicted latents.
        Used for counterfactual reasoning.
        """
        z_curr = self.encoder(grid_curr)
        results = []
        for a in range(7):
            action = torch.tensor([a]).to(grid_curr.device)
            x = torch.tensor([x_coord]).to(grid_curr.device)
            y = torch.tensor([y_coord]).to(grid_curr.device)
            z_pred = self.predictor(z_curr, action, x, y)
            results.append(z_pred)
        return torch.cat(results, dim=0) # (7, latent_dim)
