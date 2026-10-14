"""First-Principles Mass Conservation & Neutral Loss Verifier for Tandem Mass Spectrometry (MS/MS).

Domain Physics (Enveda CASMI26):
Mass spectrometry is governed by the First Law of Thermodynamics (Conservation of Mass-Energy).
During collision-induced dissociation (CID), precursor ions fragment into charged daughter ions
and uncharged neutral molecules:

    [M + H]+ -> [F_i]+ + N_i

Where:
    m/z([F_i]+) + m(N_i) == m/z([M + H]+) (within instrumental mass accuracy, e.g. 10 ppm)

Diagnostic neutral losses reflect specific chemical functional groups:
- 18.0106 Da: H2O (Hydroxyl / Carboxylic acid)
- 17.0265 Da: NH3 (Primary amine / Amide)
- 27.9949 Da: CO (Carbonyl / Quinone)
- 43.9898 Da: CO2 (Carboxylic acid ester / Decarboxylation)
- 44.0262 Da: CH2NO (Amide cleavage)
- 60.0211 Da: C2H4O2 (Acetate / Methyl ester)

A candidate molecular structure is physically admissible only if its graph contains
sub-graphs and neutral losses consistent with the empirical fragmentation spectrum.
This decouples evaluation from database popularity priors (which bias models against
novel natural products) and bases ranking on physical chemical invariants.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Sequence


@dataclass(frozen=True)
class DiagnosticNeutralLoss:
    name: str
    mass: float
    formula: str
    functional_group: str


COMMON_NEUTRAL_LOSSES: tuple[DiagnosticNeutralLoss, ...] = (
    DiagnosticNeutralLoss("Water", 18.010565, "H2O", "Hydroxyl / Carboxylic acid"),
    DiagnosticNeutralLoss("Ammonia", 17.026549, "NH3", "Amine / Amide"),
    DiagnosticNeutralLoss("Carbon monoxide", 27.994915, "CO", "Carbonyl / Quinone"),
    DiagnosticNeutralLoss("Methanol", 32.026215, "CH4O", "Methoxy / Methyl ester"),
    DiagnosticNeutralLoss("Carbon dioxide", 43.989829, "CO2", "Carboxylic acid ester"),
    DiagnosticNeutralLoss("Ethanol", 46.041865, "C2H6O", "Ethoxy / Ethyl ester"),
    DiagnosticNeutralLoss("Acetic acid", 60.021129, "C2H4O2", "Acetate"),
)


class MassConservationVerifier:
    """Evaluates the physical admissibility of candidate structures against MS/MS peak spectra."""

    def __init__(self, tolerance_ppm: float = 15.0) -> None:
        self.tolerance_ppm = tolerance_ppm

    def matches_mass(self, observed_mass: float, theoretical_mass: float) -> bool:
        """Check if observed mass matches theoretical mass within ppm tolerance."""
        if theoretical_mass <= 0:
            return False
        delta_ppm = (abs(observed_mass - theoretical_mass) / theoretical_mass) * 1e6
        return delta_ppm <= self.tolerance_ppm

    def extract_neutral_losses(
        self,
        precursor_mz: float,
        peaks_mz: Sequence[float],
        peaks_intensity: Sequence[float],
        min_relative_intensity: float = 0.02,
    ) -> list[dict[str, float | str]]:
        """Identify physically plausible diagnostic neutral losses from MS/MS spectrum."""
        if not peaks_mz or len(peaks_mz) != len(peaks_intensity):
            return []

        max_intensity = max(peaks_intensity) if peaks_intensity else 1.0
        detected_losses: list[dict[str, float | str]] = []

        for mz, intensity in zip(peaks_mz, peaks_intensity):
            rel_int = intensity / max_intensity
            if rel_int < min_relative_intensity:
                continue

            delta_mass = precursor_mz - mz
            if delta_mass <= 0:
                continue

            for loss in COMMON_NEUTRAL_LOSSES:
                if self.matches_mass(delta_mass, loss.mass):
                    detected_losses.append({
                        "name": loss.name,
                        "observed_loss_da": round(delta_mass, 4),
                        "theoretical_loss_da": loss.mass,
                        "formula": loss.formula,
                        "functional_group": loss.functional_group,
                        "fragment_mz": round(mz, 4),
                        "relative_intensity": round(rel_int, 4),
                    })

        return detected_losses

    def score_candidate_admissibility(
        self,
        candidate_exact_mass: float,
        precursor_mz: float,
        adduct: str,
        detected_losses: Sequence[dict[str, float | str]],
        candidate_has_hydroxyl: bool = True,
        candidate_has_carboxylic: bool = True,
        candidate_has_amine: bool = True,
    ) -> dict[str, float | bool]:
        """Verify mass conservation and chemical functional group consistency.

        Returns a physical plausibility score in [0.0, 1.0].
        """
        # 1. Verify precursor adduct mass
        adduct_masses = {
            "[M+H]+": 1.007276,
            "[M+Na]+": 22.989218,
            "[M+NH4]+": 18.033823,
            "[M-H]-": -1.007276,
        }
        adduct_delta = adduct_masses.get(adduct, 1.007276)
        expected_precursor = candidate_exact_mass + adduct_delta

        precursor_match = self.matches_mass(precursor_mz, expected_precursor)
        if not precursor_match:
            return {
                "is_admissible": False,
                "plausibility_score": 0.0,
                "reason": f"Precursor mass mismatch ({precursor_mz:.4f} vs expected {expected_precursor:.4f})",
            }

        # 2. Check neutral loss compatibility with functional groups
        explained_losses = 0
        total_losses = len(detected_losses)

        for loss in detected_losses:
            name = loss["name"]
            if name == "Water" and (candidate_has_hydroxyl or candidate_has_carboxylic):
                explained_losses += 1
            elif name == "Ammonia" and candidate_has_amine:
                explained_losses += 1
            elif name == "Carbon dioxide" and candidate_has_carboxylic:
                explained_losses += 1
            elif name in ("Carbon monoxide", "Methanol", "Ethanol", "Acetic acid"):
                explained_losses += 1

        loss_score = (explained_losses / total_losses) if total_losses > 0 else 1.0

        return {
            "is_admissible": True,
            "plausibility_score": round(0.5 + 0.5 * loss_score, 4),
            "explained_losses": explained_losses,
            "total_detected_losses": total_losses,
        }
