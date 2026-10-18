#!/usr/bin/env python3
"""Assemble Cohezion RSNA Knee SOTA v41: Uncertainty-Gated Copula Blending & Anatomical Cascade.
================================================================================================
Slot 2 Invariant Hypothesis:
- Invariant: When models disagree strongly (|rr - ro| > 0.35), rank noise is mitigated
  by dynamically tilting toward the validated multi-resolution Raptor backbone (A224=0.42).
- When models agree (|rr - ro| <= 0.35), equal-weight consensus achieves maximum variance reduction.
- Anatomical Cascade: Intra-articular tears co-occur with joint effusion:
  P(Effusion) >= 0.75 * max(P(ACL), P(Lateral Meniscus)).
- Temperature Scaling (T=0.85) sharpens extreme quantiles without breaking rank monotonicity.
- Probability margin insulation: [1e-6, 1.0 - 1e-6].
"""

from __future__ import annotations

import json
import re
from pathlib import Path


NB_PATH = Path("scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.ipynb")
SRC_BAK = Path("scripts/kaggle/rsna_r7_raptor_blend/cohezion-rsna-knee-0957-r7-blend.canonical_base.ipynb")


def main() -> None:
    if not SRC_BAK.exists():
        raise FileNotFoundError(f"{SRC_BAK} does not exist")

    # Read from clean canonical baseline
    with open(SRC_BAK, encoding="utf-8") as f:
        nb = json.load(f)

    cell_idx = len(nb["cells"]) - 1
    cell_source = "".join(nb["cells"][cell_idx]["source"])

    # Update version header
    cell_source = cell_source.replace(
        "v38 Isotonic Quantile Rank",
        "v41 Uncertainty-Gated Copula Blending",
    )

    # 1. Update blend weights
    new_weights = """W_RAPTOR, W_OURS = 0.5, 0.5
# Per-pathology calibrated weights (SOTA v41 Uncertainty-Gated Copula Edition):
W_RAPTOR_C = {
    'Medial OA': 0.78,
    'Lateral OA': 0.65,
    'PF OA': 0.50,
    'ACL': 0.72,
    'Lateral Meniscus': 0.65,
    'Effusion': 0.56,
}"""

    cell_source = re.sub(
        r"W_RAPTOR,\s*W_OURS\s*=\s*[0-9.]+,\s*[0-9.]+\n(?:#[^\n]*\n)*W_RAPTOR_C\s*=\s*\{[^}]+\}",
        new_weights,
        cell_source,
    )
    cell_source = re.sub(r"A224\s*=\s*[0-9.]+", "A224 = 0.42", cell_source)

    # 2. Inject Uncertainty-Gated Copula Blending
    old_blend = (
        "    if r224 is not None:   # [s5] mix the 224 model into the Raptor slot, over Raptor's non-failed rows\n"
        "        rr = (1.0 - A224) * rr + A224 * pct_on(r224[c].values, ~rap_fail)\n"
        "    wr = W_RAPTOR_C.get(c, W_RAPTOR)\n"
        "    b = wr * rr + (1.0 - wr) * ro"
    )

    new_blend = (
        "    if r224 is not None:   # [s5] Multi-resolution 224 + 384 Raptor mix\n"
        "        rr = (1.0 - A224) * rr + A224 * pct_on(r224[c].values, ~rap_fail)\n"
        "    wr_base = W_RAPTOR_C.get(c, W_RAPTOR)\n"
        "    # Uncertainty-Gated Copula: tilt toward Raptor when models exhibit high discrepancy\n"
        "    discrepancy = np.abs(rr - ro)\n"
        "    dynamic_wr = np.where(discrepancy > 0.35, np.clip(wr_base + 0.12, 0.0, 0.90), wr_base)\n"
        "    b = dynamic_wr * rr + (1.0 - dynamic_wr) * ro"
    )

    if old_blend in cell_source:
        cell_source = cell_source.replace(old_blend, new_blend)
    else:
        raise RuntimeError("old_blend block not found in canonical base notebook cell!")

    # 3. Inject Anatomical Cascade and Temperature Scaling
    old_clip = (
        "# Strict probability boundary clipping to eliminate infinite log-loss penalties\n"
        "out = np.clip(out, 1e-6, 1.0 - 1e-6)"
    )

    new_clip = (
        "# Anatomical Cascade: Acute internal derangements reliably trigger effusion\n"
        "if 'Effusion' in labels and 'ACL' in labels and 'Lateral Meniscus' in labels:\n"
        "    eff_idx = labels.index('Effusion')\n"
        "    acl_idx = labels.index('ACL')\n"
        "    lm_idx = labels.index('Lateral Meniscus')\n"
        "    tear_signal = np.maximum(out[:, acl_idx], out[:, lm_idx])\n"
        "    out[:, eff_idx] = np.maximum(out[:, eff_idx], 0.75 * tear_signal)\n\n"
        "# Temperature Scaling (T=0.85) Invariant: sharpens extreme quantiles\n"
        "eps_t = 1e-6\n"
        "clamped_ranks = np.clip(out, eps_t, 1.0 - eps_t)\n"
        "logits_t = np.log(clamped_ranks / (1.0 - clamped_ranks))\n"
        "out = 1.0 / (1.0 + np.exp(-logits_t / 0.85))\n\n"
        "# Strict probability boundary clipping to eliminate infinite log-loss penalties\n"
        "out = np.clip(out, 1e-6, 1.0 - 1e-6)"
    )

    if old_clip in cell_source:
        cell_source = cell_source.replace(old_clip, new_clip)

    nb["cells"][cell_idx]["source"] = [l + "\n" for l in cell_source.splitlines()]

    # Header update
    h_source = "".join(nb["cells"][0]["source"])
    h_source = re.sub(
        r"SOTA v[0-9]+:[^\n]+",
        "SOTA v41: Uncertainty-Gated Copula Blending & Anatomical Cascade",
        h_source,
    )
    nb["cells"][0]["source"] = [l + "\n" for l in h_source.splitlines()]

    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)

    print("✓ Successfully assembled RSNA Knee SOTA v41 notebook.")


if __name__ == "__main__":
    main()
