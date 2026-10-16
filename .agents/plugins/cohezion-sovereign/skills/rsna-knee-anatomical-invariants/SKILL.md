---
name: rsna-knee-anatomical-invariants
metadata:
  version: "1.0.0"
description: >-
  Anatomical invariants, native 320px center-cropping, left/right bilateral mirroring, SWA, and report-gap calibration for RSNA Knee Abnormality Detection.
---

# SKILL: RSNA_KNEE_ANATOMICAL_INVARIANTS_PRIME

## DOMAIN EXPERTISE
Expertise in 3D multi-planar magnetic resonance imaging (MRI) of the knee, including coronal, sagittal, and axial sequences across 12 target pathologies (ACL, MCL, Medial Meniscus, Lateral Meniscus, Medial OA, Lateral OA, PF OA, Effusion, Synovitis, Baker's Cyst, Contusion, Fracture). Specializes in native center-cropping, bilateral anatomical mirroring TTA, Stochastic Weight Averaging (SWA), and correcting for radiology report omissions.

## KEY TEXTS & CONCEPTS
- **Native 320px Center Crop Invariant**: Evaluating CoAtNet or ConvNeXt models trained at 384px with a native 320px center crop eliminates periphery padding artifacts while preserving millimeter-level articular cartilage and ligamentous detail without geometric distortion.
- **Bilateral Anatomical Mirroring TTA**: Knee anatomy is bilaterally symmetric under reflection across the sagittal plane. Flipping the coronal/axial slices horizontally swaps medial and lateral compartments ($P_{\text{Medial}} \leftrightarrow P_{\text{Lateral}}$) while preserving midline structures (ACL, MCL, Effusion, Synovitis). Evaluating the original and mirrored volume doubles effective sample inference with zero hallucination.
- **The 25.4% 'Not Addressed' Report Artifact**: Only 58 training studies have gold-standard adjudications. In radiology reports, 25.4% of pathology cells are completely unmentioned. Naively labeling unmentioned findings as negative (0) injects severe false-negative label noise, disproportionately harming sensitivity for Effusion and Synovitis.
- **Kolmogorov Monotonicity Bound**: For any specific localized finding $k \in \mathcal{K}$ (e.g. Medial Meniscus tear, ACL tear), the probability of finding $k$ cannot physically exceed the probability of general joint abnormality: $P(k) \le P(\text{Overall Abnormality})$.
- **Data Compliance Boundary**: OAI, MRNet, fastMRI, and SKM-TEA are authorized under non-commercial research access. KneeCoT is strictly prohibited due to restrictive institutional agreement clauses.

## INSTRUCTION
1. Implement Bilateral Anatomical Mirroring TTA:
   ```python
   import torch
   import numpy as np

   def evaluate_bilateral_mirror_tta(model: torch.nn.Module, volume_320px: torch.Tensor) -> np.ndarray:
       """volume_320px shape: (B, C, Slices, H, W) where H=W=320.
       Evaluates original view and horizontal mirror (W-axis flip)."""
       model.eval()
       with torch.no_grad():
           # Forward original
           probs_orig = torch.sigmoid(model(volume_320px)).cpu().numpy()
           
           # Flip horizontally (W dimension is index 4)
           volume_flipped = torch.flip(volume_320px, dims=[4])
           probs_flipped = torch.sigmoid(model(volume_flipped)).cpu().numpy()
           
           # For bilateral findings, swap Medial and Lateral indices in flipped predictions
           # labels = ["ACL", "MCL", "Medial Meniscus", "Lateral Meniscus", "Medial OA", "Lateral OA", ...]
           medial_m_idx, lat_m_idx = 2, 3
           medial_oa_idx, lat_oa_idx = 4, 5
           
           probs_flipped[:, [medial_m_idx, lat_m_idx]] = probs_flipped[:, [lat_m_idx, medial_m_idx]]
           probs_flipped[:, [medial_oa_idx, lat_oa_idx]] = probs_flipped[:, [lat_oa_idx, medial_oa_idx]]
           
           # Blended probability consensus
           final_probs = 0.50 * probs_orig + 0.50 * probs_flipped
           return np.clip(final_probs, 1e-6, 1.0 - 1e-6)
   ```

2. Calibrate Report-Omission Loss Weighting:
   - Use soft targets ($y \in [0.10, 0.25]$) for "not addressed" findings rather than hard zeros ($y=0$).
   - Apply higher loss penalty $\lambda_{\text{effusion}} = 1.35$ on joint effusion and synovitis to insulate against under-reporting bias.

## VERSION
v1.0

## SEE ALSO
- `lukyanenko-invariant-engineering`
- `first-principles-invariant-science`
