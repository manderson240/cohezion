#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X

"""BF16 decode kernel: triggers mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co

Root cause analysis of the dispatch bug:
  - mla_asm.csv defines the kernel selection table
  - Row: bf16,bf16,16,ps=0,qSeqLen=1,prefill=0 -> mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co
  - Row: bf16,bf16,16,ps=1,qSeqLen=4,prefill=0 -> mla_a16w16_qh16_m16x4_n16x1_coex0_mask1_ps.co (PREFILL!)

The previous BF16 submissions (submission_bf16_only.py, submission_a16w16.py) both pass
work_meta_data which sets persistent=True in asm_mla.cu line 128:
  bool persistent = (num_kv_splits_indptr == nullptr);
This forces ps=1 and config_max_seqlen_q=4 -> dispatches PREFILL kernel instead of DECODE.

The fix: use NON-persistent mode by passing num_kv_splits_indptr directly (not None)
and passing None for work_meta_data/work_indptr/work_info_set. This gives ps=0,
qSeqLen=1 for our decode case, matching the BF16 decode kernel row in the CSV.

Implementation: call mla_decode_fwd() without work_meta_data (non-persistent path)
but with explicit num_kv_splits and num_kv_splits_indptr. This keeps the code simple
while correctly routing to the BF16 decode kernel.

The non-persistent path in mla_decode_fwd:
  1. Calls mla_decode_stage1_asm_fwd with num_kv_splits_indptr (ps=0)
  2. Calls _fwd_kernel_stage2_asm Triton kernel to reduce splits
"""

import torch
from aiter.mla import mla_decode_fwd
from task import input_t, output_t


NUM_HEADS = 16
NUM_KV_HEADS = 1
QK_HEAD_DIM = 576
V_HEAD_DIM = 512
SM_SCALE = 1.0 / (QK_HEAD_DIM**0.5)
PAGE_SIZE = 1

# Einsum is faster for small total KV (proven optimal across many experiments)
EINSUM_MAX_TOTAL_KV = 32768

_cache: dict = {}


def _choose_num_kv_splits(bs: int, total_kv: int) -> int:
    """Pick num_kv_splits for non-persistent BF16 decode.

    For the non-persistent path the heuristic from aiter.mla.get_meta_param is
    appropriate but we call it directly to avoid the lru_cache dtype interaction.
    Simpler table suffices for the test shapes.
    """
    if total_kv <= 4096:
        return 1
    if total_kv <= 16384:
        return 2
    if total_kv <= 65536:
        return 4
    if total_kv <= 262144:
        return 8
    if total_kv <= 524288:
        return 16
    return 32


def _einsum_attention(data: input_t) -> output_t:
    """Flash-equivalent via batched einsum — fastest for small KV sequences."""
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    kv = kv_data["bf16"].view(bs, kvseqlen, QK_HEAD_DIM)
    qr = q.view(bs, 1, NUM_HEADS, QK_HEAD_DIM)
    scores = torch.einsum("bqnh,bsh->bnqs", qr, kv).mul_(SM_SCALE)
    weights = torch.softmax(scores, dim=-1)
    v = kv[:, :, :V_HEAD_DIM]
    return (
        torch.einsum("bnqs,bsd->bqnd", weights, v)
        .reshape(-1, NUM_HEADS, V_HEAD_DIM)
        .to(torch.bfloat16)
    )


def _build_nonpersistent_cache(
    bs: int,
    qseqlen: int,
    kvseqlen: int,
    kv_indptr: torch.Tensor,
    num_kv_splits: int,
) -> dict:
    """Pre-allocate output and metadata for non-persistent BF16 decode.

    Non-persistent mode: pass num_kv_splits_indptr directly to stage1 ASM.
    This makes persistent=False in asm_mla.cu, forcing ps=0 in kernel selection,
    which dispatches mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co.
    """
    key = ("dec_bf16_nonpersist", bs, qseqlen, kvseqlen, num_kv_splits)
    if key in _cache:
        return _cache[key]

    total_q = bs * qseqlen
    total_kv_len = int(kv_indptr[-1].item())

    # num_kv_splits_indptr: uniform split assignment [0, N, 2N, ..., bs*N]
    num_kv_splits_indptr = torch.arange(
        0,
        (bs + 1) * num_kv_splits,
        num_kv_splits,
        dtype=torch.int32,
        device="cuda",
    )

    meta = {
        "kv_indices": torch.arange(total_kv_len, dtype=torch.int32, device="cuda"),
        "kv_last_page_len": (kv_indptr[1:] - kv_indptr[:-1]).to(torch.int32),
        "num_kv_splits_indptr": num_kv_splits_indptr,
        "output": torch.empty(
            (total_q, NUM_HEADS, V_HEAD_DIM),
            dtype=torch.bfloat16,
            device="cuda",
        ),
    }
    _cache[key] = meta
    return meta


def _dec_bf16_attention(data: input_t) -> output_t:
    """Non-persistent BF16 decode: triggers mla_dec_stage1_bf16_a16w16_subQ16_mqa16.co.

    Key differences from submission_bf16_only.py / submission_a16w16.py:
    - Does NOT pass work_meta_data (stays non-persistent, ps=0)
    - Passes num_kv_splits_indptr directly as 7th arg to mla_decode_stage1_asm_fwd
    - max_seqlen_q=1 + ps=0 + gqa_ratio=16 + bf16/bf16 -> decode kernel row in CSV
    """
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    qseqlen = config["q_seq_len"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    kv_bf16 = kv_data["bf16"]
    num_kv_splits = _choose_num_kv_splits(bs, total_kv)

    # 4D view: (total_kv, page_size=1, nhead_kv=1, dim=576)
    kv_4d = kv_bf16.view(kv_bf16.shape[0], PAGE_SIZE, NUM_KV_HEADS, QK_HEAD_DIM)

    meta = _build_nonpersistent_cache(bs, qseqlen, kvseqlen, kv_indptr, num_kv_splits)
    output = meta["output"]

    # Call mla_decode_fwd WITHOUT work_meta_data (non-persistent mode).
    # Pass num_kv_splits and num_kv_splits_indptr explicitly so the function
    # skips get_meta_param and goes directly to mla_decode_stage1_asm_fwd with
    # num_kv_splits_indptr (not None) -> persistent=False in C++ -> ps=0.
    mla_decode_fwd(
        q.view(-1, NUM_HEADS, QK_HEAD_DIM),
        kv_4d,
        output,
        qo_indptr,
        kv_indptr,
        meta["kv_indices"],
        meta["kv_last_page_len"],
        qseqlen,
        page_size=PAGE_SIZE,
        nhead_kv=NUM_KV_HEADS,
        sm_scale=SM_SCALE,
        logit_cap=0.0,
        num_kv_splits=num_kv_splits,
        num_kv_splits_indptr=meta["num_kv_splits_indptr"],
        # work_meta_data=None (default) — keeps non-persistent mode
        # work_indptr=None (default)
        # work_info_set=None (default)
        q_scale=None,
        kv_scale=None,
        intra_batch_mode=False,
    )
    return output


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data
    bs = config["batch_size"]
    kvseqlen = config["kv_seq_len"]
    total_kv = bs * kvseqlen

    if total_kv <= EINSUM_MAX_TOTAL_KV:
        return _einsum_attention(data)

    return _dec_bf16_attention(data)
