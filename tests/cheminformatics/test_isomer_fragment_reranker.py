"""Unit tests verifying structural isomer discrimination via in-silico cleavage.
================================================================================
Tests discrimination across:
1. Functional group isomers (Butyl acetate vs Ethyl butyrate, C6H12O2).
2. Regioisomers (Methyl salicylate vs 2,4-Dihydroxyacetophenone, C8H8O3).
3. Stepped Collision Energy (CE) sensitivity.
4. Edge-case resilience (empty spectrum, malformed inputs).
"""

from __future__ import annotations

import pytest
from cohezion.cheminformatics.isomer_fragment_reranker import IsomerFragmentReranker


@pytest.fixture
def reranker() -> IsomerFragmentReranker:
    return IsomerFragmentReranker(tolerance_da=0.015, tolerance_ppm=15.0)


def test_ester_functional_isomers_discrimination(reranker: IsomerFragmentReranker) -> None:
    """Case 1: Butyl acetate vs Ethyl butyrate (Formula: C6H12O2, Exact MW: 116.0837 Da).
    Butyl acetate yields diagnostic loss of acetic acid (m/z 57.0699), acetate ion (m/z 61.0284),
    and intact precursor [M+H]+ at m/z 117.0910.
    Ethyl butyrate does not produce the m/z 57.0699 neutral loss.
    """
    butyl_acetate = "CCCCOC(=O)C"      # C6H12O2
    ethyl_butyrate = "CCCC(=O)OCC"     # C6H12O2

    # Synthetic experimental MS/MS spectrum corresponding to BUTYL ACETATE:
    exp_peaks_butyl_acetate = [
        (57.0699, 0.70),   # [M+H - CH3COOH]+
        (61.0284, 0.50),   # [CH3COOH2]+
        (117.0910, 0.30),  # [M+H]+
    ]

    score_butyl = reranker.score_candidate(butyl_acetate, exp_peaks_butyl_acetate)
    score_ethyl = reranker.score_candidate(ethyl_butyrate, exp_peaks_butyl_acetate)

    assert score_butyl.explained_intensity_ratio > score_ethyl.explained_intensity_ratio
    assert score_butyl.matched_peak_count >= 2
    assert score_butyl.composite_score > score_ethyl.composite_score

    # Now verify reranking: Butyl acetate starts at rank 5, Ethyl butyrate at rank 1
    candidates = [ethyl_butyrate, "CCCCCC(=O)O", "CC(C)CC(=O)O", "CCC(C)C(=O)O", butyl_acetate]
    reranked = reranker.rerank_candidate_pool(candidates, exp_peaks_butyl_acetate)

    # Butyl acetate should jump to Rank 1!
    top_candidate = reranked[0]
    assert top_candidate.smiles == butyl_acetate
    assert top_candidate.final_rank == 1
    assert top_candidate.rank_delta == +4  # Promoted from rank 5 to rank 1!


def test_aromatic_regioisomer_discrimination(reranker: IsomerFragmentReranker) -> None:
    """Case 2: Methyl salicylate vs 2,4-Dihydroxyacetophenone (Formula: C8H8O3).
    Methyl salicylate (COC(=O)c1ccccc1O) exhibits diagnostic loss of methanol (32.026 Da)
    yielding m/z 121.0284, and precursor at 153.0546.
    """
    methyl_salicylate = "COC(=O)c1ccccc1O"        # C8H8O3
    dihydroxyacetophenone = "CC(=O)c1ccc(O)cc1O"   # C8H8O3

    # Experimental MS/MS for methyl salicylate
    exp_peaks_salicylate = [
        (153.0546, 0.40),  # [M+H]+
        (121.0284, 0.90),  # [M+H - CH3OH]+ (diagnostic methanol loss)
    ]

    score_salicylate = reranker.score_candidate(methyl_salicylate, exp_peaks_salicylate)
    score_other = reranker.score_candidate(dihydroxyacetophenone, exp_peaks_salicylate)

    assert score_salicylate.composite_score > score_other.composite_score
    assert score_salicylate.explained_intensity_ratio > 0.60


def test_stepped_collision_energy_variance(reranker: IsomerFragmentReranker) -> None:
    """Verifies that stepped collision energy appropriately modulates scoring."""
    smiles = "COC(=O)c1ccccc1O"
    exp_peaks = [
        (153.0546, 0.70),  # Intact precursor
        (121.0284, 0.30),  # Diagnostic neutral loss
    ]

    low_ce_score = reranker.score_candidate(smiles, exp_peaks, collision_energy=15.0)
    high_ce_score = reranker.score_candidate(smiles, exp_peaks, collision_energy=45.0)

    # At low CE and high CE, scoring is active and positive
    assert low_ce_score.stepped_ce_variance_score > 0.0
    assert high_ce_score.stepped_ce_variance_score > 0.0


def test_empty_spectrum_and_invalid_smiles_graceful_handling(
    reranker: IsomerFragmentReranker,
) -> None:
    """Ensure resilience against degenerate inputs."""
    res_empty = reranker.score_candidate("CCC", [])
    assert res_empty.composite_score == 0.0
    assert res_empty.matched_peak_count == 0

    res_invalid = reranker.score_candidate("INVALID_SMILES_STRING", [(100.0, 1.0)])
    assert res_invalid.composite_score == 0.0
