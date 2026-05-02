"""MLA Probe: Dump runner state for MLA decode optimization paths."""

from __future__ import annotations

import inspect
import sys

from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    # === 1. aiter MLA APIs ===
    try:
        import aiter

        print(f"aiter version: {aiter.__version__}", file=sys.stderr)
        mla_attrs = [
            a
            for a in dir(aiter)
            if "mla" in a.lower() or "attention" in a.lower() or "flash" in a.lower()
        ]
        print(f"MLA/attention attrs: {mla_attrs}", file=sys.stderr)
    except Exception as e:
        print(f"aiter scan error: {e}", file=sys.stderr)

    # === 2. mla_decode_fwd source ===
    try:
        src = inspect.getsource(aiter.mla_decode_fwd)
        print(f"mla_decode_fwd source ({len(src)} chars):\n{src[:1500]}", file=sys.stderr)
    except Exception as e:
        print(f"mla_decode_fwd source error: {e}", file=sys.stderr)

    # === 3. Check torch.ops.aiter for hidden attention ops ===
    try:
        import torch

        aiter_ops = [a for a in dir(torch.ops.aiter) if not a.startswith("_")]
        attn_ops = [
            a
            for a in aiter_ops
            if "attn" in a.lower()
            or "mla" in a.lower()
            or "flash" in a.lower()
            or "decode" in a.lower()
        ]
        print(f"torch.ops.aiter attention ops ({len(attn_ops)}): {attn_ops}", file=sys.stderr)
        # Also check for paged attention
        paged = [a for a in aiter_ops if "paged" in a.lower()]
        print(f"paged attention ops: {paged}", file=sys.stderr)
    except Exception as e:
        print(f"torch.ops.aiter error: {e}", file=sys.stderr)

    # === 4. Check for FlashInfer or other attention libraries ===
    try:
        import flashinfer

        print(f"flashinfer available: {flashinfer.__version__}", file=sys.stderr)
    except ImportError:
        print("flashinfer: NOT AVAILABLE", file=sys.stderr)

    try:
        import flash_attn

        print(f"flash_attn available: {flash_attn.__version__}", file=sys.stderr)
    except ImportError:
        print("flash_attn: NOT AVAILABLE", file=sys.stderr)

    # === 5. Check for SDPA and scaled_dot_product_attention variants ===
    try:
        import torch

        sdpa_attrs = [a for a in dir(torch.nn.functional) if "attention" in a.lower()]
        print(f"F.attention funcs: {sdpa_attrs}", file=sys.stderr)
        # Check backends
        backends = [a for a in dir(torch.backends) if not a.startswith("_")]
        print(f"torch.backends: {backends}", file=sys.stderr)
    except Exception as e:
        print(f"SDPA check error: {e}", file=sys.stderr)

    # === 6. Reference kernel shape analysis ===
    try:
        q, kv_data, qo_indptr, kv_indptr, config = data
        print(f"q shape: {q.shape}, dtype: {q.dtype}", file=sys.stderr)
        print(f"qo_indptr: {qo_indptr}", file=sys.stderr)
        print(f"kv_indptr: {kv_indptr}", file=sys.stderr)
        print(f"config: {config}", file=sys.stderr)
        for key, val in kv_data.items():
            if isinstance(val, tuple):
                print(
                    f"kv_data['{key}']: tuple of {len(val)}, shapes={[v.shape for v in val if hasattr(v, 'shape')]}",
                    file=sys.stderr,
                )
            elif hasattr(val, "shape"):
                print(f"kv_data['{key}']: {val.shape} {val.dtype}", file=sys.stderr)
    except Exception as e:
        print(f"shape analysis error: {e}", file=sys.stderr)

    # Run reference for correctness
    return ref_kernel(data)
