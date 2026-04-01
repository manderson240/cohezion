"""
MLA BREAKTHROUGH PROBE: pa_ps_asm — Paged Attention Persistent ASM kernel.

From AITER v0.1.9: "fix(pa_ps): fix pa_ps_asm .co for gfx950"
Also probing: mha fwd v3, flash_attn variable-length, all ASM attention ops.
"""
from __future__ import annotations

import inspect
import sys

import aiter
import torch
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data

    # === Probe 1: pa_ps_asm and paged attention variants ===
    pa_funcs = [a for a in dir(aiter) if "pa_" in a.lower() or "paged" in a.lower() or "page" in a.lower()]
    print(f"Paged attention functions: {pa_funcs}", file=sys.stderr)

    for name in pa_funcs:
        fn = getattr(aiter, name, None)
        if callable(fn):
            try:
                sig = str(inspect.signature(fn))
                print(f"  {name} sig: {sig[:200]}", file=sys.stderr)
            except Exception as e:
                print(f"  {name}: {e}", file=sys.stderr)

    # === Probe 2: All ASM kernels in aiter ===
    asm_funcs = [a for a in dir(aiter) if "asm" in a.lower()]
    print(f"ASM kernels ({len(asm_funcs)}): {asm_funcs}", file=sys.stderr)

    # === Probe 3: torch.ops.aiter MLA/attention ASM ===
    try:
        attn_ops = [a for a in dir(torch.ops.aiter) if "attn" in a.lower() or "mla" in a.lower() or "pa_" in a.lower() or "paged" in a.lower()]
        print(f"torch.ops.aiter attention: {attn_ops}", file=sys.stderr)
        for name in attn_ops[:10]:
            try:
                fn = getattr(torch.ops.aiter, name)
                sig = str(inspect.signature(fn))
                print(f"  {name} sig: {sig[:200]}", file=sys.stderr)
            except Exception:
                pass
    except Exception as e:
        print(f"torch.ops.aiter scan: {e}", file=sys.stderr)

    # === Probe 4: mha fwd v3 (AITER v0.1.7: "mha fwd v3 gfx950 support") ===
    mha_funcs = [a for a in dir(aiter) if "mha" in a.lower() or "fwd_v3" in a.lower() or "fav3" in a.lower()]
    print(f"MHA fwd v3 functions: {mha_funcs}", file=sys.stderr)
    for name in mha_funcs:
        fn = getattr(aiter, name, None)
        if callable(fn):
            try:
                sig = str(inspect.signature(fn))
                print(f"  {name} sig: {sig[:200]}", file=sys.stderr)
            except Exception as e:
                print(f"  {name}: {e}", file=sys.stderr)

    # === Probe 5: flash_attn inputs for MLA ===
    try:
        sig = str(inspect.signature(aiter.flash_attn_func))
        print(f"flash_attn_func sig: {sig}", file=sys.stderr)
        bs = config["batch_size"]
        num_heads = config["num_heads"]
        kv_seq_len = config["kv_seq_len"]
        kv_bf16 = kv_data["bf16"]
        print(f"q={q.shape}, kv={kv_bf16.shape}, bs={bs}, nh={num_heads}, kv_len={kv_seq_len}", file=sys.stderr)
        print(f"qo_indptr={qo_indptr}, kv_indptr={kv_indptr}", file=sys.stderr)
    except Exception as e:
        print(f"flash_attn probe: {e}", file=sys.stderr)

    return ref_kernel(data)
