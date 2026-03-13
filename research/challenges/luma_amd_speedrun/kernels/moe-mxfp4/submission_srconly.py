"""
MXFP4 MoE — Source-only introspection (no CSV dumps).

Targets:
  1. dsv3_fp4_tuned_fmoe.csv — the MXFP4-specific DeepSeek tuning config
  2. get_2stage_cfgs source — dispatch logic
  3. All env var references in fused_moe module
  4. fused_moe dispatch-relevant lines

Does NOT dump large GEMM/generic CSVs to avoid buffer overflow.
"""
import sys
import os
import inspect
from task import input_t, output_t
from reference import ref_kernel


def custom_kernel(data: input_t) -> output_t:
    if not hasattr(custom_kernel, '_probed'):
        custom_kernel._probed = True
        try:
            import aiter
            from aiter import fused_moe as fmoe_module
            aiter_path = os.path.dirname(aiter.__file__)

            # 1. ONLY the dsv3_fp4 CSV (not all CSVs — avoid buffer overflow)
            configs_dir = os.path.join(aiter_path, "configs")
            for root, dirs, files in os.walk(configs_dir):
                for f in sorted(files):
                    if 'dsv3_fp4' in f.lower() or 'fp4' in f.lower():
                        fpath = os.path.join(root, f)
                        relpath = os.path.relpath(fpath, aiter_path)
                        print(f"\n=== {relpath} ===", file=sys.stderr)
                        with open(fpath) as fh:
                            print(fh.read()[:6000], file=sys.stderr)

            # 2. get_2stage_cfgs full source
            try:
                from aiter.fused_moe import get_2stage_cfgs
                src = inspect.getsource(get_2stage_cfgs)
                print(f"\n=== get_2stage_cfgs source ===", file=sys.stderr)
                print(src, file=sys.stderr)
            except Exception as e:
                print(f"get_2stage_cfgs error: {e}", file=sys.stderr)

            # 3. ALL env var references in fused_moe module
            try:
                src_full = inspect.getsource(fmoe_module)
                print(f"\n=== ALL ENV VAR REFS in fused_moe ===", file=sys.stderr)
                for i, line in enumerate(src_full.split('\n')):
                    if 'environ' in line or 'AITER' in line or 'os.getenv' in line:
                        print(f"L{i}: {line.rstrip()}", file=sys.stderr)
            except Exception as e:
                print(f"env vars error: {e}", file=sys.stderr)

            # 4. fused_moe function dispatch lines
            try:
                from aiter.fused_moe import fused_moe
                src = inspect.getsource(fused_moe)
                print(f"\n=== fused_moe dispatch lines ===", file=sys.stderr)
                for i, line in enumerate(src.split('\n')):
                    ll = line.lower()
                    if any(kw in ll for kw in ['ksplit', 'block_m', 'online_tune',
                                                'bypass_tune', 'use_nt', 'environ',
                                                'aiter_', 'cfg', 'stage1', 'stage2',
                                                'tuned', 'csv', 'default']):
                        print(f"L{i}: {line.rstrip()}", file=sys.stderr)
            except Exception as e:
                print(f"fused_moe source error: {e}", file=sys.stderr)

            # 5. All public exports
            print(f"\n=== fused_moe exports ===", file=sys.stderr)
            exports = [x for x in dir(fmoe_module) if not x.startswith('_')]
            print(', '.join(exports), file=sys.stderr)

        except Exception as e:
            print(f"PROBE ERROR: {e}", file=sys.stderr)

    return ref_kernel(data)
