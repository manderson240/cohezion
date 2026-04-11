"""
MPS (Matrix Product State) Weight Compressor (2026 SOTA).
Compresses large weight matrices (like Embeddings) into low-rank cores.
"""

import logging
import numpy as np
from typing import List, Tuple

logger = logging.getLogger(__name__)


class MPSCompressor:
    def __init__(self, bond_dim: int = 64):
        self.bond_dim = bond_dim

    def compress_matrix(self, matrix: np.ndarray, shape: Tuple[int, ...]) -> List[np.ndarray]:
        """
        Decomposes a matrix into a chain of MPS cores.
        matrix: The weight matrix to compress.
        shape: The target tensor shape (e.g., (8, 8, 8, 8) for a 64x64 matrix).
        """
        if matrix.size != np.prod(shape):
            raise ValueError(f"Matrix size {matrix.size} does not match tensor shape {shape}")

        tensor = matrix.reshape(shape)
        d = len(shape)
        cores = []

        curr_tensor = tensor
        left_dim = 1

        for i in range(d - 1):
            # Reshape to (left_dim * current_leg, remaining_legs)
            row_dim = left_dim * shape[i]
            curr_tensor = curr_tensor.reshape(row_dim, -1)

            # SVD
            u, s, vh = np.linalg.svd(curr_tensor, full_matrices=False)

            # Truncate bond dimension
            rank = min(self.bond_dim, len(s))
            u = u[:, :rank]
            s = s[:rank]
            vh = vh[:rank, :]

            # Create core
            core = u.reshape(left_dim, shape[i], rank)
            cores.append(core)

            # Prepare for next iteration
            curr_tensor = np.diag(s) @ vh
            left_dim = rank

        # Last core
        cores.append(curr_tensor.reshape(left_dim, shape[-1], 1))

        total_params = sum(c.size for c in cores)
        orig_params = matrix.size
        logger.info(
            "MPS Compression complete. Ratio: %.2fx (%d -> %d params)",
            orig_params / total_params,
            orig_params,
            total_params,
        )

        return cores

    def reconstruct_matrix(
        self, cores: List[np.ndarray], original_shape: Tuple[int, int]
    ) -> np.ndarray:
        """Reconstructs the original matrix from MPS cores."""
        res = cores[0]
        for i in range(1, len(cores)):
            # Contract core i with result on the bond dimension
            # res: (1, d1, r1) -> (r1, d2, r2)
            res = np.tensordot(res, cores[i], axes=(-1, 0))

        # res: (1, d1, d2, ..., dn, 1)
        return res.reshape(original_shape)
