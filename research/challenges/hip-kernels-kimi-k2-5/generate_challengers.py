#!/usr/bin/env python3
"""Generate R-Zero Challenger Variants.

Creates 100 diverse challenger implementations for local evaluation.
"""

from pathlib import Path


BASE_DIR = Path("/home/mike-anderson/dev/cohezion/hip-kernels-kimi-k2-5/rzero-challengers")

# GEMM: Grid search tile sizes and split-K
GEMM_TILES = [
    ("32x128", "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x128E"),
    ("32x256", "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x256E"),
    ("32x512", "_ZN5aiter41f4gemm_bf16_per1x32Fp4_BpreShuffle_32x512E"),
    ("128x128", "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_128x128E"),
    ("192x128", "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E"),
    ("256x128", "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_256x128E"),
]

GEMM_SPLITS = [0, 1, 2, 3, 4]


def generate_gemm_challenger(
    idx: int, tile: tuple[str, str], log2_ks: int, shape_threshold: int
) -> str:
    """Generate a GEMM challenger with specific parameters."""
    tile_name, kernel_name = tile

    code = f'''"""GEMM Challenger {idx:03d}: Tile={tile_name}, Split-K={log2_ks}, Threshold={shape_threshold}."""
import torch
from task import input_t, output_t
import aiter
from aiter import dtypes
from aiter.ops.triton.quant import dynamic_mxfp4_quant
from aiter.utility.fp4_utils import e8m0_shuffle

def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data
    A = A.contiguous()
    M = A.shape[0]
    
    x_fp4, bs_e8m0 = dynamic_mxfp4_quant(A)
    A_scale_sh = e8m0_shuffle(bs_e8m0).view(dtypes.fp8_e8m0)
    A_q = x_fp4.view(dtypes.fp4x2)
    
    # Shape-adaptive kernel selection
    if M <= {shape_threshold}:
        kernel_name = "{kernel_name}"
        log2_ks = {log2_ks}
    else:
        kernel_name = "_ZN5aiter42f4gemm_bf16_per1x32Fp4_BpreShuffle_192x128E"
        log2_ks = 0
    
    out = torch.empty(M, B.shape[0], dtype=torch.bfloat16, device="cuda")
    
    return aiter.gemm_a4w4_asm(
        A_q, B_shuffle, A_scale_sh, B_scale_sh,
        out, kernel_name,
        bpreshuffle=True,
        log2_k_split=log2_ks,
    )
'''
    return code


def generate_all_gemm_challengers():
    """Generate all GEMM challenger variants."""
    gemm_dir = BASE_DIR / "gemm"
    gemm_dir.mkdir(parents=True, exist_ok=True)

    idx = 1
    for tile in GEMM_TILES:
        for log2_ks in GEMM_SPLITS:
            # Different shape thresholds for variety
            for threshold in [8, 16, 32, 64]:
                if idx > 33:  # Limit to 33 GEMM challengers
                    break
                code = generate_gemm_challenger(idx, tile, log2_ks, threshold)
                filepath = gemm_dir / f"challenger_{idx:03d}.py"
                filepath.write_text(code)
                idx += 1

    print(f"Generated {idx - 1} GEMM challengers")


# MoE: Grid search KSPLIT and thresholds
MOE_KSPLIT = [1, 2, 3, 4, 6, 8]
MOE_THRESHOLDS = [(5, 15), (10, 30), (15, 40)]


def generate_moe_challenger(idx: int, ks: int, thresholds: tuple[int, int], use_opus: bool) -> str:
    """Generate a MoE challenger."""
    t1, t2 = thresholds
    opus_flag = "1" if use_opus else "0"

    code = f'''"""MoE Challenger {idx:03d}: KSPLIT={ks}, Thresholds={thresholds}, OPUS={use_opus}."""
import os
import torch
from task import input_t, output_t
from aiter.fused_moe import fused_moe
from aiter import ActivationType, QuantType

os.environ["AITER_USE_NT"] = "1"
os.environ["AITER_USE_OPUS_MOE_SORTING"] = "{opus_flag}"

def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states, gate_up_weight, down_weight,
        gate_up_weight_scale, down_weight_scale,
        gate_up_weight_shuffled, down_weight_shuffled,
        gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
        topk_weights, topk_ids, config,
    ) = data

    hp = config["d_hidden_pad"] - config["d_hidden"]
    ip = config["d_expert_pad"] - config["d_expert"]
    ne = gate_up_weight_shuffled.shape[0]
    est_m = topk_ids.numel() // ne
    
    # Adaptive KSPLIT
    if est_m < {t1}:
        ks = "{min(ks * 2, 8)}"
    elif est_m < {t2}:
        ks = "{ks}"
    else:
        ks = "1"
    
    os.environ["AITER_BYPASS_TUNE_CONFIG"] = "1"
    os.environ["AITER_KSPLIT"] = ks

    return fused_moe(
        hidden_states, gate_up_weight_shuffled, down_weight_shuffled,
        topk_weights, topk_ids, expert_mask=None,
        activation=ActivationType.Silu, quant_type=QuantType.per_1x32,
        doweight_stage1=False,
        w1_scale=gate_up_weight_scale_shuffled, w2_scale=down_weight_scale_shuffled,
        a1_scale=None, a2_scale=None,
        hidden_pad=hp, intermediate_pad=ip,
    )
'''
    return code


def generate_all_moe_challengers():
    """Generate all MoE challenger variants."""
    moe_dir = BASE_DIR / "moe"
    moe_dir.mkdir(parents=True, exist_ok=True)

    idx = 1
    for ks in MOE_KSPLIT:
        for thresholds in MOE_THRESHOLDS:
            for use_opus in [True, False]:
                if idx > 33:  # Limit to 33 MoE challengers
                    break
                code = generate_moe_challenger(idx, ks, thresholds, use_opus)
                filepath = moe_dir / f"challenger_{idx:03d}.py"
                filepath.write_text(code)
                idx += 1

    print(f"Generated {idx - 1} MoE challengers")


# MLA: Grid search num_kv_splits and modes
MLA_SPLITS = [1, 2, 4, 8, 16, 32, 64]
MLA_MODES = [
    (True, True),  # fast_mode, intra_batch
    (True, False),
    (False, True),
    (False, False),
]


def generate_mla_challenger(idx: int, num_splits: int, fast_mode: bool, intra_batch: bool) -> str:
    """Generate an MLA challenger."""
    fast_str = "True" if fast_mode else "False"
    intra_str = "True" if intra_batch else "False"

    code = f'''"""MLA Challenger {idx:03d}: Splits={num_splits}, Fast={fast_mode}, Intra={intra_batch}."""
import torch
from task import input_t, output_t
from aiter.mla import mla_decode_fwd
from aiter import get_mla_metadata_v1

SM_SCALE = 1.0 / (576 ** 0.5)
V_HEAD_DIM = 512
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
PAGE_SIZE = 1

def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    qseqlen = config["q_seq_len"]
    nheads = config["num_heads"]
    total_kv = bs * kvseqlen
    
    # Use FP8 for speed
    kv_fp8 = kv_data["fp8"]
    kv_4d = kv_fp8.view(kv_fp8.shape[0], PAGE_SIZE, NUM_KV_HEADS, kv_fp8.shape[-1])
    
    num_splits = {num_splits}
    
    o = torch.empty((q.shape[0], nheads, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda")
    
    kv_indices = torch.arange(total_kv, dtype=torch.int32, device="cuda")
    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
    
    meta = get_mla_metadata_v1(
        bs, qseqlen, nheads, q.dtype, kv_fp8.dtype,
        qo_indptr, kv_indptr, kv_last_page_len,
        num_kv_splits=num_splits,
    )
    
    mla_decode_fwd(
        q.view(-1, nheads, QK_HEAD_DIM), kv_4d, o,
        qo_indptr, kv_indptr, kv_indices, kv_last_page_len,
        qseqlen, page_size=PAGE_SIZE, nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE, logit_cap=0.0, num_kv_splits=num_splits,
        intra_batch_mode={intra_str}, **meta,
    )
    return o
'''
    return code


def generate_all_mla_challengers():
    """Generate all MLA challenger variants."""
    mla_dir = BASE_DIR / "mla"
    mla_dir.mkdir(parents=True, exist_ok=True)

    idx = 1
    for num_splits in MLA_SPLITS:
        for fast_mode, intra_batch in MLA_MODES:
            if idx > 34:  # Limit to 34 MLA challengers
                break
            code = generate_mla_challenger(idx, num_splits, fast_mode, intra_batch)
            filepath = mla_dir / f"challenger_{idx:03d}.py"
            filepath.write_text(code)
            idx += 1

    print(f"Generated {idx - 1} MLA challengers")


def main():
    """Generate all 100 challengers."""
    print("R-Zero Challenger Generation")
    print("=" * 50)

    generate_all_gemm_challengers()
    generate_all_moe_challengers()
    generate_all_mla_challengers()

    total = 33 + 33 + 34
    print(f"\nTotal challengers generated: {total}")
    print(f"Location: {BASE_DIR}")


if __name__ == "__main__":
    main()
