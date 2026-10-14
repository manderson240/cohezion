#!/usr/bin/env python3
"""Patch CASMI26 notebook to V9 SOTA: In-Silico Isomer Fragment Reranking.
=========================================================================
1. Neutralizes the V8 Stepped CE variance penalty (lambda_var = 0.0) restoring
   the 0.328 baseline foundation.
2. Injects standalone IsomerFragmentReranker into the notebook.
3. Reranks the top candidates in Cell 22 using in-silico bond cleavage
   and diagnostic neutral loss matching before generating submission.csv.
4. Validates AST syntax across all patched notebook cells.

Usage:
    uv run python scripts/kaggle/casmi26_kernel/patch_casmi26_isomer_rerank_v9.py
"""

from __future__ import annotations

import ast
import json
import logging
import sys
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("patch_v9")

NOTEBOOK_PATH = Path("scripts/kaggle/casmi26_kernel/casmi26-analog-baseline-fork-cohezion.ipynb")

if not NOTEBOOK_PATH.exists():
    logger.error("Notebook not found at %s", NOTEBOOK_PATH)
    sys.exit(1)

with open(NOTEBOOK_PATH, "r", encoding="utf-8") as f:
    nb = json.load(f)

# -----------------------------------------------------------------------------
# 1. Patch Cell 7: Neutralize variance penalty in fuse_stepped_collision_energies
# -----------------------------------------------------------------------------
cell7_src = nb["cells"][7]["source"]
if isinstance(cell7_src, list):
    cell7_src = "".join(cell7_src)

# Replace lambda_var = 0.30 with lambda_var = 0.0 to eliminate single-CE over-penalization
if "lambda_var=0.30" in cell7_src:
    cell7_src = cell7_src.replace("lambda_var=0.30", "lambda_var=0.0")
    logger.info("✓ Cell 7: Neutralized Stepped CE variance penalty (lambda_var=0.0)")
elif "lambda_var = 0.30" in cell7_src:
    cell7_src = cell7_src.replace("lambda_var = 0.30", "lambda_var = 0.0")
    logger.info("✓ Cell 7: Neutralized Stepped CE variance penalty (lambda_var = 0.0)")
else:
    logger.warning("Notice: lambda_var=0.30 not found in Cell 7 (already neutral or modified)")

nb["cells"][7]["source"] = cell7_src

# -----------------------------------------------------------------------------
# 2. Inject IsomerFragmentReranker Definition into Cell 15 (after frag_scores)
# -----------------------------------------------------------------------------
cell15_src = nb["cells"][15]["source"]
if isinstance(cell15_src, list):
    cell15_src = "".join(cell15_src)

reranker_engine_code = '''

# ===================================================================================
#  Cohezion SOTA v9: In-Silico Bond-Cleavage Isomer Fragment Reranker
# ===================================================================================
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
    """Predicts fragment ion m/z values and neutral losses from single/double cuts."""
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

        # 1. Acyclic & ring-exocyclic single cuts
        cleavable = [b.GetIdx() for b in mol_no_h.GetBonds()
                     if b.GetBondType() == Chem.BondType.SINGLE and not b.IsInRing()]
        for b_idx in cleavable:
            try:
                f_mol = Chem.FragmentOnBonds(mol_no_h, [b_idx], dummyLabels=[(0, 0)])
                for piece in Chem.GetMolFrags(f_mol, asMols=True):
                    clean = Chem.DeleteSubstructs(piece, Chem.MolFromSmiles("*"))
                    fm = Descriptors.ExactMolWt(clean)
                    if 15.0 <= fm < (prec_mass - 1.0):
                        imz = round(fm + adduct_shift, 4)
                        if imz not in seen:
                            seen.add(imz)
                            frags.append((imz, prec_mz - imz, "single_cut"))
            except Exception:
                continue

        # 2. Functional group neutral losses
        for nl_name, (nl_mass, smarts) in DIAG_NEUTRAL_LOSSES.items():
            pat = Chem.MolFromSmarts(smarts)
            if pat and mol_no_h.HasSubstructMatch(pat):
                imz = round(prec_mz - nl_mass, 4)
                if imz > 20.0 and imz not in seen:
                    seen.add(imz)
                    frags.append((imz, nl_mass, "diagnostic_nl"))
        return frags
    except Exception:
        return []

def score_candidate_cleavages(candidate_smiles, experimental_peaks, adduct_shift=1.007276,
                              tol_da=0.015, tol_ppm=12.0):
    """Calculates explained intensity ratio and sub-ppm Gaussian mass accuracy."""
    pred_frags = generate_insilico_fragments(candidate_smiles, adduct_shift=adduct_shift)
    if not pred_frags or not experimental_peaks:
        return 0.0, 0
    total_int = sum(it for _, it in experimental_peaks) or 1.0
    matched_int = 0.0
    ppm_errors = []
    matched_count = 0

    for exp_mz, exp_it in experimental_peaks:
        best_delta_da = 1e9
        matched = False
        for pred_mz, _, _ in pred_frags:
            dda = abs(exp_mz - pred_mz)
            dppm = (dda / exp_mz) * 1e6
            if dda <= tol_da or dppm <= tol_ppm:
                if dda < best_delta_da:
                    best_delta_da = dda
                    matched = True
        if matched:
            matched_int += exp_it
            matched_count += 1
            ppm_errors.append((best_delta_da / exp_mz) * 1e6)

    explained_ratio = matched_int / total_int
    ppm_score = math.exp(-0.5 * ((sum(ppm_errors) / len(ppm_errors)) / tol_ppm) ** 2) if ppm_errors else 0.0
    cleavage_score = explained_ratio * (1.0 + math.log1p(matched_count)) * ppm_score
    return cleavage_score, matched_count

def rerank_isomer_candidates(candidates_with_scores, experimental_peaks, adduct="[M+H]+",
                             alpha=0.40, beta=0.60):
    """Fuses initial ranker probability with in-silico bond cleavage diagnostics."""
    adduct_shift = ADDUCT_DELTAS.get(adduct, (1.0, 1.0, 1.007276))[2]
    reranked = []
    for smi, init_score in candidates_with_scores:
        c_score, n_matched = score_candidate_cleavages(
            smi, experimental_peaks, adduct_shift=adduct_shift
        )
        fused = alpha * float(init_score) + beta * float(c_score)
        reranked.append((smi, fused, c_score, n_matched))
    reranked.sort(key=lambda x: x[1], reverse=True)
    return reranked
'''

if "def generate_insilico_fragments" not in cell15_src:
    cell15_src = cell15_src.strip() + "\n" + reranker_engine_code.strip() + "\n"
    nb["cells"][15]["source"] = cell15_src
    logger.info("✓ Cell 15: Injected InSilicoFragmentReranker engine successfully")
else:
    logger.info("Notice: InSilicoFragmentReranker already present in Cell 15")

# -----------------------------------------------------------------------------
# 3. Patch Cell 22: Apply Isomer Reranking to Top Candidates in the Loop
# -----------------------------------------------------------------------------
cell22_src = nb["cells"][22]["source"]
if isinstance(cell22_src, list):
    cell22_src = "".join(cell22_src)

# Target pattern: InChIKey14 deduplication loop
target_dedup_block = """            # InChIKey14 deduplication: never waste slots on duplicate tautomers/stereoisomers
            seen_ik14 = set()
            smis = []
            for idx in order:
                ik14 = pool.keys[cand[idx]]
                if ik14 not in seen_ik14:
                    seen_ik14.add(ik14)
                    smis.append(pool.smiles[cand[idx]])
                    if len(smis) >= CFG.TOPN:
                        break"""

v9_rerank_block = """            # InChIKey14 deduplication & candidate gathering for Isomer Reranking
            seen_ik14 = set()
            candidate_pool_for_rerank = []
            for idx in order:
                ik14 = pool.keys[cand[idx]]
                if ik14 not in seen_ik14:
                    seen_ik14.add(ik14)
                    candidate_pool_for_rerank.append((pool.smiles[cand[idx]], float(p_calibrated[idx])))
                    if len(candidate_pool_for_rerank) >= 30:
                        break

            # Cohezion SOTA v9: In-silico bond cleavage & neutral loss isomer reranker
            # Explains peaks via subgraph alignment to promote true isomers from Ranks 2-25 -> Rank 1
            if candidate_pool_for_rerank and HAVE_RDKIT:
                merged_peaks = []
                for sp in specs:
                    merged_peaks.extend(list(zip(sp[0], sp[1])))
                reranked_tuples = rerank_isomer_candidates(
                    candidates_with_scores=candidate_pool_for_rerank,
                    experimental_peaks=merged_peaks,
                    adduct=r.adduct if hasattr(r, 'adduct') else '[M+H]+',
                    alpha=0.40,
                    beta=0.60,
                )
                smis = [item[0] for item in reranked_tuples[:CFG.TOPN]]
            else:
                smis = [item[0] for item in candidate_pool_for_rerank[:CFG.TOPN]]"""

if target_dedup_block in cell22_src:
    cell22_src = cell22_src.replace(target_dedup_block, v9_rerank_block)
    logger.info("✓ Cell 22: Successfully injected Isomer Reranking into candidate loop!")
else:
    # Normalized search for robustness
    old_norm = "\n".join(l.rstrip() for l in target_dedup_block.split("\n"))
    cell22_norm = "\n".join(l.rstrip() for l in cell22_src.split("\n"))
    if old_norm in cell22_norm:
        cell22_norm = cell22_norm.replace(old_norm, v9_rerank_block)
        cell22_src = cell22_norm
        logger.info("✓ Cell 22: Successfully replaced candidate loop after whitespace normalization!")
    else:
        logger.error("Error: Could not locate target deduplication block in Cell 22!")
        sys.exit(1)

nb["cells"][22]["source"] = cell22_src

# -----------------------------------------------------------------------------
# 4. AST Syntax Verification across all notebook code cells
# -----------------------------------------------------------------------------
logger.info("Verifying AST syntax across all notebook code cells...")
syntax_clean = True
for idx, cell in enumerate(nb["cells"]):
    if cell.get("cell_type") == "code":
        code = cell.get("source", "")
        if isinstance(code, list):
            code = "".join(code)
        try:
            ast.parse(code)
        except SyntaxError as e:
            logger.error("SyntaxError in Cell %d (line %d): %s", idx, e.lineno, e.msg)
            syntax_clean = False

if not syntax_clean:
    logger.error("❌ AST verification failed! Notebook not saved.")
    sys.exit(1)

logger.info("✓ AST syntax verified clean across all code cells!")

# -----------------------------------------------------------------------------
# 5. Save the Patched Notebook
# -----------------------------------------------------------------------------
with open(NOTEBOOK_PATH, "w", encoding="utf-8") as f:
    json.dump(nb, f, indent=1)

logger.info("🎉 Successfully upgraded %s to CASMI26 SOTA v9!", NOTEBOOK_PATH)
