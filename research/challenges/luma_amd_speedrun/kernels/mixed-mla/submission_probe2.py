"""
MLA probe 2 — inspect fav3_sage_attention_mxfp4 and decode_mla APIs.
"""
import sys
import os
import inspect
import importlib
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    if not hasattr(custom_kernel, '_probed'):
        custom_kernel._probed = True

        # 1. fav3_sage_attention_mxfp4_wrapper
        print("=== FAV3 SAGE MXFP4 WRAPPER ===", file=sys.stderr)
        try:
            fav3_mod = importlib.import_module('aiter.ops.triton.attention.fav3_sage_attention_mxfp4_wrapper')
            print(f"Members: {[x for x in dir(fav3_mod) if not x.startswith('_')]}", file=sys.stderr)
            for name in dir(fav3_mod):
                obj = getattr(fav3_mod, name)
                if callable(obj) and not name.startswith('_'):
                    try:
                        sig = inspect.signature(obj)
                        print(f"  {name}{sig}", file=sys.stderr)
                    except (ValueError, TypeError):
                        print(f"  {name} (no signature)", file=sys.stderr)
        except Exception as e:
            print(f"fav3 wrapper error: {type(e).__name__}: {e}", file=sys.stderr)

        # 2. Read fav3 wrapper source (first 120 lines)
        print("\n=== FAV3 WRAPPER SOURCE ===", file=sys.stderr)
        try:
            fav3w = importlib.import_module('aiter.ops.triton.attention.fav3_sage_attention_mxfp4_wrapper')
            with open(fav3w.__file__) as f:
                for i, line in enumerate(f):
                    if i < 120:
                        print(line.rstrip(), file=sys.stderr)
        except Exception as e:
            print(f"Source read error: {e}", file=sys.stderr)

        # 3. AOT Triton decode_mla source (first 80 lines)
        print("\n=== DECODE_MLA SOURCE ===", file=sys.stderr)
        try:
            dm = importlib.import_module('aiter.aot.triton.decode_mla')
            with open(dm.__file__) as f:
                for i, line in enumerate(f):
                    if i < 80:
                        print(line.rstrip(), file=sys.stderr)
        except Exception as e:
            print(f"decode_mla error: {type(e).__name__}: {e}", file=sys.stderr)

        # 4. pa_decode source (first 60 lines)
        print("\n=== PA_DECODE SOURCE ===", file=sys.stderr)
        try:
            pa = importlib.import_module('aiter.ops.triton.attention.pa_decode')
            members = [x for x in dir(pa) if not x.startswith('_')]
            print(f"Members: {members}", file=sys.stderr)
            for name in members:
                obj = getattr(pa, name)
                if callable(obj) and not name.startswith('_'):
                    try:
                        sig = inspect.signature(obj)
                        print(f"  {name}{sig}", file=sys.stderr)
                    except (ValueError, TypeError):
                        print(f"  {name} (no signature)", file=sys.stderr)
        except Exception as e:
            print(f"pa_decode error: {type(e).__name__}: {e}", file=sys.stderr)

        # 5. mla.py source — look at mla_decode_fwd implementation
        print("\n=== MLA.PY DECODE_FWD SOURCE ===", file=sys.stderr)
        try:
            import aiter.mla as mla_mod
            with open(mla_mod.__file__) as f:
                lines = f.readlines()
            # Find mla_decode_fwd function and print it
            in_func = False
            func_lines = 0
            for i, line in enumerate(lines):
                if 'def mla_decode_fwd' in line:
                    in_func = True
                if in_func:
                    print(f"{i+1}: {line.rstrip()}", file=sys.stderr)
                    func_lines += 1
                    if func_lines > 120:
                        break
        except Exception as e:
            print(f"mla.py read error: {e}", file=sys.stderr)

        print("\n=== END PROBE 2 ===", file=sys.stderr)

    return ref_kernel(data)
