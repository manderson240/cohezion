import logging

import numpy as np
import torch
import torch.nn.functional as F

logger = logging.getLogger(__name__)


class MorphicField:
    """
    Global Morphic Resonance Field (Gateway 26).

    Stores successful thought vectors ("Imprints") and allows new agents
    to "resonate" with past success, guiding them toward effective
    regions of the latent space.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._minit()
        return cls._instance

    def _minit(self):
        """Initialize the field."""
        # Storage for imprinted vectors [N, dim]
        self.memory_bank: list[torch.Tensor] = []
        self.scores: list[float] = []
        self.dim = 768  # Default for now, can adapt

    def imprint(self, vector: torch.Tensor | np.ndarray, score: float):
        """
        Imprint a successful thought into the morphic field.
        Only high-quality thoughts (score > 0.8) are accepted.
        """
        if float(score) < 0.8:
            return

        if isinstance(vector, np.ndarray):
            vector = torch.from_numpy(vector).float()

        if vector.dim() == 1:
            vector = vector.unsqueeze(0)

        # Normalize for cosine similarity
        vector = F.normalize(vector, p=2, dim=1)

        # Add to bank
        self.memory_bank.append(vector.detach().cpu())
        self.scores.append(score)

        # Keep bank size manageable (e.g., max 1000 top thoughts)
        if len(self.memory_bank) > 1000:
            self._prune()

        logger.info(
            f"🧬 Morphic Field Imprinted (Score: {score:.2f}, Bank Size: {len(self.memory_bank)})"
        )

    def resonate(
        self, vector: torch.Tensor | np.ndarray
    ) -> tuple[float, torch.Tensor | None]:
        """
        Check for resonance with existing patterns.
        Returns (max_resonance_score, guiding_vector).
        """
        if not self.memory_bank:
            return 0.0, None

        if isinstance(vector, np.ndarray):
            vector = torch.from_numpy(vector).float()

        if vector.dim() == 1:
            vector = vector.unsqueeze(0)

        vector = F.normalize(vector, p=2, dim=1)

        # Stack memory bank
        bank = torch.cat(self.memory_bank, dim=0)

        # Calculate similarity [1, N]
        sims = torch.mm(vector, bank.t())

        max_sim, idx = torch.max(sims, dim=1)

        return max_sim.item(), bank[idx].squeeze(0)

    def _prune(self):
        """Keep only the highest scoring memories."""
        # Simple pruning: sort by score and keep top 800
        combined = sorted(
            zip(self.scores, self.memory_bank, strict=False),
            key=lambda x: x[0],
            reverse=True,
        )
        self.scores = [x[0] for x in combined[:800]]
        self.memory_bank = [x[1] for x in combined[:800]]


def get_morphic_field() -> MorphicField:
    return MorphicField()
