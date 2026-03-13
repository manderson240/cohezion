"""
MXFP4 MoE — Introspection: cktile stage function signatures.

Goal: Discover cktile_moe_stage1 and cktile_moe_stage2 function signatures,
the moe_sorting_fwd output format, and how fused_moe constructs the stage calls.
This is needed for Task #16 (direct CK stage kernel calls).
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
            from aiter import fused_moe as fmoe_module

            # 1. Find cktile-related functions and their signatures
            print("\n=== cktile functions ===", file=sys.stderr)
            for name in sorted(dir(fmoe_module)):
                if 'cktile' in name.lower() or 'stage' in name.lower():
                    obj = getattr(fmoe_module, name)
                    if callable(obj):
                        try:
                            sig = inspect.signature(obj)
                            print(f"{name}{sig}", file=sys.stderr)
                        except (ValueError, TypeError):
                            print(f"{name}(<signature unavailable>)", file=sys.stderr)

            # 2. Find moe_sorting function signatures
            print("\n=== moe_sorting functions ===", file=sys.stderr)
            for name in sorted(dir(fmoe_module)):
                if 'sorting' in name.lower():
                    obj = getattr(fmoe_module, name)
                    if callable(obj):
                        try:
                            sig = inspect.signature(obj)
                            print(f"{name}{sig}", file=sys.stderr)
                        except (ValueError, TypeError):
                            print(f"{name}(<signature unavailable>)", file=sys.stderr)

            # 3. Get the fused_moe source — focus on the cktile dispatch branch
            print("\n=== fused_moe cktile dispatch code ===", file=sys.stderr)
            try:
                from aiter.fused_moe import fused_moe
                src = inspect.getsource(fused_moe)
                lines = src.split('\n')
                # Find cktile-related blocks
                in_cktile_block = False
                for i, line in enumerate(lines):
                    ll = line.lower()
                    if 'cktile' in ll or in_cktile_block:
                        in_cktile_block = True
                        print(f"L{i}: {line.rstrip()}", file=sys.stderr)
                        # End block after 2 blank lines
                        if line.strip() == '' and i > 0 and lines[i-1].strip() == '':
                            in_cktile_block = False
            except Exception as e:
                print(f"fused_moe source error: {e}", file=sys.stderr)

            # 4. Get get_2stage_cfgs — the full heuristic path
            print("\n=== get_2stage_cfgs (heuristic, ksplit branch) ===", file=sys.stderr)
            try:
                from aiter.fused_moe import get_2stage_cfgs
                src = inspect.getsource(get_2stage_cfgs)
                lines = src.split('\n')
                in_block = False
                for i, line in enumerate(lines):
                    ll = line.lower()
                    if 'ksplit' in ll or 'block_m' in ll or 'use_nt' in ll or in_block:
                        in_block = True
                        print(f"L{i}: {line.rstrip()}", file=sys.stderr)
                        if in_block and line.strip() == '' and i > 0:
                            in_block = False
            except Exception as e:
                print(f"get_2stage_cfgs error: {e}", file=sys.stderr)

            # 5. Try to find AITER_BLOCK_M or similar env vars
            print("\n=== all AITER env var patterns ===", file=sys.stderr)
            try:
                full_src = inspect.getsource(fmoe_module)
                for i, line in enumerate(full_src.split('\n')):
                    if 'AITER_' in line:
                        print(f"L{i}: {line.rstrip()}", file=sys.stderr)
            except Exception as e:
                print(f"env scan error: {e}", file=sys.stderr)

        except Exception as e:
            print(f"PROBE ERROR: {e}", file=sys.stderr)

    return ref_kernel(data)
