"""
BirdCLEF 2026 Baseline Model with Perch v2 Backbone.
Implements 1536-D embedding extraction + MLP Classification Head.
"""

import logging

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim

from cohezion.models.perch_v2_adapter import PerchV2Adapter


logger = logging.getLogger(__name__)


class BirdClassificationHead(nn.Module):
    """MLP Head for bird species classification."""

    def __init__(self, input_dim: int = 1536, num_classes: int = 234):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 512),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(512, 256),
            nn.ReLU(),
            nn.Linear(256, num_classes),
        )

    def forward(self, x):
        return self.network(x)


class BirdCLEFBaseline:
    """Baseline model using Google Perch v2 + Pytorch MLP Head."""

    def __init__(self, device: str = "cpu"):
        self.device = torch.device(device)
        self.backbone = PerchV2Adapter()
        self.head = BirdClassificationHead().to(self.device)
        self.species_columns = []
        self.optimizer = optim.Adam(self.head.parameters(), lr=1e-3)
        self.criterion = nn.BCEWithLogitsLoss()

    def set_species_columns(self, sample_submission_path: str):
        """Load target species columns from sample submission."""
        df = pd.read_csv(sample_submission_path)
        self.species_columns = [col for col in df.columns if col != "row_id"]
        logger.info(f"Initialized {len(self.species_columns)} species columns.")

    def train_step(self, audio_data: np.ndarray, labels: np.ndarray) -> float:
        """Execute a single training step on local GPU/NPU."""
        self.head.train()
        self.optimizer.zero_grad()

        # 1. Extract Embeddings (Backbone is frozen)
        embeddings = self.backbone.extract_embeddings(audio_data)
        embeddings_tensor = torch.from_numpy(embeddings).float().to(self.device)

        # 2. Forward Pass
        logits = self.head(embeddings_tensor)

        # 3. Compute Loss
        labels_tensor = torch.from_numpy(labels).float().to(self.device)
        loss = self.criterion(logits, labels_tensor)

        # 4. Backward Pass
        loss.backward()
        self.optimizer.step()

        return loss.item()

    def predict(self, audio_data: np.ndarray) -> np.ndarray:
        """Generate species probabilities."""
        self.head.eval()
        with torch.no_grad():
            embeddings = self.backbone.extract_embeddings(audio_data)
            embeddings_tensor = torch.from_numpy(embeddings).float().to(self.device)
            logits = self.head(embeddings_tensor)
            probs = torch.sigmoid(logits)
        return probs.cpu().numpy()

    def format_submission(self, probs: np.ndarray, filename: str, offsets: list[int]) -> pd.DataFrame:
        """Convert probabilities to Kaggle multi-column format."""
        rows = []
        for i, window_prob in enumerate(probs):
            row_id = f"{filename}_{offsets[i]}"
            row = {"row_id": row_id}
            row.update({species: prob for species, prob in zip(self.species_columns, window_prob)})
            rows.append(row)
        return pd.DataFrame(rows)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    baseline = BirdCLEFBaseline()
    print("BirdCLEF Baseline with Perch v2 Backbone Initialized.")
