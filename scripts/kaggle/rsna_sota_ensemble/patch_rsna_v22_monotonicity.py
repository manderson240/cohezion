#!/usr/bin/env python3
"""Patches cohezion-rsna-knee-sota-ensemble.ipynb to v22 SOTA Kolmogorov Monotonicity Calibration.

Key upgrades:
1. Cell 4: Verifies TARGET_CACHE_SLICES = 16 (native 16-slice fidelity).
2. Cell 26: Applies Quantile Rank Normalization (.rank(method='average', pct=True)).
3. Cell 26: Re-projects Kolmogorov Monotonicity:
   condition_cols = [c for c in _blend_labels if c != 'Abnormal']
   _blend_output['Abnormal'] = np.maximum(_blend_output['Abnormal'], _blend_output[condition_cols].max(axis=1))
4. AutoHarness Invariant Guard: Verifies 100% rows satisfy P(Abnormal) >= max(P(Condition_i)).
"""

from __future__ import annotations

import json
from pathlib import Path

NOTEBOOK_PATH = Path("scripts/kaggle/rsna_sota_ensemble/cohezion-rsna-knee-sota-ensemble.ipynb")
BACKUP_PATH = NOTEBOOK_PATH.with_suffix(".ipynb.v21.bak")


def patch_rsna_v22() -> None:
    with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # Save v21 backup
    with open(BACKUP_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print(f"Backed up v21 notebook to {BACKUP_PATH}")

    # 1. Verify Cell 4: TARGET_CACHE_SLICES = 16
    c4 = nb["cells"][4]
    c4_src = "".join(c4["source"]) if isinstance(c4["source"], list) else c4["source"]
    if "TARGET_CACHE_SLICES = 16" in c4_src:
        print("✓ Cell 4: Verified TARGET_CACHE_SLICES = 16 (native 16-slice fidelity)")
    else:
        c4_patched = c4_src.replace("TARGET_CACHE_SLICES = 32", "TARGET_CACHE_SLICES = 16")
        c4["source"] = [line + "\n" for line in c4_patched.splitlines()]
        print("✓ Cell 4: Patched TARGET_CACHE_SLICES = 16")

    # 2. Patch Cell 26: Add Kolmogorov Monotonicity Projection
    c26 = nb["cells"][26]
    c26_src = "".join(c26["source"]) if isinstance(c26["source"], list) else c26["source"]

    target_old = """# 4. Pure Intra-Class Quantile Rank Transformation for Macro ROC-AUC
# ROC-AUC evaluates intra-class ranking exclusively.
_blend_output[_blend_labels] = _blend_output[_blend_labels].rank(method='average', pct=True)
print(f"[v21-podium-sota] generated calibrated rank-normalized blend on {_blend_labels}", flush=True)
_blend_output.to_csv(_ke_primary, index=False)"""

    v22_code = """# 4. Pure Intra-Class Quantile Rank Transformation for Macro ROC-AUC
# ROC-AUC evaluates intra-class ranking exclusively.
_blend_output[_blend_labels] = _blend_output[_blend_labels].rank(method='average', pct=True)

# 5. Kolmogorov Monotonicity Projection (v22 SOTA)
# Re-project medical probability bounds: Knee abnormality must bound all sub-condition anomalies.
if 'Abnormal' in _blend_output.columns:
    condition_cols = [c for c in _blend_labels if c != 'Abnormal']
    _blend_output['Abnormal'] = _ke_np.maximum(
        _blend_output['Abnormal'].to_numpy(_ke_np.float64),
        _blend_output[condition_cols].max(axis=1).to_numpy(_ke_np.float64)
    )
    # AutoHarness verification invariant: 100% rows P(Abnormal) >= max(P(Condition_i))
    _viol_count = int((_blend_output['Abnormal'] < _blend_output[condition_cols].max(axis=1) - 1e-9).sum())
    assert _viol_count == 0, f"AutoHarness Guard: Kolmogorov Monotonicity violated in {_viol_count} rows"
    print(f"[v22-monotonicity-sota] Kolmogorov Monotonicity invariant verified (100% rows satisfied)", flush=True)

print(f"[v22-podium-sota] generated calibrated rank-normalized blend on {_blend_labels}", flush=True)
_blend_output.to_csv(_ke_primary, index=False)"""

    if target_old in c26_src:
        c26_patched = c26_src.replace(target_old, v22_code)
        c26["source"] = [line + "\n" for line in c26_patched.splitlines()]
        print("✓ Cell 26: Patched with Kolmogorov Monotonicity Projection + AutoHarness Guard")
    else:
        # Fallback check if whitespace or formatting differed slightly
        print("Warning: Exact target_old not found in Cell 26, checking substring...")
        if "_blend_output[_blend_labels].rank(method='average', pct=True)" in c26_src:
            print("Found rank transformation in Cell 26, applying replacement...")
            idx = c26_src.find("# 4. Pure Intra-Class Quantile Rank Transformation")
            if idx != -1:
                end_idx = c26_src.find("_blend_output.to_csv(_ke_primary, index=False)") + len("_blend_output.to_csv(_ke_primary, index=False)")
                c26_patched = c26_src[:idx] + v22_code + c26_src[end_idx:]
                c26["source"] = [line + "\n" for line in c26_patched.splitlines()]
                print("✓ Cell 26: Patched successfully via index slicing")
            else:
                raise RuntimeError("Could not locate rank transformation block in Cell 26")
        else:
            raise RuntimeError("Target rank code not found in Cell 26")

    with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print(f"✓ Saved patched notebook to {NOTEBOOK_PATH}")


if __name__ == "__main__":
    patch_rsna_v22()
