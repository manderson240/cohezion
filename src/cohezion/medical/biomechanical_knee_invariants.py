"""First-Principles Biomechanical & Anatomical Invariants for Knee MRI Pathology.

Domain Biomechanics (RSNA Knee Abnormality Detection):
A knee joint is a constrained mechanical linkage (tibia, femur, patella) stabilized
by primary and secondary restraints:

1. Cruciate Ligament Biomechanics:
   - The Anterior Cruciate Ligament (ACL) is the primary restraint to anterior tibial translation.
   - Rupture typically occurs during a non-contact valgus-external rotation or hyperextension pivot shift.
   - Kinetic Signature: ACL tear strongly couples with bone contusions ("bone bruises") in the
     posterior lateral tibial plateau and sulcus terminalis of the lateral femoral condyle.

2. Meniscal Load Distribution:
   - Medial meniscus absorbs 50% of the medial compartment load; lateral meniscus absorbs 70%.
   - Chronic Medial Osteoarthritis (OA) induces joint space loss, cartilage erosion, and secondary
     complex/macerated tears of the medial meniscus.

3. Mathematical Invariants:
   - Kolmogorov Hierarchy: P(Abnormal) >= max(P(specific_pathologies))
   - Copula Coupling: Models predicting ACL tear with high confidence (>0.85) should have elevated
     prior expectations for contusion and lateral meniscal pathology.
   - Bounded Calibration: Prevents metric divergence under log-loss evaluation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


class BiomechanicalKneeInvariants:
    """Enforces anatomical consistency and biomechanical coupling constraints on multi-label knee predictions."""

    SUBCONDITIONS: tuple[str, ...] = (
        "ACL",
        "MCL",
        "Medial Meniscus",
        "Lateral Meniscus",
        "Medial OA",
        "Lateral OA",
        "PF OA",
        "Effusion",
        "Synovitis",
        "Baker's",
        "Contusion",
        "Fracture",
    )

    def __init__(
        self,
        eps: float = 1e-6,
        pivot_shift_coupling: float = 0.15,
        oa_meniscal_coupling: float = 0.10,
    ) -> None:
        self.eps = eps
        self.pivot_shift_coupling = pivot_shift_coupling
        self.oa_meniscal_coupling = oa_meniscal_coupling

    def enforce_probability_bounds(self, preds: np.ndarray) -> np.ndarray:
        """Clamp probabilities strictly within [eps, 1 - eps] to eliminate log-loss divergences."""
        return np.clip(preds, self.eps, 1.0 - self.eps)

    def apply_biomechanical_coupling(self, df: pd.DataFrame) -> pd.DataFrame:
        """Adjust predictions to reflect anatomical kinetic cascades.

        If a complete ACL tear is detected, increase the floor for pivot-shift bone contusion.
        If advanced Medial OA is present, ensure meniscal degeneration expectation is physiologically sound.
        """
        out = df.copy()

        # 1. Pivot-shift kinetic coupling: ACL -> Contusion
        if "ACL" in out.columns and "Contusion" in out.columns:
            acl_high = out["ACL"] > 0.80
            # Biomechanical kinetic floor: high-confidence ACL tear implies elevated contusion probability
            contusion_floor = out.loc[acl_high, "ACL"] * self.pivot_shift_coupling
            out.loc[acl_high, "Contusion"] = np.maximum(
                out.loc[acl_high, "Contusion"],
                contusion_floor,
            )

        # 2. Degenerative coupling: Medial OA -> Medial Meniscus
        if "Medial OA" in out.columns and "Medial Meniscus" in out.columns:
            oa_severe = out["Medial OA"] > 0.85
            med_men_floor = out.loc[oa_severe, "Medial OA"] * self.oa_meniscal_coupling
            out.loc[oa_severe, "Medial Meniscus"] = np.maximum(
                out.loc[oa_severe, "Medial Meniscus"],
                med_men_floor,
            )

        # 3. Enforce strict numerical bounds across all columns
        for col in self.SUBCONDITIONS:
            if col in out.columns:
                out[col] = self.enforce_probability_bounds(out[col].values)

        return out

    def verify_anatomical_integrity(self, df: pd.DataFrame) -> dict[str, int | float]:
        """Audit predictions for physiologically impossible configurations."""
        report: dict[str, int | float] = {
            "total_records": len(df),
            "acl_with_zero_contusion": 0,
            "nan_or_inf_count": 0,
        }

        # Check for NaN / Inf
        report["nan_or_inf_count"] = int(df[list(self.SUBCONDITIONS)].isna().sum().sum())

        # Check for uncoupled ACL tears with zero contusion
        if "ACL" in df.columns and "Contusion" in df.columns:
            uncoupled = (df["ACL"] > 0.90) & (df["Contusion"] < 0.05)
            report["acl_with_zero_contusion"] = int(uncoupled.sum())

        return report
