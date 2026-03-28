"""Helion autotuning configuration for MLA decode kernel.

Search space optimized for CDNA 4 (MI355X) architecture.
Defines tile sizes, precision modes, and fusion strategies.
"""

from typing import List, Tuple


class MLAAutotuneConfig:
    """Autotuning search space for MLA decode on MI355X."""

    # CDNA 4 MFMA-friendly configurations
    # Each config: (BLOCK_M, BLOCK_N, BLOCK_K, num_warps, num_stages)
    BLOCK_CONFIGS: List[Tuple[int, int, int, int, int]] = [
        # Small batch configs (M=16, 32)
        (16, 32, 64, 4, 2),
        (16, 64, 64, 4, 2),
        (32, 32, 64, 4, 2),
        (32, 64, 64, 4, 2),
        # Standard configs (M=64)
        (64, 32, 64, 4, 2),
        (64, 32, 64, 8, 2),
        (64, 64, 64, 4, 2),
        (64, 64, 64, 8, 2),
        # Larger KV blocks
        (64, 128, 64, 8, 2),
        (64, 128, 128, 8, 2),
        # Aggressive unrolling
        (64, 32, 64, 8, 3),
        (64, 64, 64, 8, 3),
    ]

    # Precision modes
    PRECISION_MODES: List[str] = ["tf32", "ieee", "tf32x3"]

    # Loop orders for cache optimization
    LOOP_ORDERS: List[str] = ["default", "kv_first", "q_first"]

    @classmethod
    def get_helion_config(cls, config_idx: int = 0) -> dict:
        """Get Helion Config dict for given index."""
        if config_idx >= len(cls.BLOCK_CONFIGS):
            config_idx = 0

        block_m, block_n, block_k, num_warps, num_stages = cls.BLOCK_CONFIGS[config_idx]

        return {
            "block_sizes": [block_m, block_n, block_k],
            "num_warps": num_warps,
            "num_stages": num_stages,
            "indexing": "block_ptr",  # Better than pointer for MI355X
            "pid_type": "flat",  # CDNA 4 prefers flat grid
            "l2_groupings": [8],  # L2 cache line optimization
        }

    @classmethod
    def get_all_configs(cls) -> List[dict]:
        """Return all configurations for grid search."""
        return [cls.get_helion_config(i) for i in range(len(cls.BLOCK_CONFIGS))]


# Export for Helion decorator
HELION_CONFIGS = MLAAutotuneConfig.get_all_configs()

# Recommended default for quick iteration
DEFAULT_CONFIG = {
    "block_sizes": [64, 32, 64],
    "num_warps": 4,
    "num_stages": 2,
    "indexing": "block_ptr",
    "pid_type": "flat",
    "l2_groupings": [8],
}
