"""
Lean probe: pa_ps_fwd_asm + flash_attn_varlen_func source code only.
No call attempts — just dump signatures and source to learn the API.
"""
from __future__ import annotations

import inspect
import sys

from reference import ref_kernel
from task import input_t, output_t


_probed = False

def custom_kernel(data: input_t) -> output_t:
    global _probed
    if not _probed:
        _probed = True
        import aiter

        # 1. pa_ps_fwd_asm
        for name in ["pa_ps_fwd_asm", "gen_pa_ps_fwd_asm", "pa_persistent_fwd", "pa_fwd_asm"]:
            fn = getattr(aiter, name, None)
            if fn:
                try:
                    src = inspect.getsource(fn)
                    print(f"\n=== {name} ({len(src)}c) ===\n{src[:2500]}", file=sys.stderr)
                except Exception as e:
                    print(f"{name} src err: {e}", file=sys.stderr)

        # 2. flash_attn_varlen_func
        for name in ["flash_attn_varlen_func", "fmha_v3_varlen_fwd"]:
            fn = getattr(aiter, name, None)
            if fn:
                try:
                    src = inspect.getsource(fn)
                    print(f"\n=== {name} ({len(src)}c) ===\n{src[:2500]}", file=sys.stderr)
                except Exception as e:
                    print(f"{name} src err: {e}", file=sys.stderr)

        # 3. pa_decode_gluon
        fn = getattr(aiter, "pa_decode_gluon", None)
        if fn:
            try:
                src = inspect.getsource(fn)
                print(f"\n=== pa_decode_gluon ({len(src)}c) ===\n{src[:2000]}", file=sys.stderr)
            except Exception as e:
                print(f"pa_decode_gluon src err: {e}", file=sys.stderr)

    return ref_kernel(data)
