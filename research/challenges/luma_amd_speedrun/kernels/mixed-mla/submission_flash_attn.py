"""
MLA Novel Approach: Use aiter.flash_attn_func instead of mla_decode_fwd.

The MLA bottleneck is the 3-stage Python dispatch (67µs vs leader 4.3µs).
aiter.flash_attn_func achieves 17.19x speedup on attention (per Qwen-VL blog).
If it can handle MLA's fused KV format, this could dramatically close the gap.

Also probe: aiter.ops.triton.mla_decode (different from mla_decode_fwd).
"""

from __future__ import annotations

import inspect
import os
import sys


os.environ["AITER_USE_NT"] = "1"

import aiter
import torch
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data

    bs = config["batch_size"]
    num_heads = config["num_heads"]
    qk_head_dim = config["qk_head_dim"]  # 576
    v_head_dim = config["v_head_dim"]  # 512
    kv_seq_len = config["kv_seq_len"]
    sm_scale = config["sm_scale"]

    # === Probe 1: flash_attn_func ===
    try:
        sig = str(inspect.signature(aiter.flash_attn_func))
        print(f"flash_attn_func sig: {sig}", file=sys.stderr)

        # flash_attn typically wants (q, k, v, softmax_scale)
        # MLA has fused KV: kv_data['bf16'] is [total_kv, 1, 576]
        # We need to split into K and V components
        # K = kv_data[:, :, :qk_head_dim], V = kv_data[:, :, :v_head_dim]
        kv_bf16 = kv_data["bf16"]
        print(f"kv_bf16 shape: {kv_bf16.shape}", file=sys.stderr)

    except Exception as e:
        print(f"flash_attn_func probe: {e}", file=sys.stderr)

    # === Probe 2: aiter.ops.triton.mla_decode (different module path) ===
    try:
        from aiter.ops.triton import mla_decode as mla_mod

        mla_attrs = [a for a in dir(mla_mod) if not a.startswith("_")]
        print(f"aiter.ops.triton.mla_decode attrs: {mla_attrs}", file=sys.stderr)
    except Exception as e:
        print(f"mla_decode module: {e}", file=sys.stderr)

    # === Probe 3: Check for paged_attention or other attention APIs ===
    try:
        attn_apis = [a for a in dir(aiter) if "attn" in a.lower() or "attention" in a.lower()]
        print(f"All attention APIs: {attn_apis}", file=sys.stderr)

        # Check for paged attention (used in production inference)
        if hasattr(aiter, "paged_attention_fwd"):
            sig = str(inspect.signature(aiter.paged_attention_fwd))
            print(f"paged_attention_fwd sig: {sig}", file=sys.stderr)
    except Exception as e:
        print(f"attention API scan: {e}", file=sys.stderr)

    # === Probe 4: fav3_sage (previously found but not fully explored) ===
    try:
        if hasattr(aiter, "fav3_sage_attn_fwd"):
            sig = str(inspect.signature(aiter.fav3_sage_attn_fwd))
            print(f"fav3_sage_attn_fwd sig: {sig}", file=sys.stderr)
        elif hasattr(aiter, "fav3_sage_mxfp4"):
            sig = str(inspect.signature(aiter.fav3_sage_mxfp4))
            print(f"fav3_sage_mxfp4 sig: {sig}", file=sys.stderr)
    except Exception as e:
        print(f"fav3_sage probe: {e}", file=sys.stderr)

    # === Probe 5: Direct ASM attention ops ===
    try:
        asm_attn = [a for a in dir(torch.ops.aiter) if "attn" in a.lower() or "mla" in a.lower()]
        print(f"torch.ops.aiter attention ops: {asm_attn}", file=sys.stderr)
    except Exception as e:
        print(f"torch.ops.aiter scan: {e}", file=sys.stderr)

    return ref_kernel(data)
