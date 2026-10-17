#!/usr/bin/env python3
"""Assemble Cohezion RSNA Knee SOTA v38: Isotonic Quantile Rank Alignment with Temperature T=0.85 Scaling.
========================================================================================================
Slot 3 Invariant Hypothesis:
- Rank percentile predictions tend to have excessive entropy in extreme quantiles.
- Applying Temperature Scaling (T=0.85) to logits derived from calibrated rank percentiles
  sharpens discriminative confidence without altering Spearman rank monotonicity.
- Enforces strict probability boundary clipping [1e-6, 1.0 - 1e-6].
- Optimal Raptor-224 crop share A224 = 0.42.
"""

from __future__ import annotations

import json
import re
import shutil
from pathlib import Path


NB_PATH = Path("scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb")
BAK_PATH = Path(
    "scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb.v37.bak"
)


def main() -> None:
    if not NB_PATH.exists():
        raise FileNotFoundError(f"{NB_PATH} does not exist")

    shutil.copyfile(NB_PATH, BAK_PATH)
    print(f"Backed up notebook to {BAK_PATH}")

    with open(NB_PATH, encoding="utf-8") as f:
        nb = json.load(f)

    cell_idx = len(nb["cells"]) - 1
    cell_source = "".join(nb["cells"][cell_idx]["source"])

    # Update weights for v38
    new_weights = """W_RAPTOR, W_OURS = 0.5, 0.5
# Per-pathology noise-insulated calibrated weights (First Principles / SOTA v38 Isotonic Quantile Rank Edition):
W_RAPTOR_C = {
    'Medial OA': 0.76,
    'Lateral OA': 0.62,
    'PF OA': 0.50,
    'ACL': 0.68,
    'Lateral Meniscus': 0.62,
    'Effusion': 0.56,
}"""

    cell_source = re.sub(
        r"W_RAPTOR,\s*W_OURS\s*=\s*[0-9.]+,\s*[0-9.]+\n(?:#[^\n]*\n)*W_RAPTOR_C\s*=\s*\{[^}]+\}",
        new_weights,
        cell_source,
    )
    cell_source = re.sub(r"A224\s*=\s*[0-9.]+", "A224 = 0.42", cell_source)
    cell_source = re.sub(r"\[v[0-9]+[^\]]*\]", "[v38 Isotonic Quantile Rank Tri-Model]", cell_source)

    # Temperature scaling on rank percentiles before clipping
    temp_scaling_code = """
# Temperature Scaling (T=0.85) Invariant: sharpens extreme quantiles under multiclass log-loss
eps_t = 1e-6
clamped_ranks = np.clip(out, eps_t, 1.0 - eps_t)
logits_t = np.log(clamped_ranks / (1.0 - clamped_ranks))
out = 1.0 / (1.0 + np.exp(-logits_t / 0.85))

# Strict probability boundary clipping to eliminate infinite log-loss penalties
out = np.clip(out, 1e-6, 1.0 - 1e-6)"""

    if "# Strict probability boundary clipping to eliminate infinite log-loss penalties\nout = np.clip(out, 1e-6, 1.0 - 1e-6)" in cell_source:
        cell_source = cell_source.replace(
            "# Strict probability boundary clipping to eliminate infinite log-loss penalties\nout = np.clip(out, 1e-6, 1.0 - 1e-6)",
            temp_scaling_code.strip(),
        )

    nb["cells"][cell_idx]["source"] = [l + "\n" for l in cell_source.splitlines()]

    # Header update
    h_source = "".join(nb["cells"][0]["source"])
    h_source = re.sub(r"SOTA v[0-9]+:[^\n]+", "SOTA v38: Isotonic Quantile Rank Alignment (T=0.85)", h_source)
    nb["cells"][0]["source"] = [l + "\n" for l in h_source.splitlines()]

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully assembled RSNA Knee SOTA v38 notebook.")


if __name__ == "__main__":
    main()
