#!/usr/bin/env python3
"""Patch CASMI26 Kernel to v15: IV&V Hardened Calibrated Reranker.

Eliminates destabilizing Gaussian mass penalty (w_ppm=0.0).
Restores w_gbdt=0.35, w_tanimoto=0.25, w_cleavage=0.25, w_entropy=0.15.
Preserves official RDKit Tautomer Canonicalization (canonical_ik14).
Guards against NaN/Inf.
Performs AST verification and generates an IVVCertificate.
"""

from __future__ import annotations

import ast
import json
import math
import sys
from pathlib import Path

# Load Cohezion IV&V Engine
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
sys.path.insert(0, str(REPO_ROOT / "src"))

from cohezion.compound.ivv_engine import (
    IndependentVerifier,
    IVVCertificate,
    IVVGatekeeper,
    IVVSeverity,
)

NB_PATH = Path(__file__).resolve().parent / "casmi26-analog-baseline-fork-cohezion.ipynb"


def patch_notebook() -> None:
    print(f"Reading notebook: {NB_PATH}")
    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    # 1. Update Reranker Definition Cell
    cell_101_source = """
# ===================================================================================
#  Cohezion SOTA v15: IV&V Hardened 4-Channel Calibrated Reranker
# ===================================================================================
def canonical_ik14(smi, fallback_ik14=""):
    \"\"\"Official RDKit Tautomer Canonicalization (fixes 4.4% key defect).\"\"\"
    if not smi or not HAVE_RDKIT or te is None:
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

DIAG_NEUTRAL_LOSSES = {
    "H2O": (18.010565, "[OH,cOH,COOH]"),
    "NH3": (17.026549, "[NH2,NH,CONH2]"),
    "CO": (27.994915, "[C=O,c=O,C(=O)c]"),
    "CO2": (43.989829, "[C(=O)O,c(=O)O]"),
    "CH3": (15.023475, "[CH3]"),
    "OCH3": (31.018390, "[OCH3,cOCH3]"),
    "CH3OH": (32.026179, "[C(=O)OCH3]"),
    "C2H4": (28.031300, "[CH2CH2]"),
    "HCOOH": (46.005479, "[C(=O)O]"),
    "CH3COOH": (60.021129, "[OC(=O)CH3]"),
}

def generate_insilico_fragments(smi, adduct_shift=1.007276):
    \"\"\"Predicts fragment ion m/z values and neutral losses from single cuts & diagnostic groups.\"\"\"
    if not HAVE_RDKIT:
        return []
    try:
        from rdkit.Chem import Descriptors
        m = Chem.MolFromSmiles(smi)
        if m is None:
            return []
        mol_no_h = Chem.RemoveHs(m)
        prec_mass = Descriptors.ExactMolWt(mol_no_h)
        prec_mz = prec_mass + adduct_shift
        frags = []
        seen = set()

        cleavable = [b.GetIdx() for b in mol_no_h.GetBonds()
                     if b.GetBondType() == Chem.BondType.SINGLE and not b.IsInRing()]
        for b_idx in cleavable:
            try:
                f_mol = Chem.FragmentOnBonds(mol_no_h, [b_idx], dummyLabels=[(0, 0)])
                for piece in Chem.GetMolFrags(f_mol, asMols=True):
                    clean = Chem.DeleteSubstructs(piece, Chem.MolFromSmiles("*"))
                    fm = Descriptors.ExactMolWt(clean)
                    if 15.0 <= fm < (prec_mass - 1.0):
                        frag_mz = fm + adduct_shift
                        k = round(frag_mz, 3)
                        if k not in seen:
                            seen.add(k)
                            frags.append((frag_mz, 1.0, "single_cut"))
            except Exception:
                continue

        for nl_name, (nl_mass, smarts) in DIAG_NEUTRAL_LOSSES.items():
            try:
                patt = Chem.MolFromSmarts(smarts)
                if patt and mol_no_h.HasSubstructMatch(patt):
                    frag_mz = prec_mz - nl_mass
                    if frag_mz > 15.0:
                        k = round(frag_mz, 3)
                        if k not in seen:
                            seen.add(k)
                            frags.append((frag_mz, 1.2, "diagnostic_nl"))
            except Exception:
                continue

        return frags
    except Exception:
        return []

def score_candidate_cleavages(smi, experimental_peaks, adduct_shift=1.007276, mz_tol=0.015):
    \"\"\"Matches simulated in-silico fragments against observed MS/MS peaks.\"\"\"
    frags = generate_insilico_fragments(smi, adduct_shift=adduct_shift)
    if not frags or not experimental_peaks:
        return 0.0, 0, frags

    total_score = 0.0
    matched_count = 0
    for f_mz, weight, f_type in frags:
        best_match_int = 0.0
        for exp_mz, exp_int in experimental_peaks:
            if abs(exp_mz - f_mz) <= mz_tol:
                if exp_int > best_match_int:
                    best_match_int = exp_int
        if best_match_int > 0.0:
            matched_count += 1
            total_score += weight * math.sqrt(best_match_int)

    return total_score, matched_count, frags

def compute_continuous_tanimoto(pred_probs, cand_fp):
    \"\"\"Continuous Tanimoto similarity between neural predicted fingerprint probs and candidate bits.\"\"\"
    if pred_probs is None or cand_fp is None or len(pred_probs) == 0 or len(cand_fp) == 0:
        return 0.0
    n = min(len(pred_probs), len(cand_fp))
    p = pred_probs[:n]
    c = cand_fp[:n]
    intersection = float(np.dot(p, c))
    sum_p = float(np.sum(p))
    sum_c = float(np.sum(c))
    denom = sum_p + sum_c - intersection
    if denom <= 1e-9 or not math.isfinite(denom):
        return 0.0
    sim = intersection / denom
    return max(0.0, min(1.0, sim)) if math.isfinite(sim) else 0.0

def compute_in_silico_spectral_entropy(experimental_peaks, pred_frags, tol=0.015):
    \"\"\"Computes spectral entropy similarity between experimental peaks and in-silico fragments.\"\"\"
    if not experimental_peaks or not pred_frags:
        return 0.0
    exp_mzs = np.array([p[0] for p in experimental_peaks], dtype=np.float32)
    exp_its = np.array([p[1] for p in experimental_peaks], dtype=np.float32)
    qm, qp = _clean(exp_mzs, exp_its, CFG.INT_FLOOR, CFG.MAX_PEAKS, 0.5, True)
    if len(qm) == 0:
        return 0.0
    sim_mzs = np.array([f[0] for f in pred_frags], dtype=np.float32)
    sim_its = np.array([0.8 if f[2] == "diagnostic_nl" else 0.5 for f in pred_frags], dtype=np.float32)
    cm, cp = _clean(sim_mzs, sim_its, 0.001, len(sim_mzs), 0.5, True)
    if len(cm) == 0:
        return 0.0
    try:
        sim = float(entropy_sim(qm, qp, cm, cp, tol))
        return sim if math.isfinite(sim) else 0.0
    except Exception:
        return 0.0

def rerank_candidates_v15(candidates_with_meta, experimental_peaks, target_neutral_mass,
                          pred_fingerprint_logits=None, adduct="[M+H]+",
                          w_gbdt=0.35, w_tanimoto=0.25, w_cleavage=0.25, w_entropy=0.15, w_ppm=0.0):
    \"\"\"SOTA v15 4-Channel Calibrated Reranker (Destabilizing Mass Penalty Eliminated).\"\"\"
    try:
        adduct_dict = globals().get("ADDUCTS", {})
        adduct_shift = adduct_dict.get(adduct, (1, 1, 1.007276))[2] if adduct in adduct_dict else 1.007276

        pred_probs = None
        if pred_fingerprint_logits is not None:
            clipped_logits = np.clip(pred_fingerprint_logits, -15.0, 15.0)
            pred_probs = 1.0 / (1.0 + np.exp(-clipped_logits))
            if np.isnan(pred_probs).any():
                pred_probs = np.nan_to_num(pred_probs, nan=0.0)

        reranked = []
        for smi, init_score, cand_fp, cand_mass in candidates_with_meta:
            try:
                c_score, n_matched, pred_frags = score_candidate_cleavages(
                    smi, experimental_peaks, adduct_shift=adduct_shift
                )
            except Exception:
                c_score, n_matched, pred_frags = 0.0, 0, []

            t_score = compute_continuous_tanimoto(pred_probs, cand_fp)
            ent_score = compute_in_silico_spectral_entropy(experimental_peaks, pred_frags)

            # Guards against NaN/Inf in scores
            c_score = 0.0 if not math.isfinite(c_score) else c_score
            t_score = 0.0 if not math.isfinite(t_score) else t_score
            ent_score = 0.0 if not math.isfinite(ent_score) else ent_score
            init_val = float(init_score) if math.isfinite(float(init_score)) else 0.0

            norm_c_score = min(1.0, max(0.0, c_score / 2.5))

            # Restored calibrated weights: w_gbdt=0.35, w_tanimoto=0.25, w_cleavage=0.25, w_entropy=0.15
            fused = (
                w_gbdt * init_val +
                w_tanimoto * float(t_score) +
                w_cleavage * float(norm_c_score) +
                w_entropy * float(ent_score)
            )
            if not math.isfinite(fused):
                fused = init_val

            reranked.append((smi, fused, c_score, t_score, ent_score, 0.0))

        reranked.sort(key=lambda x: (x[1] if math.isfinite(x[1]) else -1e9), reverse=True)
        return reranked
    except Exception:
        return [(item[0], float(item[1]) if math.isfinite(float(item[1])) else 0.0, 0.0, 0.0, 0.0, 0.0) for item in candidates_with_meta]
"""

    # 2. Update Run / Submission Cell
    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") != "code":
            continue
        src = "".join(cell.get("source", []))
        if "Cohezion SOTA v14" in src or "rerank_candidates_v14" in src:
            nb["cells"][idx]["source"] = [line + "\n" for line in cell_101_source.strip().split("\n")]
            print(f"Patched reranker definitions in cell {idx}")
        elif "reranked = rerank_candidates_v14(" in src:
            updated_src = src.replace("rerank_candidates_v14(", "rerank_candidates_v15(")
            updated_src = updated_src.replace("w_gbdt=0.25,", "w_gbdt=0.35,")
            updated_src = updated_src.replace("w_cleavage=0.20,", "w_cleavage=0.25,")
            updated_src = updated_src.replace("w_ppm=0.15", "w_ppm=0.0")
            nb["cells"][idx]["source"] = [line + "\n" for line in updated_src.strip().split("\n")]
            print(f"Patched execution weights in cell {idx}")

    # Write patched notebook
    with open(NB_PATH, "w", encoding="utf-8") as f:
        json.dump(nb, f, indent=1)
    print("Saved patched notebook successfully.")


def verify_ast() -> bool:
    print("Running AST verification across all cells...")
    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    for idx, cell in enumerate(nb["cells"]):
        if cell.get("cell_type") == "code":
            code = "".join(cell.get("source", []))
            try:
                ast.parse(code)
            except SyntaxError as e:
                print(f"❌ SyntaxError in cell {idx}: {e}")
                return False
    print("✓ All cells parsed successfully with 0 AST syntax errors.")
    return True


def run_ivv_audit() -> IVVCertificate:
    print("\nExecuting IV&V independent audit...")
    with open(NB_PATH, "r", encoding="utf-8") as f:
        nb = json.load(f)

    code_str = "\n".join(
        "".join(c.get("source", []))
        for c in nb.get("cells", [])
        if c.get("cell_type") == "code"
    )

    verifier = IndependentVerifier(verifier_id="independent-casmi26-auditor")
    cert = verifier.audit_code_artifact(
        artifact_id="manderson240/casmi26-analog-baseline-fork-cohezion:v15",
        creator_id="casmi26-creator",
        code_str=code_str,
        requirements_spec={"competition_type": "enveda-CASMI26-molecule-id-mass-spectra"},
    )

    gatekeeper = IVVGatekeeper()
    gatekeeper.register_certificate(cert)
    approved, msg = gatekeeper.verify_deployment_readiness(
        artifact_id="manderson240/casmi26-analog-baseline-fork-cohezion:v15",
        creator_id="casmi26-creator",
    )
    if not approved:
        print(f"❌ IV&V Deployment Rejected: {msg}")
        sys.exit(1)

    print(f"✓ {msg}")
    print(f"  Certificate Hash: {cert.signature}")
    return cert


if __name__ == "__main__":
    patch_notebook()
    if not verify_ast():
        sys.exit(1)
    cert = run_ivv_audit()
    print("\nReady for Kaggle push and notebook submission dispatch.")
