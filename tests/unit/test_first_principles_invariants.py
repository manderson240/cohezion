"""Unit tests for First-Principles Invariant Modules:
1. MDLProgramSelector (ARC-AGI Algorithmic Information Theory)
2. MassConservationVerifier (CASMI26 Physical Thermodynamics)
3. BiomechanicalKneeInvariants (RSNA Knee Anatomical & Kinetic Coupling)
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cohezion.chemistry.mass_conservation_verifier import MassConservationVerifier
from cohezion.medical.biomechanical_knee_invariants import BiomechanicalKneeInvariants
from cohezion.optimization.mdl_program_selector import MDLProgramSelector


def test_mdl_program_selector_complexity():
    selector = MDLProgramSelector()

    concise_code = """
def transform(grid):
    return [row[::-1] for row in grid]
"""

    bloated_lookup_code = """
def transform(grid):
    if len(grid) == 3:
        if grid[0][0] == 1:
            return [[1, 2, 3], [4, 5, 6], [7, 8, 9]]
        elif grid[0][0] == 2:
            return [[2, 2, 2], [3, 3, 3], [4, 4, 4]]
        else:
            return [[0, 0, 0], [0, 0, 0], [0, 0, 0]]
    elif len(grid) == 4:
        return [[1] * 4 for _ in range(4)]
    return grid
"""

    score_concise = selector.compute_complexity(concise_code)
    score_bloated = selector.compute_complexity(bloated_lookup_code)

    assert score_concise["is_valid"] is True
    assert score_bloated["is_valid"] is True
    assert score_concise["mdl_score"] < score_bloated["mdl_score"]
    assert score_concise["branch_count"] == 0
    assert score_bloated["branch_count"] > 3

    # Ranking test
    cands = [
        {"code": bloated_lookup_code, "all_train_passed": True, "name": "bloated"},
        {"code": concise_code, "all_train_passed": True, "name": "concise"},
        {"code": "syntax error !!!", "all_train_passed": True, "name": "invalid"},
    ]
    ranked = selector.rank_candidates(cands)
    assert ranked[0]["name"] == "concise"
    assert ranked[1]["name"] == "bloated"
    assert ranked[2]["name"] == "invalid"
    assert ranked[2]["pareto_score"] == float("inf")


def test_mass_conservation_verifier():
    verifier = MassConservationVerifier(tolerance_ppm=10.0)

    # Aspirin: C9H8O4, Exact Mass: 180.0423
    exact_mass = 180.0423
    precursor_mz = 181.0496  # [M+H]+ = 180.0423 + 1.007276 = 181.049576
    assert verifier.matches_mass(precursor_mz, 181.0496) is True

    # Neutral loss test: water loss (18.0106) and CO2 loss (43.9898)
    fragment_1 = precursor_mz - 18.0106  # 163.0390
    fragment_2 = precursor_mz - 43.9898  # 137.0598
    fragment_noise = 50.1234

    peaks_mz = [fragment_1, fragment_2, fragment_noise]
    peaks_int = [1000.0, 500.0, 50.0]

    losses = verifier.extract_neutral_losses(precursor_mz, peaks_mz, peaks_int)
    loss_names = [l["name"] for l in losses]
    assert "Water" in loss_names
    assert "Carbon dioxide" in loss_names

    score_res = verifier.score_candidate_admissibility(
        candidate_exact_mass=exact_mass,
        precursor_mz=precursor_mz,
        adduct="[M+H]+",
        detected_losses=losses,
        candidate_has_hydroxyl=True,
        candidate_has_carboxylic=True,
    )
    assert score_res["is_admissible"] is True
    assert score_res["plausibility_score"] >= 0.90


def test_biomechanical_knee_invariants():
    invariants = BiomechanicalKneeInvariants(pivot_shift_coupling=0.20)

    df = pd.DataFrame({
        "StudyInstanceUID": ["UID_1", "UID_2"],
        "ACL": [0.95, 0.10],
        "Contusion": [0.01, 0.05],
        "Medial OA": [0.90, 0.15],
        "Medial Meniscus": [0.02, 0.20],
        "Lateral Meniscus": [0.5, 0.1],
        "MCL": [0.1, 0.1],
        "Lateral OA": [0.1, 0.1],
        "PF OA": [0.1, 0.1],
        "Effusion": [0.5, 0.5],
        "Synovitis": [0.5, 0.5],
        "Baker's": [0.1, 0.1],
        "Fracture": [0.0, 1.0],  # test boundary clamping
    })

    coupled_df = invariants.apply_biomechanical_coupling(df)

    # UID_1 has ACL = 0.95, so contusion should be elevated from 0.01 to at least 0.95 * 0.20 = 0.19
    assert coupled_df.loc[0, "Contusion"] >= 0.19
    # Fracture was 0.0, should be clamped to eps
    assert coupled_df.loc[0, "Fracture"] >= 1e-6
    assert coupled_df.loc[1, "Fracture"] <= 1.0 - 1e-6

    # Verify anatomical audit
    audit = invariants.verify_anatomical_integrity(coupled_df)
    assert audit["total_records"] == 2
    assert audit["nan_or_inf_count"] == 0
    assert audit["acl_with_zero_contusion"] == 0
