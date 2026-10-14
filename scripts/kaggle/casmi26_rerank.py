"""CASMI26 joint re-ranker: adduct-surrogate ICEBERG scoring + bond-cleavage parsimony + priors.

Score(m) = z(S_ICE) + mu_pop * z(log(1 + PubChemCount)) + lam_frag * z(S_MetFrag) + delta_sub

* S_ICE is a log-sum-exp over the adduct hypotheses that are mass-consistent with the precursor,
  each scored by a *modified cosine* that lets ICEBERG's [M+H]+ peaks match at m/z or m/z + delta_A.
* S_MetFrag is a bitmask bond-cleavage matcher (<=2 cuts, H-transfer penalty), run lazily.
* delta_sub is a bounded diagnostic-ion / neutral-loss substructure term.

Needs numpy + rdkit. `python casmi26_rerank.py --selftest` runs the checks.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass, field
from functools import lru_cache

import numpy as np
from rdkit import Chem, RDLogger
from rdkit.Chem import Descriptors


RDLogger.DisableLog("rdApp.*")

PROTON = 1.007276466812
H_ATOM = 1.00782503223
ELECTRON = 0.000548579909
H2O = 18.010564684
NH3 = 17.026549101
NA = 22.989769282

ADDUCT_SHIFT = {  # ion m/z = neutral monoisotopic mass + shift
    "[M+H]+": PROTON,
    "[M+NH4]+": NH3 + PROTON,
    "[M+Na]+": NA - ELECTRON,
    "[M-H2O+H]+": PROTON - H2O,
    "[M+H-2H2O]+": PROTON - 2 * H2O,
}
ADDUCT_PRIOR = {
    "[M+H]+": 0.55,
    "[M+NH4]+": 0.15,
    "[M-H2O+H]+": 0.15,
    "[M+Na]+": 0.12,
    "[M+H-2H2O]+": 0.03,
}


def adduct_delta(adduct: str) -> float:
    """Shift of the observed precursor relative to [M+H]+ (the frame ICEBERG predicts in)."""
    return ADDUCT_SHIFT[adduct] - PROTON


def tol_da(mz, ppm: float = 15.0, floor: float = 0.003):
    return np.maximum(np.asarray(mz, float) * ppm * 1e-6, floor)


@dataclass
class Query:
    precursor_mz: float
    mz: np.ndarray
    intensity: np.ndarray
    adduct: str | None = None

    def __post_init__(self):
        mz, it = np.asarray(self.mz, float), np.asarray(self.intensity, float)
        keep = (it > 0) & np.isfinite(mz) & np.isfinite(it)
        mz, it = mz[keep], it[keep]
        order = np.argsort(mz)
        self.mz, self.intensity = mz[order], (it[order] / it.max() if it.size else it)


@dataclass
class Candidate:
    smiles: str
    ice_mz: np.ndarray | None = None  # ICEBERG forward prediction, [M+H]+ frame
    ice_int: np.ndarray | None = None
    pubchem_count: int | None = None  # None = lookup failed (imputed); 0 = genuinely absent


@dataclass
class Config:
    mu_pop: float = 0.42
    lam_frag: float = 0.35
    w_sub: float = 1.0
    sub_cap: float = 1.0
    tau_ice: float = 0.10  # log-sum-exp temperature over adducts
    gamma_shift: float = 0.85  # down-weight of matches made through the adduct shift
    ppm: float = 15.0
    mass_ppm: float = 10.0
    count_cap: float = 1e5  # log1p cap so mega-popular compounds cannot dominate
    tau_frag: float = 2.0
    mf_topk: int = 60
    mf_max_heavy: int = 70
    scale_mode: str = "robust"  # "robust" = per-query median/MAD units, "raw" = as-is
    min_spread: dict = field(default_factory=lambda: {"ice": 0.05, "pop": 0.5, "mf": 0.05})
    hard_mass_filter: bool = True


# ----------------------------------------------------------------------------- molecule cache
@lru_cache(maxsize=300_000)
def mol_info(smiles: str):
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    try:
        key14 = Chem.MolToInchiKey(mol)[:14]
    except Exception:
        key14 = smiles
    return mol, Descriptors.ExactMolWt(mol), key14


# ----------------------------------------------------------------------------- S_ICE
def modified_cosine(q_mz, q_int, p_mz, p_int, delta: float, gamma: float, ppm: float) -> float:
    """One-to-one greedy cosine; a predicted peak p matches q at p (weight 1) or p + delta (gamma)."""
    q_mz, p_mz = np.asarray(q_mz, float), np.asarray(p_mz, float)
    if q_mz.size == 0 or p_mz.size == 0:
        return 0.0
    qs, ps = np.sqrt(q_int), np.sqrt(p_int)
    tol = tol_da(q_mz, ppm)[:, None]
    ok0 = np.abs(q_mz[:, None] - p_mz[None, :]) <= tol
    ok1 = (np.abs(q_mz[:, None] - (p_mz[None, :] + delta)) <= tol) & (abs(delta) > 1e-6)
    w = np.where(ok0, 1.0, np.where(ok1, gamma, 0.0))
    prod = w * qs[:, None] * ps[None, :]
    used_q, used_p, total = np.zeros(q_mz.size, bool), np.zeros(p_mz.size, bool), 0.0
    for flat in np.argsort(-prod, axis=None):
        v = prod.flat[flat]
        if v <= 0:
            break
        i, j = divmod(int(flat), p_mz.size)
        if not (used_q[i] or used_p[j]):
            used_q[i] = used_p[j] = True
            total += v
    return float(total / (np.linalg.norm(qs) * np.linalg.norm(ps)))


def adduct_hypotheses(query: Query, neutral_mass: float, mass_ppm: float) -> list[str]:
    names = [query.adduct] if query.adduct else list(ADDUCT_PRIOR)
    tol = float(tol_da(query.precursor_mz, mass_ppm, 0.002))
    return [a for a in names if abs(neutral_mass + ADDUCT_SHIFT[a] - query.precursor_mz) <= tol]


def ice_score(query: Query, cand: Candidate, hyps: list[str], cfg: Config) -> float | None:
    """tau * log sum_A pi_A exp(cos_A / tau), pi renormalised over mass-consistent adducts."""
    if cand.ice_mz is None or len(cand.ice_mz) == 0 or not hyps:
        return None
    p_mz = np.asarray(cand.ice_mz, float)
    p_int = np.asarray(cand.ice_int, float)
    p_int = p_int / p_int.max()
    pri = np.array([ADDUCT_PRIOR[a] for a in hyps])
    pri = pri / pri.sum()
    sims = np.array(
        [
            modified_cosine(
                query.mz, query.intensity, p_mz, p_int, adduct_delta(a), cfg.gamma_shift, cfg.ppm
            )
            for a in hyps
        ]
    )
    t = cfg.tau_ice
    return float(t * np.log(np.sum(pri * np.exp(sims / t))))


# ----------------------------------------------------------------------------- S_MetFrag
_BOND_COST = {
    Chem.BondType.SINGLE: 1.0,
    Chem.BondType.AROMATIC: 2.0,
    Chem.BondType.DOUBLE: 2.5,
    Chem.BondType.TRIPLE: 3.5,
}
_H_SHIFTS = np.array([1, 0, 2, -1, 3])  # H atoms added to the cut piece (1 = protonation)
_H_PEN = np.array([0.0, 0.5, 0.5, 1.0, 1.0])


@lru_cache(maxsize=300_000)
def fragment_table(smiles: str, max_heavy: int = 70):
    """All connected pieces from <=2 bond cuts: (neutral-sum masses, cut costs). Cached per SMILES."""
    info = mol_info(smiles)
    if info is None or info[0].GetNumHeavyAtoms() > max_heavy:
        return np.empty(0), np.empty(0)
    mol = info[0]
    pt = Chem.GetPeriodicTable()
    mass = [
        pt.GetMostCommonIsotopeMass(a.GetAtomicNum()) + a.GetTotalNumHs() * H_ATOM
        for a in mol.GetAtoms()
    ]
    adj = [[b.GetOtherAtomIdx(a.GetIdx()) for b in a.GetBonds()] for a in mol.GetAtoms()]
    bonds = [
        (b.GetBeginAtomIdx(), b.GetEndAtomIdx(), _BOND_COST.get(b.GetBondType(), 1.5))
        for b in mol.GetBonds()
    ]
    n = len(mass)
    best: dict[int, tuple[float, float]] = {}

    def components(cut):
        banned = {(i, j) for i, j, _ in cut} | {(j, i) for i, j, _ in cut}
        seen, comps = [False] * n, []
        for s in range(n):
            if seen[s]:
                continue
            stack, bits, m = [s], 0, 0.0
            seen[s] = True
            while stack:
                u = stack.pop()
                bits |= 1 << u
                m += mass[u]
                for v in adj[u]:
                    if not seen[v] and (u, v) not in banned:
                        seen[v] = True
                        stack.append(v)
            comps.append((bits, m))
        return comps

    def register(cut):
        comps = components(cut)
        if len(comps) < 2:
            return  # ring bond cut alone: nothing separates
        for bits, m in comps:
            cost = sum(c for i, j, c in cut if ((bits >> i) & 1) != ((bits >> j) & 1))
            if m >= 15.0 and (bits not in best or cost < best[bits][1]):
                best[bits] = (m, cost)

    for a in range(len(bonds)):
        register([bonds[a]])
        for b in range(a + 1, len(bonds)):
            register([bonds[a], bonds[b]])
    if not best:
        return np.empty(0), np.empty(0)
    arr = np.array(list(best.values()))
    return arr[:, 0], arr[:, 1]


def metfrag_score(query: Query, smiles: str, deltas: list[float], cfg: Config) -> float:
    """Intensity-weighted fraction of peaks explained by cheap cleavages, in [0, 1]."""
    masses, costs = fragment_table(smiles, cfg.mf_max_heavy)
    sel = query.mz < query.precursor_mz - 1.5  # precursor-region peaks explain nothing
    q_mz, q_w = query.mz[sel], np.sqrt(query.intensity[sel])
    if masses.size == 0 or q_mz.size == 0:
        return 0.0
    ions = (masses[:, None] + _H_SHIFTS[None, :] * H_ATOM - ELECTRON).ravel()
    pens = (costs[:, None] + _H_PEN[None, :]).ravel()
    order = np.argsort(ions)
    ions, pens = ions[order], pens[order]
    got = np.zeros(q_mz.size)
    for d in sorted(set([0.0] + [round(x, 6) for x in deltas])):
        gam = 1.0 if d == 0.0 else cfg.gamma_shift
        for k, q in enumerate(q_mz):
            t = float(tol_da(q, cfg.ppm))
            lo, hi = np.searchsorted(ions, [q - d - t, q - d + t])
            if hi > lo:
                got[k] = max(got[k], gam * math.exp(-pens[lo:hi].min() / cfg.tau_frag))
    return float((q_w * got).sum() / q_w.sum())


# ----------------------------------------------------------------------------- delta_substructure
def _smarts(s):
    return Chem.MolFromSmarts(s)


# (name, SMARTS, evidence [("loss", Da) | ("ion", mz)], weight, veto_ratio)
_RULES = [
    ("hexose", "[OX2]C1OC(CO)C(O)C(O)C1O", [("loss", 162.0528)], 0.8, 1.0),
    ("glucuronide", "[OX2]C1OC(C(=O)[OX2])C(O)C(O)C1O", [("loss", 176.0321)], 0.8, 1.0),
    ("deoxyhexose", "[OX2]C1OC([CH3])C(O)C(O)C1O", [("loss", 146.0579)], 0.8, 1.0),
    ("pentose", "[OX2]C1OCC(O)C(O)C1O", [("loss", 132.0423)], 0.8, 1.0),
    ("sulfate", "[#6]O[SX4](=O)(=O)[OX2,OX1-]", [("loss", 79.9568)], 0.6, 0.8),
    ("phosphate", "[#6]OP(=O)([OX2,OX1-])[OX2,OX1-]", [("loss", 97.9769)], 0.6, 0.8),
    ("carboxylic_acid", "[CX3](=O)[OX2H1,OX1-]", [("loss", 45.9929), ("loss", 43.9898)], 0.3, 0.3),
    ("phenyl", "c1ccccc1", [("ion", 77.0386)], 0.3, 0.3),
    ("benzyl", "c[CH2]", [("ion", 91.0542)], 0.3, 0.3),
    ("benzoyl", "c1ccccc1[CX3]=O", [("ion", 105.0335)], 0.4, 0.3),
    ("primary_amine", "[NX3;H2;!$(NC=O)]", [("loss", NH3)], 0.2, 0.2),
]
_RULES = [(n, _smarts(s), ev, w, v) for n, s, ev, w, v in _RULES]


def _evidence(query: Query, evid, deltas: list[float]) -> float:
    best = 0.0
    refs = {query.precursor_mz} | {query.precursor_mz - d for d in deltas}
    for kind, val in evid:
        for ref in refs if kind == "loss" else [None]:
            target = val if kind == "ion" else ref - val
            hit = np.abs(query.mz - target) <= tol_da(target)
            if hit.any():
                rel = float(query.intensity[hit].max())
                if rel >= 0.01:
                    best = max(best, min(1.0, rel / 0.05))
    return best


def substructure_delta(query: Query, smiles: str, deltas: list[float], cfg: Config) -> float:
    mol = mol_info(smiles)[0]
    total = 0.0
    for _name, patt, evid, w, veto in _RULES:
        e = _evidence(query, evid, deltas)
        if e > 0:
            total += w * e * (1.0 if mol.HasSubstructMatch(patt) else -veto)
    return cfg.w_sub * float(np.clip(total, -cfg.sub_cap, cfg.sub_cap))


# ----------------------------------------------------------------------------- joint ranking
@dataclass
class Ranked:
    smiles: str
    inchikey14: str
    score: float
    parts: dict
    adducts: list
    imputed: list


def _standardise(x: np.ndarray, floor: float, mode: str) -> np.ndarray:
    """Per-query robust z. `floor` stops a near-constant component being amplified into noise."""
    ok = ~np.isnan(x)
    out = np.zeros_like(x)
    if not ok.any():
        return out
    if mode == "raw":
        out[ok] = x[ok]
        return out
    med = np.median(x[ok])
    spread = max(1.4826 * np.median(np.abs(x[ok] - med)), floor)
    out[ok] = (x[ok] - med) / spread
    return out  # NaN -> 0 (= query median): missing evidence neither rewards nor punishes


def feature_matrix(query: Query, cands: list[Candidate], cfg: Config):
    """Rows kept (deduped by InChIKey14) + columns [z_ice, z_pop, z_mf, delta]."""
    rows = []
    for c in cands:
        info = mol_info(c.smiles)
        if info is None:
            continue
        _, mass, key = info
        hyps = adduct_hypotheses(query, mass, cfg.mass_ppm)
        if cfg.hard_mass_filter and not hyps:
            continue
        rows.append(dict(c=c, key=key, hyps=hyps, ice=ice_score(query, c, hyps, cfg)))
    if not rows:
        return [], np.empty((0, 4))
    n = len(rows)
    ice = np.array([np.nan if r["ice"] is None else r["ice"] for r in rows])
    cnt = [r["c"].pubchem_count for r in rows]
    known = [x for x in cnt if x is not None]
    fill = float(np.median(np.log1p(np.minimum(known, cfg.count_cap)))) if known else 0.0
    pop = np.array([fill if x is None else math.log1p(min(x, cfg.count_cap)) for x in cnt])

    z_ice = _standardise(ice, cfg.min_spread["ice"], cfg.scale_mode)
    z_pop = _standardise(pop, cfg.min_spread["pop"], cfg.scale_mode)

    # lazy MetFrag: top-K on provisional score, plus everything ICEBERG could not score
    prov = z_ice + cfg.mu_pop * z_pop
    todo = set(np.argsort(-prov)[: cfg.mf_topk]) | {i for i in range(n) if np.isnan(ice[i])}
    mf = np.full(n, np.nan)
    for i in todo:
        deltas = [adduct_delta(a) for a in rows[i]["hyps"]] or [0.0]
        mf[i] = metfrag_score(query, rows[i]["c"].smiles, deltas, cfg)
    z_mf = _standardise(mf, cfg.min_spread["mf"], cfg.scale_mode)

    sub = np.array(
        [
            substructure_delta(
                query, r["c"].smiles, [adduct_delta(a) for a in r["hyps"]] or [0.0], cfg
            )
            for r in rows
        ]
    )
    for i, r in enumerate(rows):
        r["imputed"] = [k for k, v in (("ice", ice[i]), ("mf", mf[i])) if np.isnan(v)]
    return rows, np.column_stack([z_ice, z_pop, z_mf, sub])


def rerank(
    query: Query, cands: list[Candidate], cfg: Config | None = None, top: int = 25
) -> list[Ranked]:
    cfg = cfg or Config()
    rows, F = feature_matrix(query, cands, cfg)
    if not rows:
        return []
    theta = np.array([1.0, cfg.mu_pop, cfg.lam_frag, 1.0])
    scores = F @ theta
    out, seen = [], set()
    for i in np.argsort(-scores):  # InChIKey14 dedupe: MRR@25 slots are scarce
        r = rows[i]
        if r["key"] in seen:
            continue
        seen.add(r["key"])
        out.append(
            Ranked(
                r["c"].smiles,
                r["key"],
                float(scores[i]),
                dict(zip(("ice", "pop", "mf", "sub"), map(float, F[i]))),
                r["hyps"],
                r["imputed"],
            )
        )
        if len(out) == top:
            break
    return out


# ----------------------------------------------------------------------------- calibration
def fit_weights(
    F_list: list[np.ndarray], true_idx: list[int], theta0=(1.0, 0.42, 0.35, 1.0), l2=1e-2
):
    """Listwise softmax NLL over per-query feature matrices; L2 pull toward theta0.

    Returns theta; report mu = theta[1]/theta[0], lam = theta[2]/theta[0]. Split train/val
    by MOLECULE (same InChIKey14 never on both sides) or the fit memorises the library.
    """
    from scipy.optimize import minimize

    th0 = np.asarray(theta0, float)

    def nll(th):
        loss, grad = l2 * np.sum((th - th0) ** 2), 2 * l2 * (th - th0)
        for F, t in zip(F_list, true_idx):
            s = F @ th
            p = np.exp(s - s.max())
            p /= p.sum()
            loss += -(s[t] - s.max() - np.log(np.exp(s - s.max()).sum()))
            grad += p @ F - F[t]
        return loss, grad

    res = minimize(nll, th0, jac=True, method="L-BFGS-B", bounds=[(1e-3, None)] * 4)
    return res.x


def mrr_at_k(ranked_keys: list[list[str]], truth: list[str], k: int = 25) -> float:
    rr = [
        (1.0 / (lst[:k].index(t) + 1)) if t in lst[:k] else 0.0
        for lst, t in zip(ranked_keys, truth)
    ]
    return float(np.mean(rr))


# ----------------------------------------------------------------------------- self-test
def _selftest():
    eb = "CCOC(=O)c1ccccc1"  # ethyl benzoate, M = 150.06808
    decoys = ["COC(=O)Cc1ccccc1", "CC(=O)OCc1ccccc1", "O=C(C)c1ccccc1OC"]
    M = mol_info(eb)[1]
    cfg = Config()

    # 1. [M+NH4]+ precursor: naive [M+H]+ filter loses the truth; adduct-aware keeps it
    q_nh4 = Query(M + ADDUCT_SHIFT["[M+NH4]+"], [105.0335, 77.0386, 123.0441], [1.0, 0.4, 0.3])
    assert abs(q_nh4.precursor_mz - 168.1019) < 1e-3
    assert adduct_hypotheses(q_nh4, M, 10) == ["[M+NH4]+"]
    assert not abs(M + PROTON - q_nh4.precursor_mz) < 0.003, "naive filter would have accepted"

    # 2. surrogate alignment: -H2O frame needs the shift to match
    ice_mz, ice_int = (
        np.array([151.0754, 123.0441, 105.0335, 77.0386]),
        np.array([0.2, 0.5, 1.0, 0.4]),
    )
    obs = Query(M + PROTON - H2O, ice_mz - H2O, ice_int)
    d = adduct_delta("[M-H2O+H]+")
    with_shift = modified_cosine(
        obs.mz, obs.intensity, ice_mz, ice_int, d, cfg.gamma_shift, cfg.ppm
    )
    no_shift = modified_cosine(
        obs.mz, obs.intensity, ice_mz, ice_int, 0.0, cfg.gamma_shift, cfg.ppm
    )
    assert with_shift > 0.8 > no_shift + 0.3, (with_shift, no_shift)

    # 3. fragmenter explains benzoyl / phenyl / protonated benzoic acid via H-transfer
    q = Query(151.0754, [77.0386, 105.0335, 123.0441], [0.4, 1.0, 0.5])
    s_true = metfrag_score(q, eb, [0.0], cfg)
    s_dec = [metfrag_score(q, s, [0.0], cfg) for s in decoys]
    assert s_true > 0.9 and all(s_true > x for x in s_dec), (s_true, s_dec)

    # 4. end-to-end: ICEBERG missing for the truth (low confidence) -> MetFrag + prior carry it
    cands = [Candidate(eb, pubchem_count=50_000)] + [
        Candidate(s, ice_mz, ice_int, pubchem_count=c) for s, c in zip(decoys, [20, 5, 3])
    ]
    ranked = rerank(q, cands, cfg)
    print([(r.smiles, round(r.score, 2), r.imputed) for r in ranked])
    assert ranked[0].smiles == eb
    # duplicate stereo/tautomer-free isomers collapse to one slot
    assert len(rerank(q, cands + [Candidate("C(C)OC(=O)c1ccccc1")], cfg)) == len(ranked)
    print("selftest OK")


if __name__ == "__main__":
    if "--selftest" in sys.argv:
        _selftest()
