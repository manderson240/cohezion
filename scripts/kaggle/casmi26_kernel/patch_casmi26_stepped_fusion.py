#!/usr/bin/env python3
"""Patch CASMI26 notebook with Stepped Collision Energy Fusion, Adduct Mass Gating, and InChIKey14 Deduplication.

Replaces the 0.328 plateau 'max(s_e)' lottery-ticket aggregator with:
1. Variance-Penalized Stepped CE Fusion (S(c) = sum w_e s_e - 0.30 Var_e).
2. Adduct-aware Gaussian precursor mass soft-weighting (sigma = 6.0 ppm).
3. InChIKey14 deduplication across top-25 candidate lists.
"""

import json
import re
import sys

NOTEBOOK_PATH = "scripts/kaggle/casmi26_kernel/casmi26-analog-baseline-fork-cohezion.ipynb"

with open(NOTEBOOK_PATH, "r") as f:
    nb = json.load(f)

# 1. Patch Cell 7: Add fusion & gating functions, update lib_sim and analog_sim
cell7_src = nb["cells"][7]["source"]
if isinstance(cell7_src, list):
    cell7_src = "".join(cell7_src)

stepped_ce_block = '''
# ===================================================================================
#  Cohezion SOTA v8: Variance-Penalized Stepped Collision Energy Fusion & Adduct Gating
# ===================================================================================
DEFAULT_CE_WEIGHTS = {20.0: 0.50, 40.0: 0.35, 60.0: 0.15}

def fuse_stepped_collision_energies(sims_by_ce, weights=DEFAULT_CE_WEIGHTS, lambda_var=0.30):
    """Variance-penalized stepped collision energy fusion:
       S(c) = sum(w_e * s_e) - lambda * Var_e(s_e).
       Penalizes single-energy false positive spikes while rewarding consistent matches.
    """
    if not sims_by_ce:
        return 0.0
    avail_ces = list(sims_by_ce.keys())
    w_subset = {ce: weights.get(ce, 1.0 / len(avail_ces)) for ce in avail_ces}
    tot_w = sum(w_subset.values())
    norm_w = {ce: w / tot_w for ce, w in w_subset.items()}
    mean_val = sum(norm_w[ce] * sims_by_ce[ce] for ce in avail_ces)
    var_val = float(np.var([sims_by_ce[ce] for ce in avail_ces])) if len(avail_ces) > 1 else 0.0
    return float(max(0.0, mean_val - lambda_var * var_val))

ADDUCT_DELTAS = {
    "[M+H]+": (1.0, 1.0, 1.007276),
    "[M+Na]+": (1.0, 1.0, 22.989218),
    "[M+NH4]+": (1.0, 1.0, 18.033823),
    "[M+K]+": (1.0, 1.0, 38.963158),
    "[2M+H]+": (2.0, 1.0, 1.007276),
    "[2M+Na]+": (2.0, 1.0, 22.989218),
    "[M-H]-": (1.0, 1.0, -1.007276),
    "[M+Cl]-": (1.0, 1.0, 34.969402),
    "[M+HCOO]-": (1.0, 1.0, 44.998201),
}
ADDUCT_PRIORS = {
    "[M+H]+": 0.79,
    "[M+Na]+": 0.08,
    "[M+NH4]+": 0.05,
    "[2M+H]+": 0.03,
    "[M+K]+": 0.02,
    "[M-H]-": 0.03,
}

def compute_precursor_mass_weight(observed_mz, candidate_neutral_mass, sigma_ppm=6.0):
    """Adduct-aware Gaussian precursor mass soft-weighting for candidate molecules."""
    best_w = 0.0
    for adduct, prior in ADDUCT_PRIORS.items():
        if adduct not in ADDUCT_DELTAS:
            continue
        n, z, d = ADDUCT_DELTAS[adduct]
        expected_mz = (n * candidate_neutral_mass + d) / z
        ppm_err = abs(observed_mz - expected_mz) / expected_mz * 1e6
        g_prob = math.exp(-0.5 * (ppm_err / sigma_ppm) ** 2)
        w = g_prob * prior
        if w > best_w:
            best_w = w
    return float(best_w)

def lib_sim(L, specs, target):
    """CLASS 1: direct match against library spectra with variance-penalized stepped CE fusion."""
    cand = lib_window(L, target, target * CFG.PPM_WIN / 1e6)
    if len(cand) == 0:
        return {}
    sims_by_ce = {}
    for item in specs:
        mz, it = item[0], item[1]
        ce = item[2] if len(item) > 2 else 40.0
        qm, qp = clean(mz, it)
        if len(qm) == 0:
            continue
        sc = search(qm, qp, cand, L['off'], L['mz'], L['it'],
                    CFG.MZ_TOL, CFG.INT_FLOOR, CFG.MAX_PEAKS, CFG.INT_POWER, CFG.ENT_WEIGHT, 1)
        for c, s in zip(cand, sc):
            k = L['ik'][c]
            if k not in sims_by_ce:
                sims_by_ce[k] = {}
            if s > sims_by_ce[k].get(ce, -1.0):
                sims_by_ce[k][ce] = float(s)
    return {k: fuse_stepped_collision_energies(c_dict) for k, c_dict in sims_by_ce.items()}

def analog_sim(L, specs, target, rep, rep_key, rep_nm):
    """CLASS 2: mass-SHIFTED match over a wide window with variance-penalized stepped CE fusion."""
    lo = np.searchsorted(rep_nm, target - CFG.ANALOG_WIN, 'left')
    hi = np.searchsorted(rep_nm, target + CFG.ANALOG_WIN, 'right')
    cand = rep[lo:hi]
    if len(cand) == 0:
        return []
    shift = (target - rep_nm[lo:hi]).astype(np.float32)
    ckey = rep_key[lo:hi]
    sims_by_ce = {}
    for item in specs:
        mz, it = item[0], item[1]
        ce = item[2] if len(item) > 2 else 40.0
        qm, qp = clean(mz, it)
        if len(qm) == 0:
            continue
        sc = search_shift(qm, qp, cand, L['off'], L['mz'], L['it'],
                          CFG.MZ_TOL, CFG.INT_FLOOR, CFG.MAX_PEAKS,
                          CFG.INT_POWER, CFG.ENT_WEIGHT, 1, shift)
        for c, k, s in zip(cand, ckey, sc):
            if k not in sims_by_ce:
                sims_by_ce[k] = {}
            if s > sims_by_ce[k].get(ce, -1.0):
                sims_by_ce[k][ce] = float(s)
    agg = {k: fuse_stepped_collision_energies(c_dict) for k, c_dict in sims_by_ce.items()}
    return sorted(agg.items(), key=lambda x: -x[1])[:CFG.N_ANALOG]
'''

# Find the start of def clean(mz, it) or def lib_sim
pattern = r"def lib_sim\(L, specs, target\):[\s\S]*?return sorted\(agg\.items\(\), key=lambda x: -x\[1\]\)\[:CFG\.N_ANALOG\]"
if re.search(pattern, cell7_src):
    cell7_src = re.sub(pattern, stepped_ce_block.strip(), cell7_src)
    print("✓ Successfully patched Cell 7 with stepped CE fusion and mass gating!")
else:
    print("Warning: Could not match exact regex pattern in Cell 7, checking direct replace...")
    idx = cell7_src.find("def lib_sim(L, specs, target):")
    if idx != -1:
        cell7_src = cell7_src[:idx] + stepped_ce_block.strip() + "\n"
        print("✓ Successfully replaced lib_sim / analog_sim in Cell 7 via index!")
    else:
        print("Error: Could not find def lib_sim in Cell 7!")
        sys.exit(1)

nb["cells"][7]["source"] = cell7_src

# 2. Patch Cell 15: Safe unpacking in frag_scores
cell15_src = nb["cells"][15]["source"]
if isinstance(cell15_src, list):
    cell15_src = "".join(cell15_src)

cell15_src = cell15_src.replace(
    "for mz, it in specs:",
    "for item in specs:\n        mz, it = item[0], item[1]"
)
nb["cells"][15]["source"] = cell15_src
print("✓ Successfully patched Cell 15 frag_scores safe unpacking!")

# 3. Patch Cell 22: Pass collision energy in specs, apply precursor mass soft-weighting, and InChIKey14 deduplication
cell22_src = nb["cells"][22]["source"]
if isinstance(cell22_src, list):
    cell22_src = "".join(cell22_src)

old_loop_block = """        target = float(np.median(nms))                       # fuse all spectra of the molecule
        specs  = [(r.ms2_mzs, r.ms2_normalized_intensities) for r in sub.itertuples()]

        # Channel 1: Direct library matches
        lib_hits = lib_sim(L, specs, target)

        # Channel 2: Mass-shifted analog propagation
        analogs  = analog_sim(L, specs, target, rep, rep_key, rep_nm)

        # Tight candidate window (10 ppm) preserves peak precision
        cand = pool.window(target, CFG.PPM_WIN)
        if len(cand) == 0:
            cand = pool.window(target, CFG.PPM_FALLBACK)
        if len(cand):
            cfp = pool.fps(cand)
            lv  = np.array([lib_hits.get(pool.keys[c], 0.0) for c in cand], np.float32)
            ids, sims = [], []
            for k, s in analogs:
                i = pool.k2i.get(k, -1)
                if i >= 0: ids.append(i); sims.append(s)
            afp = pool.fps(np.array(ids)) if ids else None
            fsc = frag_scores([pool.smiles[c] for c in cand], specs,
                              float(np.mean([1.0 if m == 'positive' else -1.0
                                             for m in sub.ionization_mode])))
            zlog = model_logits(sub)
            X   = rank_features(cfp, lv, afp, np.array(sims, np.float32), zlog, fsc)[:, :NFEAT]
            p   = rank_proba(X)
            order = np.argsort(-p)[:CFG.TOPN]
            smis  = [pool.smiles[cand[i]] for i in order]
            diag.append((mid, target, len(cand), float(lv.max()),
                         float(sims[0]) if sims else 0.0, float(p[order[0]])))

        # Safe Tail Expansion: If tight window had <25 candidates, expand window for tail slots ONLY
        # This guarantees 0 demotion for top-ranked tight candidates while filling remaining slots
        if len(smis) < CFG.TOPN:
            seen_smis = set(smis)
            for expansion_win in [15.0, 30.0, 50.0]:
                extra_cand = pool.window(target, expansion_win)
                for ec in extra_cand:
                    smi_c = pool.smiles[ec]
                    if smi_c not in seen_smis:
                        smis.append(smi_c)
                        seen_smis.add(smi_c)
                        if len(smis) >= CFG.TOPN:
                            break
                if len(smis) >= CFG.TOPN:
                    break"""

new_loop_block = """        target = float(np.median(nms))                       # fuse all spectra of the molecule
        specs = []
        for r in sub.itertuples():
            ce = 40.0
            if hasattr(r, 'collision_energy_ev'):
                cev = r.collision_energy_ev
                if isinstance(cev, (list, tuple, np.ndarray)) and len(cev) > 0:
                    ce = float(cev[0])
                elif isinstance(cev, (int, float)) and not np.isnan(cev):
                    ce = float(cev)
            specs.append((r.ms2_mzs, r.ms2_normalized_intensities, ce))

        # Channel 1: Direct library matches (stepped CE fusion)
        lib_hits = lib_sim(L, specs, target)

        # Channel 2: Mass-shifted analog propagation (stepped CE fusion)
        analogs  = analog_sim(L, specs, target, rep, rep_key, rep_nm)

        # Tight candidate window (10 ppm) preserves peak precision
        cand = pool.window(target, CFG.PPM_WIN)
        if len(cand) == 0:
            cand = pool.window(target, CFG.PPM_FALLBACK)
        if len(cand):
            cfp = pool.fps(cand)
            lv  = np.array([lib_hits.get(pool.keys[c], 0.0) for c in cand], np.float32)
            ids, sims = [], []
            for k, s in analogs:
                i = pool.k2i.get(k, -1)
                if i >= 0: ids.append(i); sims.append(s)
            afp = pool.fps(np.array(ids)) if ids else None
            fsc = frag_scores([pool.smiles[c] for c in cand], specs,
                              float(np.mean([1.0 if m == 'positive' else -1.0
                                             for m in sub.ionization_mode])))
            zlog = model_logits(sub)
            X   = rank_features(cfp, lv, afp, np.array(sims, np.float32), zlog, fsc)[:, :NFEAT]
            p   = rank_proba(X)

            # Gaussian adduct-aware precursor mass soft-weighting
            obs_mz = float(np.median(sub.precursor_mz))
            mass_weights = np.array([compute_precursor_mass_weight(obs_mz, float(pool.mass[c]), sigma_ppm=6.0)
                                     for c in cand], dtype=np.float32)
            p_calibrated = p * (0.70 + 0.30 * mass_weights)
            order = np.argsort(-p_calibrated)

            # InChIKey14 deduplication: never waste slots on duplicate tautomers/stereoisomers
            seen_ik14 = set()
            smis = []
            for idx in order:
                ik14 = pool.keys[cand[idx]]
                if ik14 not in seen_ik14:
                    seen_ik14.add(ik14)
                    smis.append(pool.smiles[cand[idx]])
                    if len(smis) >= CFG.TOPN:
                        break

            diag.append((mid, target, len(cand), float(lv.max()) if len(lv) else 0.0,
                         float(sims[0]) if sims else 0.0, float(p_calibrated[order[0]]) if len(order) else 0.0))

        # Safe Tail Expansion with InChIKey14 Deduplication
        if len(smis) < CFG.TOPN:
            seen_smis = set(smis)
            seen_ik14 = {pool.k2i.get(s, s) for s in smis}
            for expansion_win in [15.0, 30.0, 50.0]:
                extra_cand = pool.window(target, expansion_win)
                for ec in extra_cand:
                    ik14_ec = pool.keys[ec]
                    smi_c = pool.smiles[ec]
                    if ik14_ec not in seen_ik14 and smi_c not in seen_smis:
                        smis.append(smi_c)
                        seen_ik14.add(ik14_ec)
                        seen_smis.add(smi_c)
                        if len(smis) >= CFG.TOPN:
                            break
                if len(smis) >= CFG.TOPN:
                    break"""

if old_loop_block in cell22_src:
    cell22_src = cell22_src.replace(old_loop_block, new_loop_block)
    print("✓ Successfully patched Cell 22 candidate scoring and deduplication loop!")
else:
    print("Warning: Could not do exact string replace in Cell 22, checking normalized spacing...")
    # Normalize line endings and whitespace
    old_norm = "\n".join(line.rstrip() for line in old_loop_block.split("\n"))
    cell22_norm = "\n".join(line.rstrip() for line in cell22_src.split("\n"))
    if old_norm in cell22_norm:
        cell22_norm = cell22_norm.replace(old_norm, new_loop_block)
        cell22_src = cell22_norm
        print("✓ Successfully replaced loop in Cell 22 after whitespace normalization!")
    else:
        print("Error: Could not match old loop block in Cell 22!")
        sys.exit(1)

nb["cells"][22]["source"] = cell22_src

# Save updated notebook
with open(NOTEBOOK_PATH, "w") as f:
    json.dump(nb, f, indent=1)

print(f"✓ Successfully wrote updated notebook to {NOTEBOOK_PATH}")
