"""MLA using mla_decode_fwd (non-ASM) with MXFP4 KV — v2 with updated API."""

import os
import sys

import torch
from task import input_t, output_t


os.environ["AITER_MLA_USE_PERSISTENT"] = "1"
os.environ["AITER_USE_NT"] = "1"

_probed = False
_o = {}


def custom_kernel(data: input_t) -> output_t:
    global _probed
    q, kd, qi, ki, cfg = data
    b, sl, nh = cfg["batch_size"], cfg["kv_seq_len"], cfg["num_heads"]

    if not _probed:
        _probed = True
        # Inspect the updated mla_decode_fwd signature
        try:
            import inspect

            from aiter.mla import mla_decode_fwd

            sig = inspect.signature(mla_decode_fwd)
            print(f"[PROBE] mla_decode_fwd signature: {sig}", file=sys.stderr)
        except Exception as e:
            print(f"[PROBE] mla_decode_fwd inspect failed: {e}", file=sys.stderr)

        # Also check for any other mla functions
        try:
            from aiter import mla

            for name in sorted(dir(mla)):
                if not name.startswith("_") and "decode" in name.lower():
                    print(f"[PROBE] aiter.mla.{name}", file=sys.stderr)
        except Exception as e:
            print(f"[PROBE] aiter.mla dir failed: {e}", file=sys.stderr)

    # Use MXFP4 KV
    kf, ks = kd["mxfp4"]
    k4 = kf.view(kf.shape[0], 1, 1, 288)

    # Compute kv_indices and kv_last_page_lens for the updated API
    kv_indices = torch.arange(b * sl, dtype=torch.int32, device="cuda")
    kv_last_page_lens = (ki[1:] - ki[:-1]).to(torch.int32)

    ok = (b * nh, 512)
    if ok not in _o:
        _o[ok] = torch.empty((b, nh, 512), dtype=torch.bfloat16, device="cuda")
    ot = _o[ok]

    ns = 16 if sl > 4096 else 8

    from aiter.mla import mla_decode_fwd

    return mla_decode_fwd(
        q,
        k4,
        ot,
        qi,
        ki,
        kv_indices,
        kv_last_page_lens,
        max_seqlen_q=1,
        page_size=1,
        nhead_kv=1,
        sm_scale=1.0 / (576**0.5),
        q_scale=None,
        kv_scale=ks,
        num_kv_splits=ns,
        intra_batch_mode=True,
    )
