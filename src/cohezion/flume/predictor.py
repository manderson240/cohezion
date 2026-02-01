import torch
import torch.nn as nn


class TrajectoryPredictor(nn.Module):
    """
    Models the 'velocity' and evolution of reasoning in latent space.
    Allows predicting where a thought is going or exploring counterfactuals.
    """

    def __init__(self, z_dim: int = 256, hidden_dim: int = 512):
        super().__init__()
        self.z_dim = z_dim

        # Predicts Δz (velocity) based on current z
        self.navigator = nn.Sequential(
            nn.Linear(z_dim, hidden_dim),
            nn.ReLU(),
            nn.LayerNorm(hidden_dim),
            nn.Linear(hidden_dim, z_dim),
        )

    def forward(self, z: torch.Tensor) -> torch.Tensor:
        """Compute the next state in the trajectory."""
        delta = self.navigator(z)
        return z + delta

    def predict_sequence(self, z: torch.Tensor, steps: int = 5) -> list[torch.Tensor]:
        """Predict a sequence of future thought vectors."""
        trajectory = [z]
        current_z = z
        for _ in range(steps):
            current_z = self.forward(current_z)
            trajectory.append(current_z)
        return trajectory

    def predict_with_physics(
        self,
        z: torch.Tensor,
        steps: int = 10,
        physics_weight: float = 0.3,
        momentum: float = 0.9,
    ) -> list[torch.Tensor]:
        """
        Predict trajectory using 'latent physics'.
        Simulates momentum and force-like updates.
        """
        trajectory = [z]
        current_z = z
        velocity = torch.zeros_like(z)

        for _ in range(steps):
            # 1. 'Force' from the navigator (intentional direction)
            force = self.navigator(current_z)

            # 2. Update velocity with momentum
            velocity = momentum * velocity + (1 - momentum) * force

            # 3. Apply physics weight (influence of current momentum)
            current_z = current_z + force + physics_weight * velocity
            trajectory.append(current_z)

        return trajectory

    def imagine_branches(
        self,
        z: torch.Tensor,
        perturbations: int = 3,
        steps: int = 5,
        noise_scale: float = 0.1,
    ) -> list[list[torch.Tensor]]:
        """Explore alternative 'counterfactual' thought paths."""
        branches = []
        for _ in range(perturbations):
            # Start with a slight perturbation
            noise = torch.randn_like(z) * noise_scale
            branch = self.predict_sequence(z + noise, steps=steps)
            branches.append(branch)
        return branches
