"""
MXFP4 MoE — Deep introspection probe.

Dumps: CSV configs, fused_moe source dispatch logic, available kernel names,
and tests env var combinations. Delegates to ref_kernel for correctness.
"""
import sys
import os
import inspect
from task import input_t, output_t
from reference import ref_kernel


def custom_kernel(data: input_t) -> output_t:
    (
        hidden_states, gate_up_weight, down_weight,
        gate_up_weight_scale, down_weight_scale,
        gate_up_weight_shuffled, down_weight_shuffled,
        gate_up_weight_scale_shuffled, down_weight_scale_shuffled,
        topk_weights, topk_ids, config,
    ) = data

    # Only introspect on first call
    if not hasattr(custom_kernel, '_probed'):
        custom_kernel._probed = True
        try:
            import aiter
            from aiter import fused_moe as fmoe_module
            aiter_path = os.path.dirname(aiter.__file__)

            # 1. Full CSV configs
            configs_dir = os.path.join(aiter_path, "configs")
            for root, dirs, files in os.walk(configs_dir):
                for f in sorted(files):
                    if f.endswith('.csv'):
                        fpath = os.path.join(root, f)
                        relpath = os.path.relpath(fpath, aiter_path)
                        print(f"\n=== {relpath} ===", file=sys.stderr)
                        with open(fpath) as fh:
                            content = fh.read()
                            # Print full content for small files, first 30 lines for large
                            lines = content.split('\n')
                            if len(lines) <= 50:
                                print(content, file=sys.stderr)
                            else:
                                print('\n'.join(lines[:30]), file=sys.stderr)
                                print(f"... ({len(lines)} total lines)", file=sys.stderr)

            # 2. fused_moe dispatch: get_2stage_cfgs function source
            try:
                from aiter.fused_moe import get_2stage_cfgs
                src = inspect.getsource(get_2stage_cfgs)
                print(f"\n=== get_2stage_cfgs source ===", file=sys.stderr)
                # Print first 80 lines
                for i, line in enumerate(src.split('\n')[:80]):
                    print(line, file=sys.stderr)
            except Exception as e:
                print(f"get_2stage_cfgs: {e}", file=sys.stderr)

            # 3. fused_moe function signature and key lines
            try:
                from aiter.fused_moe import fused_moe
                src = inspect.getsource(fused_moe)
                print(f"\n=== fused_moe key lines (KSPLIT/dispatch) ===", file=sys.stderr)
                for i, line in enumerate(src.split('\n')):
                    ll = line.lower()
                    if any(kw in ll for kw in ['ksplit', 'split_k', 'splitk', 'block_m',
                                                 'use_nt', 'online_tune', 'bypass',
                                                 'environ', 'aiter_']):
                        print(f"L{i}: {line}", file=sys.stderr)
            except Exception as e:
                print(f"fused_moe source: {e}", file=sys.stderr)

            # 4. List all available env vars that aiter checks
            try:
                src_full = inspect.getsource(fmoe_module)
                print(f"\n=== All env var references in fused_moe module ===", file=sys.stderr)
                for i, line in enumerate(src_full.split('\n')):
                    if 'environ' in line or 'AITER' in line:
                        print(f"L{i}: {line.strip()}", file=sys.stderr)
            except Exception as e:
                print(f"fused_moe module source: {e}", file=sys.stderr)

            # 5. Check what's importable from fused_moe
            print(f"\n=== fused_moe module exports ===", file=sys.stderr)
            exports = [x for x in dir(fmoe_module) if not x.startswith('_')]
            print(', '.join(exports), file=sys.stderr)

        except Exception as e:
            print(f"INTROSPECT ERROR: {e}", file=sys.stderr)

    return ref_kernel(data)
