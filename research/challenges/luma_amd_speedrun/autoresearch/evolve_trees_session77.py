"""
Evolve K-Search trees with Session 77 confirmed discoveries.

Injects new strategies based on:
1. GEMM: 192x128 tile kernel for M>32 (CONFIRMED 4/4 pass)
2. GEMM: gen_gemm_a4w4_blockscale_fake_tensors at aiter level (not tuned_gemm)
3. GEMM: Triton block_scaled_matmul tutorial (official MXFP4 CDNA4)
4. MoE: CK_BLOCK_GEMM=1 (CONFIRMED: all shapes pass, 182us without KSPLIT)
5. MoE: CK_BLOCK_GEMM=1 + adaptive KSPLIT combined (UNTESTED)
6. MoE: KSPLIT=6 for est_m<5 (OpenCode Kimi v16, UNTESTED)
7. MoE: FlyDSL Pipeline available on runner (CONFIRMED)
8. MoE: AITER_BYPASS_TUNE_CONFIG=1 eliminates CSV lookup
9. MLA: pa_ps_fwd_asm persistent streaming paged attention (CONFIRMED EXISTS)
10. MLA: fmha_v3_varlen_fwd FlashMHA v3 variable length (CONFIRMED EXISTS)
11. MLA: flash_attn_varlen_func with padded V (WRITTEN, untested)
12. MLA: 13 total attention APIs discovered

This is Cohezion treating kernel optimization as RL:
- K-Search tree = policy (which strategies to try)
- Ralph Loop = episode (benchmark -> gate -> propose -> apply -> verify)
- Node result_us = reward signal
- Tree evolution = policy update
"""

from __future__ import annotations

import sys
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
from ksearch_tree import KSearchTree


def evolve_gemm_tree():
    """Inject Session 77 GEMM discoveries."""
    tree_path = Path(__file__).parent / "tree" / "gemm_tree.json"
    tree = KSearchTree.load(tree_path)

    # --- Strategy 1: 192x128 tile kernel for M>32 (CONFIRMED WORKING) ---
    tree.insert_child(
        parent_id="root_gemm",
        strategy=(
            "192x128 tile kernel for M>32: gen_gemm_a4w4 with 192x128 tile "
            "(CONFIRMED 4/4 pass, use for M=64 and M=256 shapes)"
        ),
        parameters={
            "kernel": "gen_gemm_a4w4",
            "tile": "192x128",
            "condition": "M > 32",
            "confirmed_shapes": [
                "64_7168_2048",
                "256_3072_1536",
            ],
            "status": "CONFIRMED_WORKING",
        },
        priority=0.92,
        notes=(
            "[Session 77] CONFIRMED: 4/4 shapes pass with 192x128 tile. "
            "Use for M>32 shapes where larger tile improves occupancy."
        ),
    )

    # --- Strategy 2: gen_gemm_a4w4_blockscale_fake_tensors at aiter level ---
    tree.insert_child(
        parent_id="root_gemm",
        strategy=(
            "gen_gemm_a4w4_blockscale_fake_tensors: aiter-level block-scale GEMM "
            "(NOT tuned_gemm -- separate API path with blockscale support)"
        ),
        parameters={
            "api": "aiter.gen_gemm_a4w4_blockscale_fake_tensors",
            "note": "Found at aiter level, not inside tuned_gemm module",
            "blockscale": True,
        },
        priority=0.88,
        notes=(
            "[Session 77] Discovered at aiter top-level, distinct from tuned_gemm.tgemm.mm(). "
            "Block-scale variant may handle MXFP4 natively without separate quant step."
        ),
    )

    # --- Strategy 3: Triton block_scaled_matmul tutorial (official MXFP4 CDNA4) ---
    tree.insert_child(
        parent_id="root_gemm",
        strategy=(
            "Triton block_scaled_matmul tutorial: official MXFP4 CDNA4 reference kernel "
            "(Triton tutorial path, not aiter ASM)"
        ),
        parameters={
            "source": "triton_tutorials/block_scaled_matmul",
            "format": "MXFP4",
            "target": "CDNA4 (MI355X)",
            "approach": "triton_jit",
        },
        priority=0.80,
        notes=(
            "[Session 77] Official Triton tutorial for block-scaled matmul on CDNA4. "
            "Reference implementation for MXFP4 -- may be tunable beyond default params."
        ),
    )

    tree.save(tree_path)
    stats = tree.get_stats()
    print(f"GEMM tree: {stats}")
    return stats


def evolve_moe_tree():
    """Inject Session 77 MoE discoveries."""
    tree_path = Path(__file__).parent / "tree" / "moe_tree.json"
    tree = KSearchTree.load(tree_path)

    # --- Strategy 1: CK_BLOCK_GEMM=1 (CONFIRMED: all shapes pass, 182us) ---
    node1 = tree.insert_child(
        parent_id="root_moe",
        strategy=(
            "CK_BLOCK_GEMM=1 without KSPLIT: block GEMM dispatch "
            "(CONFIRMED: all shapes pass, 182us baseline)"
        ),
        parameters={
            "env": {"CK_BLOCK_GEMM": "1"},
            "KSPLIT": 0,
            "result_baseline_us": 182.0,
            "status": "CONFIRMED_WORKING",
        },
        priority=0.95,
        notes=(
            "[Session 77] CONFIRMED: CK_BLOCK_GEMM=1 passes ALL shapes at 182us "
            "without any KSPLIT. This is the new baseline to beat with KSPLIT tuning."
        ),
    )

    # --- Strategy 2: CK_BLOCK_GEMM=1 + adaptive KSPLIT (UNTESTED) ---
    tree.insert_child(
        parent_id=node1.id,
        strategy=(
            "CK_BLOCK_GEMM=1 + adaptive KSPLIT: combine block GEMM with "
            "per-shape KSPLIT tuning (UNTESTED combination)"
        ),
        parameters={
            "env": {"CK_BLOCK_GEMM": "1"},
            "KSPLIT_TABLE": {
                "257_256_16": 4,
                "257_256_128": 4,
                "257_256_512": 0,
                "33_512_16": 2,
                "33_512_128": 2,
                "33_512_512": 0,
                "33_2048_512": 0,
            },
            "status": "UNTESTED",
        },
        priority=0.93,
        notes=(
            "[Session 77] UNTESTED: CK_BLOCK_GEMM=1 confirmed at 182us baseline. "
            "Adding adaptive KSPLIT on top may push below 182us. "
            "High priority -- best previous MoE result was 88.68us with OPUS+KSPLIT."
        ),
    )

    # --- Strategy 3: KSPLIT=6 for est_m<5 (OpenCode Kimi v16) ---
    tree.insert_child(
        parent_id="root_moe",
        strategy=(
            "KSPLIT=6 for est_m<5: OpenCode Kimi v16 heuristic "
            "(high KSPLIT for very small effective M)"
        ),
        parameters={
            "condition": "est_m < 5",
            "KSPLIT": 6,
            "source": "OpenCode Kimi v16",
            "status": "UNTESTED",
        },
        priority=0.75,
        notes=(
            "[Session 77] From OpenCode Kimi v16 submission. KSPLIT=6 when estimated M "
            "per expert is very small (<5 tokens). Rationale: small M needs more K-splits "
            "to keep CUs busy. UNTESTED on our shapes."
        ),
    )

    # --- Strategy 4: FlyDSL Pipeline (CONFIRMED available) ---
    tree.insert_child(
        parent_id="root_moe",
        strategy=(
            "FlyDSL Pipeline: DSL-based kernel generation for MoE dispatch "
            "(CONFIRMED available on runner)"
        ),
        parameters={
            "tool": "FlyDSL",
            "status": "CONFIRMED_AVAILABLE",
            "approach": "dsl_pipeline",
        },
        priority=0.65,
        notes=(
            "[Session 77] FlyDSL Pipeline confirmed available on Kaggle runner. "
            "Can generate custom MoE dispatch kernels. Lower priority than "
            "CK_BLOCK_GEMM tuning but offers a fundamentally different approach."
        ),
    )

    # --- Strategy 5: AITER_BYPASS_TUNE_CONFIG=1 ---
    tree.insert_child(
        parent_id="root_moe",
        strategy=(
            "AITER_BYPASS_TUNE_CONFIG=1: eliminate CSV tune config lookup "
            "(reduces dispatch overhead)"
        ),
        parameters={
            "env": {"AITER_BYPASS_TUNE_CONFIG": "1"},
            "status": "CONFIRMED_WORKING",
        },
        priority=0.70,
        notes=(
            "[Session 77] CONFIRMED: Setting AITER_BYPASS_TUNE_CONFIG=1 eliminates "
            "CSV config file lookup overhead. Combine with CK_BLOCK_GEMM=1 for "
            "reduced dispatch latency."
        ),
    )

    tree.save(tree_path)
    stats = tree.get_stats()
    print(f"MoE tree: {stats}")
    return stats


def evolve_mla_tree():
    """Inject Session 77 MLA/attention discoveries."""
    tree_path = Path(__file__).parent / "tree" / "mla_tree.json"
    tree = KSearchTree.load(tree_path)

    # --- Strategy 1: pa_ps_fwd_asm (persistent streaming paged attention) ---
    tree.insert_child(
        parent_id="root_mla",
        strategy=(
            "pa_ps_fwd_asm: persistent streaming paged attention "
            "(ASM kernel, CONFIRMED EXISTS in aiter)"
        ),
        parameters={
            "api": "aiter.pa_ps_fwd_asm",
            "type": "persistent_streaming",
            "format": "paged",
            "status": "CONFIRMED_EXISTS",
        },
        priority=0.90,
        notes=(
            "[Session 77] CONFIRMED EXISTS: Persistent streaming paged attention ASM kernel. "
            "Persistent kernels stay resident on CUs -- avoids launch overhead. "
            "Streaming variant processes KV cache incrementally. "
            "High priority for decode-heavy workloads."
        ),
    )

    # --- Strategy 2: fmha_v3_varlen_fwd (FlashMHA v3 variable length) ---
    tree.insert_child(
        parent_id="root_mla",
        strategy=(
            "fmha_v3_varlen_fwd: FlashMHA v3 variable-length forward "
            "(CONFIRMED EXISTS, latest flash attention generation)"
        ),
        parameters={
            "api": "aiter.fmha_v3_varlen_fwd",
            "type": "flash_mha_v3",
            "variable_length": True,
            "status": "CONFIRMED_EXISTS",
        },
        priority=0.88,
        notes=(
            "[Session 77] CONFIRMED EXISTS: FlashMHA v3 variable-length forward kernel. "
            "V3 is the latest generation -- likely optimized for CDNA4. "
            "Variable-length support handles ragged batches without padding waste."
        ),
    )

    # --- Strategy 3: flash_attn_varlen_func with padded V ---
    tree.insert_child(
        parent_id="root_mla",
        strategy=(
            "flash_attn_varlen_func with padded V: handle MLA fused KV "
            "by padding V dimension (WRITTEN, untested)"
        ),
        parameters={
            "api": "aiter.flash_attn_varlen_func",
            "approach": "pad_v_dimension",
            "pad_strategy": "zero_pad_to_head_dim",
            "status": "WRITTEN_UNTESTED",
        },
        priority=0.82,
        notes=(
            "[Session 77] WRITTEN but untested: flash_attn_varlen_func requires V "
            "with same head_dim as Q/K. MLA has compressed KV -- pad V to match. "
            "If padding overhead < dispatch overhead savings, this wins."
        ),
    )

    # --- Strategy 4: 13 attention APIs landscape node ---
    tree.insert_child(
        parent_id="root_mla",
        strategy=(
            "Attention API landscape: 13 total APIs discovered in aiter "
            "(systematic evaluation needed)"
        ),
        parameters={
            "apis_discovered": [
                "flash_attn_func",
                "flash_attn_varlen_func",
                "paged_attention_fwd",
                "pa_ps_fwd_asm",
                "fmha_v3_varlen_fwd",
                "fav3_sage_attn_fwd",
                "fav3_sage_mxfp4",
                "mla_decode_fwd",
                "mla_decode_fwd_v2",
                "mla_extend_fwd",
                "fmha_fwd",
                "fmha_varlen_fwd",
                "fmha_bwd",
            ],
            "total_count": 13,
            "status": "LANDSCAPE_MAPPED",
        },
        priority=0.50,
        notes=(
            "[Session 77] 13 total attention APIs catalogued. Priority APIs for MLA: "
            "pa_ps_fwd_asm (persistent streaming), fmha_v3_varlen_fwd (latest gen), "
            "flash_attn_varlen_func (padded V approach). Lower-priority: fav3_sage variants, "
            "mla_decode_fwd_v2. This node tracks the landscape for systematic evaluation."
        ),
    )

    tree.save(tree_path)
    stats = tree.get_stats()
    print(f"MLA tree: {stats}")
    return stats


if __name__ == "__main__":
    print("=" * 60)
    print("Evolving K-Search trees with Session 77 discoveries...")
    print("=" * 60)
    print()

    gemm_stats = evolve_gemm_tree()
    print()
    moe_stats = evolve_moe_tree()
    print()
    mla_stats = evolve_mla_tree()

    print()
    print("=" * 60)
    print("Evolution complete. Summary:")
    print(f"  GEMM: {gemm_stats['active']} active / {gemm_stats['total_nodes']} total nodes")
    print(f"  MoE:  {moe_stats['active']} active / {moe_stats['total_nodes']} total nodes")
    print(f"  MLA:  {mla_stats['active']} active / {mla_stats['total_nodes']} total nodes")
    print("=" * 60)
