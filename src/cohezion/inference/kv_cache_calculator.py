r"""Architecture-Aware KV-Cache Memory Calculation Engine
======================================================
Computes exact KV-Cache memory consumption based on:
  1. Attention Architecture (MHA, GQA, MLA)
  2. Transformer Hyperparameters (layers, kv_heads, head_dim)
  3. Total Tokens Allocated (Input Prompt Tokens + Max Generation Tokens)
  4. KV-Cache Quantization Precision (FP16, Q8_0, Q4_0)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import StrEnum


logger = logging.getLogger(__name__)


class AttentionType(StrEnum):
    MHA = "multi_head_attention"
    GQA = "grouped_query_attention"
    MLA = "multi_head_latent_attention"  # DeepSeek R1 / V3 low-rank latent compression


@dataclass(frozen=True, slots=True)
class ModelArchitectureSpec:
    model_name: str
    n_layers: int
    n_heads: int
    n_kv_heads: int
    head_dim: int
    attention_type: AttentionType = AttentionType.GQA
    latent_dim: int = 512  # For MLA (DeepSeek)


# Architecture Roster Specs
KNOWN_SPECS: dict[str, ModelArchitectureSpec] = {
    "deepseek-r1-70b": ModelArchitectureSpec(
        model_name="DeepSeek-R1-70B",
        n_layers=80,
        n_heads=64,
        n_kv_heads=8,
        head_dim=128,
        attention_type=AttentionType.GQA,
    ),
    "deepseek-r1-671b-mla": ModelArchitectureSpec(
        model_name="DeepSeek-R1-671B-MLA",
        n_layers=61,
        n_heads=128,
        n_kv_heads=128,
        head_dim=128,
        attention_type=AttentionType.MLA,
        latent_dim=512,
    ),
    "qwen3-coder-80b": ModelArchitectureSpec(
        model_name="Qwen3-Coder-Next-80B",
        n_layers=80,
        n_heads=64,
        n_kv_heads=8,
        head_dim=128,
        attention_type=AttentionType.GQA,
    ),
    "qwen3.6-moe-35b": ModelArchitectureSpec(
        model_name="qwen3.6-moe-35b-a3b",
        n_layers=40,
        n_heads=32,
        n_kv_heads=8,
        head_dim=128,
        attention_type=AttentionType.GQA,
    ),
    "muse-glimmer-30b": ModelArchitectureSpec(
        model_name="Muse-Glimmer-30B",
        n_layers=48,
        n_heads=32,
        n_kv_heads=8,
        head_dim=128,
        attention_type=AttentionType.GQA,
    ),
    "nemotron-3.5-lightning-30b": ModelArchitectureSpec(
        model_name="Nemotron-3.5-Lightning-30B-A3B-ROCmFP4",
        n_layers=48,
        n_heads=32,
        n_kv_heads=8,
        head_dim=128,
        attention_type=AttentionType.GQA,
    ),
}


def calculate_architecture_kv_cache_gb(
    model_key: str = "qwen3-coder-80b",
    prompt_tokens: int = 4096,
    max_gen_tokens: int = 4096,
    batch_size: int = 1,
    kv_bits: int = 16,  # 16 for FP16, 8 for Q8_0, 4 for Q4_0
) -> float:
    """Calculate exact KV-cache footprint in GB for a specific architecture and token allocation.

    Parameters
    ----------
    model_key : str
        Key matching KNOWN_SPECS.
    prompt_tokens : int
        Input prompt token length.
    max_gen_tokens : int
        Maximum tokens model is allowed to generate.
    batch_size : int
        Batch size (concurrent sequences).
    kv_bits : int
        Quantization bits for KV cache (16, 8, or 4).
    """
    spec = KNOWN_SPECS.get(model_key.lower())
    if not spec:
        spec = KNOWN_SPECS["qwen3-coder-80b"]

    total_tokens = prompt_tokens + max_gen_tokens
    bytes_per_elem = kv_bits / 8.0

    if spec.attention_type == AttentionType.MLA:
        # DeepSeek Latent KV Cache: stores latent vector (latent_dim) instead of n_kv_heads * head_dim
        # bytes = n_layers * latent_dim * total_tokens * batch_size * bytes_per_elem
        total_bytes = spec.n_layers * spec.latent_dim * total_tokens * batch_size * bytes_per_elem
    else:
        # Standard GQA / MHA: 2 * n_layers * n_kv_heads * head_dim * total_tokens * batch_size * bytes_per_elem
        total_bytes = (
            2
            * spec.n_layers
            * spec.n_kv_heads
            * spec.head_dim
            * total_tokens
            * batch_size
            * bytes_per_elem
        )

    return total_bytes / (1024.0**3)
