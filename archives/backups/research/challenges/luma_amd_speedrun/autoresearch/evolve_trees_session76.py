"""
Evolve K-Search trees with Session 76 novel discoveries.

Injects new root strategies based on:
1. AITER blog findings (CK_BLOCK_GEMM, tuned_gemm, flash_attn_func)
2. 26 newly discovered MoE APIs (fmoe_g1u1_a16, fused_quant_moe_sort)
3. tritonblas fp4_matmul monkey-patching
4. GEMM quant ceiling confirmation → fused kernel as only path
5. MLA flash_attn approach (17.19x documented speedup)

This is Cohezion treating kernel optimization as RL:
- K-Search tree = policy (which strategies to try)
- Ralph Loop = episode (benchmark → gate → propose → apply → verify)
- Node result_us = reward signal
- Tree evolution = policy update
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from ksearch_tree import KSearchTree


def evolve_moe_tree():
    """Inject novel MoE strategies from Session 76 research."""
    tree_path = Path(__file__).parent / "tree" / "moe_tree.json"
    tree = KSearchTree.load(tree_path)

    # Strategy 1: CK_BLOCK_GEMM environment variable
    node1 = tree.insert_root(
        "CK_BLOCK_GEMM=1: Changes internal MoE dispatch to CK block GEMM path",
        parameters={"env": {"CK_BLOCK_GEMM": "1", "AITER_USE_NT": "1"}},
    )
    node1.priority = 0.9
    node1.notes = "From AITER blog Mar 2026. Never tested for fp4 MoE."

    # Strategy 2: fused_dynamic_mxfp4_quant_moe_sort
    node2 = tree.insert_root(
        "Fused quant+sort: fused_dynamic_mxfp4_quant_moe_sort replaces separate quant + sorting",
        parameters={"api": "aiter.ops.triton.quant.fused_dynamic_mxfp4_quant_moe_sort"},
    )
    node2.priority = 0.85
    node2.notes = "Callable confirmed. Fuses dynamic_mxfp4_quant + moe_mxfp4_sort."

    # Strategy 3: Direct CK stage dispatch with correct JIT caching
    node3 = tree.insert_root(
        "Direct CK stage1+stage2 with pre-warmed JIT (retry off-peak to avoid timeout)",
        parameters={"api": "aiter.ck_moe_stage1 + ck_moe_stage2", "non_temporal_load": True},
    )
    node3.priority = 0.7
    node3.notes = "Full 18-arg signatures confirmed. Timed out previously due to JIT cold start."

    # Strategy 4: Speculative expert execution
    node4 = tree.insert_root(
        "Speculate experts: pre-dispatch likely experts based on token statistics",
        parameters={"approach": "speculative_expert", "paper": "arxiv.org/html/2603.19289"},
    )
    node4.priority = 0.6
    node4.notes = "From research: speculating experts accelerates MoE inference."

    tree.save(tree_path)
    print(f"MoE tree: {tree.get_stats()}")


def evolve_gemm_tree():
    """Inject novel GEMM strategies from Session 76 research."""
    tree_path = Path(__file__).parent / "tree" / "gemm_tree.json"
    tree = KSearchTree.load(tree_path)

    # Strategy 1: tuned_gemm API path
    node1 = tree.insert_root(
        "tuned_gemm.tgemm.mm(): Auto-tuned CK/hipBLASLt GEMM (different from gemm_a4w4 ASM)",
        parameters={"api": "aiter.tuned_gemm.tgemm.mm"},
    )
    node1.priority = 0.8
    node1.notes = "From AITER blog. Completely different API path. May support fp4."

    # Strategy 2: tritonblas kernel monkey-patching
    node2 = tree.insert_root(
        "Monkey-patch tritonblas fp4_matmul: inject inline A-quantization into Origami kernel",
        parameters={"approach": "monkey_patch_tritonblas", "target": "fp4_matmul JIT source"},
    )
    node2.priority = 0.75
    node2.notes = (
        "tritonblas fp4_matmul works on runner (26µs). Kernel source accessible via inspect."
    )

    # Strategy 3: VLLM_USE_AITER_BLOCK_GEMM
    node3 = tree.insert_root(
        "VLLM_USE_AITER_BLOCK_GEMM=1: Enable block GEMM path for quantized inputs",
        parameters={"env": {"VLLM_USE_AITER_BLOCK_GEMM": "1"}},
    )
    node3.priority = 0.7
    node3.notes = "From AITER blog. Unknown if compatible with MXFP4."

    tree.save(tree_path)
    print(f"GEMM tree: {tree.get_stats()}")


def evolve_mla_tree():
    """Inject novel MLA strategies from Session 76 research."""
    tree_path = Path(__file__).parent / "tree" / "mla_tree.json"
    tree = KSearchTree.load(tree_path)

    # Strategy 1: flash_attn_func
    node1 = tree.insert_root(
        "flash_attn_func: AITER FlashAttention (17.19x speedup documented for Qwen-VL attention)",
        parameters={"api": "aiter.flash_attn_func"},
    )
    node1.priority = 0.9
    node1.notes = "From Qwen-VL blog Mar 24 2026. Must handle MLA fused KV format."

    # Strategy 2: paged_attention_fwd
    node2 = tree.insert_root(
        "paged_attention_fwd: Paged attention for decode (used in production inference)",
        parameters={"api": "aiter.paged_attention_fwd"},
    )
    node2.priority = 0.8
    node2.notes = "Production-grade attention API. May have lower overhead than mla_decode_fwd."

    # Strategy 3: fav3_sage variant
    node3 = tree.insert_root(
        "fav3_sage_attn_fwd: SAGE attention variant with MXFP4 KV cache support",
        parameters={"api": "aiter.fav3_sage_attn_fwd or fav3_sage_mxfp4"},
    )
    node3.priority = 0.7
    node3.notes = "Previously found but not fully explored. May bypass 3-stage dispatch."

    tree.save(tree_path)
    print(f"MLA tree: {tree.get_stats()}")


if __name__ == "__main__":
    print("Evolving K-Search trees with Session 76 discoveries...")
    evolve_moe_tree()
    evolve_gemm_tree()
    evolve_mla_tree()
    print("Done. Trees now have fresh unexplored strategies.")
