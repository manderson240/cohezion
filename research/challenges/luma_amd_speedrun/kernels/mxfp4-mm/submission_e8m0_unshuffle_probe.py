"""Probe: Read e8m0_shuffle source + compute inverse mapping."""
import sys
import os
import inspect
import torch
from reference import ref_kernel
from task import input_t, output_t


def custom_kernel(data: input_t) -> output_t:
    A, B, B_q, B_shuffle, B_scale_sh = data

    try:
        from aiter.utility.fp4_utils import e8m0_shuffle
        from aiter.ops.triton.quant import dynamic_mxfp4_quant

        # 1. Read e8m0_shuffle source
        try:
            src = inspect.getsource(e8m0_shuffle)
            print(f"E8M0_SHUFFLE SOURCE ({len(src)} chars):", file=sys.stderr)
            for i, line in enumerate(src.splitlines()[:80]):
                print(f"  [{i}] {line}", file=sys.stderr)
        except Exception as e:
            print(f"SOURCE ERROR: {e}", file=sys.stderr)
            # Fallback: read the file directly
            fp4_path = inspect.getfile(e8m0_shuffle)
            print(f"FP4_UTILS PATH: {fp4_path}", file=sys.stderr)
            with open(fp4_path) as f:
                content = f.read()
            # Find e8m0_shuffle
            lines = content.splitlines()
            in_func = False
            for i, line in enumerate(lines):
                if 'def e8m0_shuffle' in line:
                    in_func = True
                if in_func:
                    print(f"  [{i}] {line}", file=sys.stderr)
                    if i > 0 and line.strip() and not line.startswith(' ') and not line.startswith('\t') and 'def e8m0_shuffle' not in line:
                        break

        # 2. Get ground truth B_scale and compare with B_scale_sh
        m, k = A.shape
        n = B.shape[0]
        _, B_scale = dynamic_mxfp4_quant(B.contiguous())
        B_scale_u8 = B_scale.view(torch.uint8)
        B_scale_sh_u8 = B_scale_sh.view(torch.uint8)

        print(f"\nB_scale shape: {B_scale_u8.shape}, B_scale_sh shape: {B_scale_sh_u8.shape}", file=sys.stderr)

        # 3. For each row in B_scale (un-shuffled), find its position in B_scale_sh
        # Using the values as fingerprints
        k_scale = B_scale_u8.shape[1]
        if k_scale >= 2:
            # Build index map: for row i of B_scale, find matching row in B_scale_sh
            found_count = 0
            mapping = []
            for i in range(min(n, 20)):  # Check first 20 rows
                row = B_scale_u8[i]
                for j in range(B_scale_sh_u8.shape[0]):
                    if torch.equal(row, B_scale_sh_u8[j]):
                        mapping.append((i, j))
                        found_count += 1
                        break
            print(f"Row mapping (first 20): {mapping}", file=sys.stderr)
            print(f"Found {found_count}/{min(n, 20)} matches", file=sys.stderr)

            # Check if the mapping is a simple arithmetic pattern
            if len(mapping) >= 4:
                diffs = [mapping[i+1][1] - mapping[i][1] for i in range(len(mapping)-1)]
                print(f"Consecutive diffs in shuffled index: {diffs}", file=sys.stderr)

        # 4. Also check: does e8m0_shuffle operate row-wise or globally?
        # Re-shuffle the truth scale and verify it matches B_scale_sh
        B_scale_reshuffled = e8m0_shuffle(B_scale.view(torch.float8_e8m0fnu))
        match = torch.equal(B_scale_reshuffled.view(torch.uint8), B_scale_sh_u8)
        print(f"\ne8m0_shuffle(truth) matches B_scale_sh: {match}", file=sys.stderr)

        # 5. Check if the shuffle is just a row permutation (no within-row reordering)
        if k_scale == 1:
            print("K_scale=1, shuffle can only be a row permutation", file=sys.stderr)
        else:
            # Check first row's internal ordering
            row0_truth = B_scale_u8[0].tolist()
            # Find where this row is in the shuffled tensor
            for j in range(B_scale_sh_u8.shape[0]):
                if torch.equal(B_scale_u8[0], B_scale_sh_u8[j]):
                    print(f"Row 0 found at shuffled position {j}", file=sys.stderr)
                    break
                if B_scale_u8[0, 0] == B_scale_sh_u8[j, 0]:
                    # Same first element, check if rest matches
                    match_pct = (B_scale_u8[0] == B_scale_sh_u8[j]).float().mean().item()
                    print(f"Row 0 partial match at {j}: {match_pct:.1%}", file=sys.stderr)

    except Exception as e:
        print(f"PROBE ERROR: {type(e).__name__}: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)

    return ref_kernel(data)
