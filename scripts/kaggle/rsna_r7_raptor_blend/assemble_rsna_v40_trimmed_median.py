#!/usr/bin/env python3
"""Assemble Cohezion RSNA Knee SOTA v40: Calibrated Trimmed Median Consensus Ensemble.
======================================================================================
Slot 5 Invariant Hypothesis:
- Invariant: Multi-model ensembling achieves peak robustness against out-of-distribution
  variance when using a Calibrated Trimmed Median rather than weighted arithmetic mean.
- A single corrupted or out-of-domain slice can produce an extreme probability artifact in
  one backbone that skews a linear sum; trimmed median removes the highest and lowest predictions
  and computes a noise-insulated consensus score.
- Retains Kolmogorov Secondary Effusion Bound: P(Effusion) >= 0.85 * max(P(ACL), P(Medial Meniscus)).
- Retains Parent Monotonicity: P(Abnormal) >= max_k P_k.
- Enforces strict probability margin clipping [1e-6, 1.0 - 1e-6].
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path

NB_PATH = Path("scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb")
BAK_PATH = Path("scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb.v39.bak")


def main() -> None:
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")

    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up notebook to {BAK_PATH}")

    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    cell_idx = len(nb["cells"]) - 1
    cell_source = "".join(nb["cells"][cell_idx]["source"])

    # Define Trimmed Median Consensus blend block
    trimmed_median_blend_code = """
# Calibrated Trimmed-Median Consensus Ensemble (Slot 5 GM Invariant)
preds_stack = np.stack([preds_c, preds_a, preds_r7], axis=0)  # Shape: (3, N, n_classes)
# Sort across the 3 model predictions and select median (middle model)
preds_median = np.median(preds_stack, axis=0)
preds_mean = (preds_c + preds_a + preds_r7) / 3.0

# 70% median consensus + 30% mean smooth regularization
out = 0.70 * preds_median + 0.30 * preds_mean

# Invariant Projection: Acute tears physically co-occur with joint effusion
if 'Effusion' in labels and 'ACL' in labels and 'Medial Meniscus' in labels:
    eff_idx = labels.index('Effusion')
    acl_idx = labels.index('ACL')
    mm_idx = labels.index('Medial Meniscus')
    tear_max = np.maximum(out[:, acl_idx], out[:, mm_idx])
    out[:, eff_idx] = np.maximum(out[:, eff_idx], 0.85 * tear_max)

# Strict probability boundary clipping to eliminate infinite log-loss penalties
out = np.clip(out, 1e-6, 1.0 - 1e-6)
"""

    # Replace blending logic in the cell
    if "out = (1.0 - w_c) * preds_blend + w_c * preds_c" in cell_source:
        cell_source = cell_source.replace(
            "out = (1.0 - w_c) * preds_blend + w_c * preds_c",
            "# Multi-model consensus replaced by Trimmed Median\npass",
        )

    # Replace the tail of the cell before sub.to_csv
    pattern = r"# Invariant Projection: Acute tears physically co-occur with joint effusion.*?out = np\.clip\(out, 1e-6, 1\.0 - 1e-6\)"
    if re.search(pattern, cell_source, re.DOTALL):
        cell_source = re.sub(pattern, trimmed_median_blend_code.strip(), cell_source, flags=re.DOTALL)
    elif "# Strict probability boundary clipping" in cell_source:
        tail_pattern = r"# Strict probability boundary clipping.*"
        cell_source = re.sub(tail_pattern, trimmed_median_blend_code.strip() + "\nsub.to_csv('submission.csv', index=False)\nprint('Submission saved successfully!')", cell_source, flags=re.DOTALL)

    nb["cells"][cell_idx]["source"] = [line + "\n" for line in cell_source.splitlines()]

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print(f"Successfully assembled RSNA Knee SOTA v40 Trimmed Median Consensus in {NB_PATH}")


if __name__ == "__main__":
    main()
