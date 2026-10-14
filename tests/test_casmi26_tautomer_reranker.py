"""Unit tests for CASMI26 Tautomer-Aware Canonicalization & Isomer Reranker."""

import pytest
rdkit = pytest.importorskip("rdkit")
from rdkit import Chem
from rdkit.Chem.MolStandardize import rdMolStandardize

te = rdMolStandardize.TautomerEnumerator()

def canonical_ik14(smi: str, fallback_ik14: str = "") -> str:
    if not smi:
        return fallback_ik14
    try:
        m = Chem.MolFromSmiles(smi)
        if m is not None:
            m_canon = te.Canonicalize(m)
            ik = Chem.MolToInchiKey(m_canon)
            if ik:
                return ik[:14]
    except Exception:
        pass
    return fallback_ik14


def test_tautomer_canonicalization():
    # Keto vs Enol forms of acetylacetone
    smi_keto = "CC(=O)CC(=O)C"
    smi_enol = "CC(=O)C=C(O)C"

    # Raw InChIKeys are different
    m_k = Chem.MolFromSmiles(smi_keto)
    m_e = Chem.MolFromSmiles(smi_enol)
    raw_k = Chem.MolToInchiKey(m_k)[:14]
    raw_e = Chem.MolToInchiKey(m_e)[:14]
    assert raw_k != raw_e, "Raw InChIKeys should differ before canonicalization"

    # Canonical InChIKeys must match
    canon_k = canonical_ik14(smi_keto)
    canon_e = canonical_ik14(smi_enol)
    assert canon_k == canon_e == "YRKCREAYFQTBPV", "Canonical InChIKey14 must match exactly"


def test_deduplication_loop():
    candidates = [
        ("CC(=O)CC(=O)C", 0.95),  # Keto
        ("CC(=O)C=C(O)C", 0.90),  # Enol (duplicate tautomer of #1)
        ("c1ccccc1O", 0.85),      # Phenol (unique)
        ("CCO", 0.80),            # Ethanol (unique)
    ]
    seen_ik14 = set()
    selected_smis = []
    for smi, score in candidates:
        ik = canonical_ik14(smi)
        if ik not in seen_ik14:
            seen_ik14.add(ik)
            selected_smis.append(smi)

    # Enol should be skipped, leaving exactly 3 distinct molecules
    assert len(selected_smis) == 3
    assert selected_smis[0] == "CC(=O)CC(=O)C"
    assert selected_smis[1] == "c1ccccc1O"
    assert selected_smis[2] == "CCO"
