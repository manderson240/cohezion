#!/usr/bin/env python3
"""Inject breakthrough nodes into K-Search trees.

Updates trees with:
1. Correct current best values
2. Breakthrough hypothesis nodes for each kernel

Usage:
    uv run python inject_breakthrough_nodes.py
"""

import json
import logging
from pathlib import Path


logging.basicConfig(level=logging.INFO)
log = logging.getLogger("inject_breakthrough")


BREAKTHROUGH_NODES = {
    "gemm": {
        "current_best_us": 13.425,
        "rank1_target_us": 4.327,
        "nodes": [
            {
                "id": "gemm_breakthrough_direct_ck",
                "strategy": "Direct CK dispatch via ctypes - bypass aiter Python overhead",
                "priority": 0.95,
                "parameters": {
                    "approach": "direct_ctypes_dispatch",
                    "note": "288B kernel arg layout found. Stream sync error blocks this path.",
                    "status": "blocked",
                },
                "notes": "GEMM breakthrough: 288-byte kernel arg layout found in asm_gemm_a4w4.cu. 35 .co files at /home/runner/aiter/hsa/gfx950/f4gemm/. Blocked by 'work on another stream' error.",
            },
            {
                "id": "gemm_breakthrough_blockscale",
                "strategy": "gemm_a4w4_blockscale with tuned splitK - direct ASM path",
                "priority": 0.90,
                "parameters": {
                    "approach": "blockscale_tuned",
                    "note": "Try different splitK values for dominant shape M=16/N=2112/K=7168",
                    "status": "active",
                },
                "notes": "GEMM fallback: gemm_a4w4_blockscale has less overhead than gemm_a4w4. Try tuned splitK.",
            },
            {
                "id": "gemm_breakthrough_custom_triton",
                "strategy": "Custom Triton kernel with fused quant - if scale layout correct",
                "priority": 0.80,
                "parameters": {
                    "approach": "custom_triton_fused_quant",
                    "note": "tl.dot_scaled requires RHS scale [BLOCK_N, SCALE_PER_K] - N-first layout",
                    "status": "research",
                },
                "notes": "GEMM long shot: Write Triton kernel with inline MXFP4 quantization.",
            },
        ],
    },
    "moe": {
        "current_best_us": 154.183,
        "rank1_target_us": 109.793,
        "nodes": [
            {
                "id": "moe_breakthrough_direct_cktile",
                "strategy": "Direct cktile_moe_gemm1/2 dispatch - bypass fused_moe wrapper",
                "priority": 0.95,
                "parameters": {
                    "approach": "direct_cktile_dispatch",
                    "note": "cktile_moe_gemm1/2 support kernel_name param for direct dispatch",
                    "status": "active",
                },
                "notes": "MoE breakthrough: fused_moe wrapper has ~5-10µs overhead. Direct cktile dispatch bypasses this and enables KSPLIT control.",
            },
            {
                "id": "moe_breakthrough_precompiled_probe",
                "strategy": "Probe 182 pre-compiled fmoe_2stages kernels for faster variants",
                "priority": 0.85,
                "parameters": {
                    "approach": "probe_precompiled",
                    "note": "182 kernels at /home/runner/aiter/hsa/gfx950/fmoe_2stages/",
                    "status": "research",
                },
                "notes": "MoE research: Many pre-compiled kernels may be unreachable via fused_moe wrapper.",
            },
            {
                "id": "moe_breakthrough_use_nt_combined",
                "strategy": "USE_NT=1 + optimal block_m tuning",
                "priority": 0.75,
                "parameters": {
                    "approach": "use_nt_plus_block_m",
                    "note": "USE_NT=1 already helps. block_m tuning may add more.",
                    "status": "active",
                },
                "notes": "MoE incremental: USE_NT=1 gave 10% improvement. block_m tuning may add more.",
            },
        ],
    },
    "mla": {
        "current_best_us": 69.745,
        "rank1_target_us": 32.972,
        "nodes": [
            {
                "id": "mla_breakthrough_ps_buffer",
                "strategy": "PS metadata buffer pre-allocation - avoid 20-30µs C++ overhead",
                "priority": 0.95,
                "parameters": {
                    "approach": "ps_buffer_prealloc",
                    "note": "Pass work_meta_data to avoid C++ allocating PS buffer per call",
                    "status": "active",
                },
                "notes": "MLA breakthrough: C++ allocates PS metadata buffer (~20-30µs) when work_meta_data=None. Pre-allocating avoids this.",
            },
            {
                "id": "mla_breakthrough_mfma",
                "strategy": "MFMA-based MLA kernel - 36× fewer ops vs FP4 LUT approach",
                "priority": 0.80,
                "parameters": {
                    "approach": "mfma_custom_kernel",
                    "note": "CDNA3 native MFMA: __builtin_amdgcn_mfma_scale_f32_16x16x128_f8f6f4",
                    "status": "research",
                },
                "notes": "MLA moonshot: Custom MFMA kernel could be 36× faster than FP4 LUT approach.",
            },
            {
                "id": "mla_breakthrough_mxfp4_kv",
                "strategy": "MXFP4 KV cache path - 4× compression if head_size constraint resolved",
                "priority": 0.70,
                "parameters": {
                    "approach": "mxfp4_kv_cache",
                    "note": "ASM kernel rejects MXFP4: 'head_size == KV.size(3)' assertion",
                    "status": "blocked",
                },
                "notes": "MLA blocked: ASM kernel has head_size assertion. Custom kernel needed.",
            },
        ],
    },
}


def load_tree(kernel: str) -> dict:
    """Load K-Search tree."""
    tree_path = Path(__file__).parent / f"{kernel}_tree.json"
    if tree_path.exists():
        with open(tree_path) as f:
            return json.load(f)
    return {"kernel_name": kernel, "nodes": {}, "root_id": None}


def save_tree(kernel: str, tree: dict) -> None:
    """Save K-Search tree."""
    tree_path = Path(__file__).parent / f"{kernel}_tree.json"
    with open(tree_path, "w") as f:
        json.dump(tree, f, indent=2)
    log.info(f"Saved {kernel}_tree.json")


def inject_breakthrough_nodes(kernel: str) -> None:
    """Inject breakthrough nodes into tree."""
    if kernel not in BREAKTHROUGH_NODES:
        log.warning(f"No breakthrough data for kernel: {kernel}")
        return

    data = BREAKTHROUGH_NODES[kernel]
    tree = load_tree(kernel)

    # Update root best_result_us
    root_id = tree.get("root_id")
    if root_id and root_id in tree["nodes"]:
        old_best = tree["nodes"][root_id].get("best_result_us", float("inf"))
        tree["nodes"][root_id]["best_result_us"] = data["current_best_us"]
        log.info(f"Updated {kernel} root best: {old_best:.1f} → {data['current_best_us']:.1f}µs")

    # Inject breakthrough nodes
    for node_data in data["nodes"]:
        node_id = node_data["id"]

        if node_id in tree["nodes"]:
            log.info(f"Node {node_id} exists, updating...")
            tree["nodes"][node_id].update(node_data)
        else:
            log.info(f"Adding breakthrough node: {node_id}")
            tree["nodes"][node_id] = node_data

            # Add to root children if not there
            if root_id and root_id in tree["nodes"]:
                if node_id not in tree["nodes"][root_id].get("children", []):
                    tree["nodes"][root_id].setdefault("children", []).append(node_id)

    save_tree(kernel, tree)
    log.info(f"  Target: {data['rank1_target_us']}µs (Rank 1)")
    log.info(f"  Gap: {data['current_best_us'] / data['rank1_target_us']:.1f}×")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Inject breakthrough nodes into K-Search trees")
    parser.add_argument(
        "--kernel",
        choices=["gemm", "moe", "mla", "all"],
        default="all",
        help="Kernel to update",
    )
    args = parser.parse_args()

    kernels = ["gemm", "moe", "mla"] if args.kernel == "all" else [args.kernel]

    print("\n" + "=" * 60)
    print("BREAKTHROUGH NODE INJECTION")
    print("=" * 60)

    for kernel in kernels:
        print(f"\n[{kernel}]")
        inject_breakthrough_nodes(kernel)

    print("\n" + "=" * 60)
    print("INJECTION COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    main()
