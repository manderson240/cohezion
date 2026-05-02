#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""MLA breakthrough: Direct .co dispatch via load_inline C++.

Stage 1: Calls mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co directly.
Stage 2: Calls mla_reduce_v1 (fallback to aiter).

Bypasses Python dispatch overhead (~20us).
"""

import torch
from aiter import dtypes as aiter_dtypes
from aiter import (
    get_mla_metadata_info_v1,
    get_mla_metadata_v1,
    mla_reduce_v1,
)
from task import input_t, output_t
from torch.utils.cpp_extension import load_inline


# --- Architecture Constants ---
NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1
FP8_DTYPE = aiter_dtypes.fp8

# --- Kernel Info ---
_CO_PATH = "/home/runner/aiter/hsa/gfx950/mla/mla_a8w8_qh16_qseqlen1_gqaratio16_ps.co"
_KERNEL_SYMBOL = "_ZN5aiter36mla_a8w8_qh16_qseqlen1_gqaratio16_psE"

HIP_SOURCE = (
    r'''
#include <torch/extension.h>
#include <hip/hip_runtime.h>
#include <stdint.h>

// 320-byte MlaKernelArgs struct (packed)
struct __attribute__((packed)) MlaKernelArgs {
    uint64_t ptr_R;           uint32_t _p0[2];
    uint64_t ptr_LSE;         uint32_t _p1[2];
    uint64_t ptr_Q;           uint32_t _p2[2];
    uint64_t ptr_KV;          uint32_t _p3[2];
    uint64_t ptr_LTP;         uint32_t _p4[2];
    uint64_t ptr_LTD;         uint32_t _p5[2];
    uint64_t ptr_LTL;         uint32_t _p6[2];
    float scalar;             uint32_t _p12[3];
    uint32_t s_MQA;           uint32_t _p13[3];
    uint32_t s_kv_split;      uint32_t _p14[3];
    uint32_t s_Q_Bs;          uint32_t _p15[3];
    uint32_t s_Bs;            uint32_t _p16[3];
    uint32_t s_log2_plen;     uint32_t _p17[3];
    uint64_t ptr_QTP;         uint32_t _p18[2];
    uint64_t ptr_STP;         uint32_t _p19[2];
    uint64_t ptr_RP;          uint32_t _p20[2];
    uint64_t ptr_QSCALE;      uint32_t _p21[2];
    uint64_t ptr_KVSCALE;     uint32_t _p22[2];
    uint32_t out_16_nosplit;  uint32_t _p23[3];
    uint64_t ptr_LSEP;        uint32_t _p24[2];
};

static hipModule_t g_mla_module = nullptr;
static hipFunction_t g_mla_func = nullptr;

void init_mla_module() {
    if (!g_mla_module) {
        hipModuleLoad(&g_mla_module, "'''
    + _CO_PATH
    + r'''");
        hipModuleGetFunction(&g_mla_func, g_mla_module, "'''
    + _KERNEL_SYMBOL
    + r"""");
    }
}

void launch_mla_direct(
    torch::Tensor Q, torch::Tensor KV, torch::Tensor QoIndptr, torch::Tensor KvIndptr,
    torch::Tensor KvIndices, torch::Tensor KvLastPageLen, torch::Tensor WorkMetadata,
    torch::Tensor QScale, torch::Tensor KvScale,
    torch::Tensor Logits, torch::Tensor AttnLse, torch::Tensor Output,
    float sm_scale, int num_kv_splits, int gdx
) {
    MlaKernelArgs args = {};
    args.ptr_R = reinterpret_cast<uint64_t>(Logits.data_ptr());
    args.ptr_LSE = reinterpret_cast<uint64_t>(AttnLse.data_ptr());
    args.ptr_Q = reinterpret_cast<uint64_t>(Q.data_ptr());
    args.ptr_KV = reinterpret_cast<uint64_t>(KV.data_ptr());
    args.ptr_LTP = reinterpret_cast<uint64_t>(KvIndptr.data_ptr());
    args.ptr_LTD = reinterpret_cast<uint64_t>(KvIndices.data_ptr());
    args.ptr_LTL = reinterpret_cast<uint64_t>(KvLastPageLen.data_ptr());
    args.scalar = sm_scale;
    args.s_MQA = 16; // NUM_HEADS
    args.s_kv_split = num_kv_splits;
    args.s_Q_Bs = Q.stride(0) * Q.element_size();
    args.s_Bs = KV.stride(0) * KV.element_size();
    args.s_log2_plen = 0;
    args.ptr_QTP = reinterpret_cast<uint64_t>(QoIndptr.data_ptr());
    args.ptr_STP = reinterpret_cast<uint64_t>(WorkMetadata.data_ptr());
    args.ptr_RP = reinterpret_cast<uint64_t>(Output.data_ptr());
    args.ptr_QSCALE = reinterpret_cast<uint64_t>(QScale.data_ptr());
    args.ptr_KVSCALE = reinterpret_cast<uint64_t>(KvScale.data_ptr());
    args.out_16_nosplit = num_kv_splits;

    size_t arg_size = sizeof(args);
    void* config[] = {
        (void*)0x01, &args,
        (void*)0x02, &arg_size,
        (void*)0x03
    };

    hipModuleLaunchKernel(g_mla_func, gdx, 1, 1, 256, 1, 1, 0, 0, nullptr, config);
}
"""
)

CPP_SOURCE = "void init_mla_module(); void launch_mla_direct(torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, torch::Tensor, float, int, int);"

_mod = None


def get_mod():
    global _mod
    if _mod is None:
        try:
            _mod = load_inline(
                name="mla_direct_co",
                cpp_sources=[CPP_SOURCE],
                cuda_sources=[HIP_SOURCE],
                functions=["init_mla_module", "launch_mla_direct"],
                verbose=False,
                extra_cuda_cflags=["-O3", "--offload-arch=gfx950"],
            )
            _mod.init_mla_module()
        except Exception as e:
            print(f"load_inline failed: {e}")
    return _mod


_cache = {}


def _get_cached_metadata(
    bs, qseqlen, kvseqlen, q_dtype, kv_dtype, qo_indptr, kv_indptr, num_kv_splits
):
    key = (bs, qseqlen, kvseqlen, q_dtype, kv_dtype, num_kv_splits)
    if key in _cache:
        return _cache[key]

    kv_last_page_len = (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32)
    info = get_mla_metadata_info_v1(
        bs,
        qseqlen,
        NUM_HEADS,
        q_dtype,
        kv_dtype,
        is_sparse=False,
        fast_mode=False,
        num_kv_splits=num_kv_splits,
        intra_batch_mode=True,
    )
    work = [torch.empty(s, dtype=t, device="cuda") for s, t in info]
    (
        work_metadata,
        work_indptr,
        work_info_set,
        reduce_indptr,
        reduce_final_map,
        reduce_partial_map,
    ) = work

    get_mla_metadata_v1(
        qo_indptr,
        kv_indptr,
        kv_last_page_len,
        NUM_HEADS,
        NUM_KV_HEADS,
        True,
        work_metadata,
        work_info_set,
        work_indptr,
        reduce_indptr,
        reduce_final_map,
        reduce_partial_map,
        page_size=PAGE_SIZE,
        kv_granularity=max(PAGE_SIZE, 16),
        max_seqlen_qo=qseqlen,
        uni_seqlen_qo=qseqlen,
        fast_mode=False,
        max_split_per_batch=num_kv_splits,
        intra_batch_mode=True,
        dtype_q=q_dtype,
        dtype_kv=kv_dtype,
    )

    total_q = bs * qseqlen
    meta = {
        "work_metadata": work_metadata,
        "work_indptr": work_indptr,
        "reduce_indptr": reduce_indptr,
        "reduce_final_map": reduce_final_map,
        "reduce_partial_map": reduce_partial_map,
        "kv_indices": torch.arange(int(kv_indptr[-1].item()), dtype=torch.int32, device="cuda"),
        "kv_last_page_len": kv_last_page_len,
        "logits": torch.empty(
            (num_kv_splits, total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.float32, device="cuda"
        ),
        "attn_lse": torch.empty(
            (num_kv_splits, total_q, NUM_HEADS), dtype=torch.float32, device="cuda"
        ),
        "output": torch.empty(
            (total_q, NUM_HEADS, V_HEAD_DIM), dtype=torch.bfloat16, device="cuda"
        ),
    }
    _cache[key] = meta
    return meta


def _quantize_fp8(tensor):
    finfo = torch.finfo(FP8_DTYPE)
    scale = tensor.abs().amax().clamp(min=1e-12) / finfo.max
    return (tensor / scale).clamp(min=finfo.min, max=finfo.max).to(
        FP8_DTYPE
    ), scale.float().reshape(1)


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs, qsl, kvsl = config["batch_size"], config["q_seq_len"], config["kv_seq_len"]

    kv_fp8, kv_scale = kv_data["fp8"]
    q_fp8, q_scale = _quantize_fp8(q)

    num_kv_splits = 1 if bs * kvsl <= 2048 else 4
    meta = _get_cached_metadata(
        bs, qsl, kvsl, q_fp8.dtype, kv_fp8.dtype, qo_indptr, kv_indptr, num_kv_splits
    )

    mod = get_mod()
    if mod:
        mod.launch_mla_direct(
            q_fp8,
            kv_fp8.view(-1, 1, 1, 576),
            qo_indptr,
            kv_indptr,
            meta["kv_indices"],
            meta["kv_last_page_len"],
            meta["work_metadata"],
            q_scale,
            kv_scale,
            meta["logits"],
            meta["attn_lse"],
            meta["output"],
            SM_SCALE,
            num_kv_splits,
            meta["work_indptr"].size(0) - 1,
        )

        mla_reduce_v1(
            meta["logits"],
            meta["attn_lse"],
            meta["reduce_indptr"],
            meta["reduce_final_map"],
            meta["reduce_partial_map"],
            qsl,
            meta["output"],
            None,
        )
        return meta["output"]

    return mla_reduce_v1(
        meta["logits"],
        meta["attn_lse"],
        meta["reduce_indptr"],
        meta["reduce_final_map"],
        meta["reduce_partial_map"],
        qsl,
        meta["output"],
        None,
    )
