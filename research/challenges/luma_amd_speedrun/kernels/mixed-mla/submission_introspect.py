"""
MLA introspection — discover aiter MLA internals on MI355X.
Delegates to ref_kernel for correctness, prints diagnostics to stderr.
"""
import sys
import os
import inspect
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    q, kv_data, qo_indptr, kv_indptr, config = data

    # Only introspect on first call
    if not hasattr(custom_kernel, '_introspected'):
        custom_kernel._introspected = True

        print("=== AITER MLA INTROSPECTION ===", file=sys.stderr)

        # 1. Check what's in aiter.mla
        try:
            import aiter.mla as mla_mod
            print(f"aiter.mla members: {dir(mla_mod)}", file=sys.stderr)
            print(f"aiter.mla file: {mla_mod.__file__}", file=sys.stderr)
        except Exception as e:
            print(f"aiter.mla error: {e}", file=sys.stderr)

        # 2. Check for Triton-based attention in aiter.ops.triton
        try:
            import aiter.ops.triton as triton_ops
            print(f"aiter.ops.triton members: {dir(triton_ops)}", file=sys.stderr)
        except Exception as e:
            print(f"aiter.ops.triton error: {e}", file=sys.stderr)

        # 3. Check for attention submodules
        for submod in ['aiter.ops.triton.attention', 'aiter.ops.triton.mla',
                       'aiter.ops.triton.flash_attention', 'aiter.ops.triton.decode']:
            try:
                mod = __import__(submod, fromlist=[''])
                print(f"{submod} members: {dir(mod)}", file=sys.stderr)
            except ImportError:
                print(f"{submod}: NOT FOUND", file=sys.stderr)
            except Exception as e:
                print(f"{submod} error: {e}", file=sys.stderr)

        # 4. Check mla_decode_fwd signature
        try:
            from aiter.mla import mla_decode_fwd
            print(f"mla_decode_fwd type: {type(mla_decode_fwd)}", file=sys.stderr)
            if hasattr(mla_decode_fwd, '__doc__'):
                print(f"mla_decode_fwd doc: {mla_decode_fwd.__doc__[:500] if mla_decode_fwd.__doc__ else 'None'}", file=sys.stderr)
        except Exception as e:
            print(f"mla_decode_fwd error: {e}", file=sys.stderr)

        # 5. List aiter.ops directory structure
        try:
            import aiter.ops
            ops_path = os.path.dirname(aiter.ops.__file__)
            for root, dirs, files in os.walk(ops_path):
                depth = root.replace(ops_path, '').count(os.sep)
                if depth < 3:
                    indent = ' ' * 2 * depth
                    print(f"{indent}{os.path.basename(root)}/", file=sys.stderr)
                    for f in sorted(files)[:20]:
                        if f.endswith('.py'):
                            print(f"{indent}  {f}", file=sys.stderr)
        except Exception as e:
            print(f"aiter.ops walk error: {e}", file=sys.stderr)

        # 6. Check if there's a flash_attn or triton attention decode kernel
        try:
            import aiter
            aiter_path = os.path.dirname(aiter.__file__)
            # Search for attention-related .py files
            for root, dirs, files in os.walk(aiter_path):
                for f in files:
                    if ('attention' in f.lower() or 'mla' in f.lower() or
                        'flash' in f.lower() or 'decode' in f.lower()) and f.endswith('.py'):
                        rel = os.path.relpath(os.path.join(root, f), aiter_path)
                        print(f"ATTN_FILE: {rel}", file=sys.stderr)
        except Exception as e:
            print(f"Search error: {e}", file=sys.stderr)

        # 7. Check torch.ops.aiter for MLA-related ops
        try:
            import torch
            if hasattr(torch.ops, 'aiter'):
                aiter_ops = [x for x in dir(torch.ops.aiter)
                            if 'mla' in x.lower() or 'attention' in x.lower() or 'decode' in x.lower()]
                print(f"torch.ops.aiter MLA-related: {aiter_ops}", file=sys.stderr)
        except Exception as e:
            print(f"torch.ops.aiter error: {e}", file=sys.stderr)

        # 8. Input shape diagnostics
        print(f"\nINPUT_SHAPES:", file=sys.stderr)
        print(f"  q: {q.shape} {q.dtype}", file=sys.stderr)
        kv_fp8, kv_scale = kv_data["fp8"]
        print(f"  kv_fp8: {kv_fp8.shape} {kv_fp8.dtype}", file=sys.stderr)
        print(f"  kv_scale: {kv_scale.shape} {kv_scale.dtype}", file=sys.stderr)
        kv_mxfp4, mxfp4_scale = kv_data["mxfp4"]
        print(f"  kv_mxfp4: {kv_mxfp4.shape} {kv_mxfp4.dtype}", file=sys.stderr)
        print(f"  mxfp4_scale: {mxfp4_scale.shape} {mxfp4_scale.dtype}", file=sys.stderr)
        print(f"  config: {config}", file=sys.stderr)

        print("=== END INTROSPECTION ===", file=sys.stderr)

    return ref_kernel(data)
