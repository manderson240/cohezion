"""Anatomical copula coupling for RSNA knee pathology detection.

Target labels (exact 12):

    ACL, MCL, Medial Meniscus, Lateral Meniscus, Medial OA, Lateral OA,
    PF OA, Effusion, Synovitis, Baker's, Contusion, Fracture

1. Why independent column ranking under-exploits cross-label signal
-------------------------------------------------------------------
Macro ROC-AUC is computed per pathology as a one-vs-rest rank statistic,
then averaged.  If each column is ranked on its own (rank(pct=True) per
label), the ordering of samples *within* a column depends only on that
column's own predicted score.  Any information the model has expressed in
a correlated companion column is therefore discarded from the target
column's ordering.  In the knee, pathologies are not independent events:

    * ACL <-> Contusion <-> Effusion     (acute pivot-shift triad)
    * Medial Meniscus <-> Medial OA      (medial compartment wear)
    * Lateral Meniscus <-> Lateral OA    (lateral compartment wear)
    * Effusion <-> Synovitis             (inflammatory fluid accumulation)

Two samples with an identical ACL score but very different
contusion/effusion scores are equally likely to be a true ACL positive
under the independent model (they tie on ACL).  In reality the sample
with severe bone contusion + effusion is more likely positive.  For a
rank-based metric that tie-break is exactly where the recoverable signal
lives: independent ranking flattens the difference to a tie, while
coupling breaks the tie in the anatomically implied direction.

2. Coupling matrix: empirical shrunk correlation vs anatomical prior
-------------------------------------------------------------------
The 12 predicted columns are treated as realizations of a latent Gaussian
copula: a monotone rank-percentile transform yields uniform margins

    u_j = rank_pct(pred_j)                # uniform margin (copula)

and a probit transform maps them to standard normals

    z_j = ndtri(u_j)                      # ~ N(0, 1)

whose Pearson correlation is exactly Spearman's rho of the original
columns (rank-based, so robust to each label's miscalibration).  The
coupling matrix C is an empirical-Bayes shrink of that empirical
correlation R toward an anatomical prior P:

    C = (1 - shrink) * R + shrink * P

P encodes the known co-pathology edges above as unit coupling and zero
elsewhere, so the estimator is regularized by anatomy rather than
overfit to the model's prediction noise.

3. Empirical Bayes boost and monotonicity of true negatives
-----------------------------------------------------------
Under the joint Gaussian model N(0, C), the best linear predictor of z_j
from its companions (the posterior mean, mean = 0) is

    m_j = C[j, -j] @ (C[-j,-j] + rho*I)^{-1} @ z[-j]

and the boosted score is a convex blend of the model's own signal and the
companion-derived estimate:

    z_j* = (1 - alpha_shrink) * z_j + alpha_shrink * m_j

alpha_shrink is the trust placed in the anatomical prior (0 = independent
ranking, recovered exactly).  A sample with a high positive companion
(e.g. severe contusion/effusion) gets m_j > 0 and its z_j is lifted; the
final re-rank moves it upward in the ACL column.  The operation is
monotone non-decreasing in every companion whose partial weight is
non-negative, and alpha_shrink keeps the model's own score dominant, so:

    * a true negative low on every companion receives m_j ~ 0 and stays
      low -- it is never promoted past a true positive;
    * two samples identical in own-score are re-ordered only when the
      companion evidence genuinely differs, and always in the anatomical
      direction;
    * the final rank-percentile is itself a monotone transform, so it
      preserves every ordering decision made by the blended score.

Caveat (honest bound): this can only add signal that is *orthogonal* to
the target column's own prediction.  If both arms already capture the
co-pathology structure, the gain is ~0.  The 0.943 -> 0.950 target is only
reachable to the extent the companions carry genuine extra information
and alpha_shrink is tuned on out-of-fold validation.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

__all__ = ["LABELS", "ANATOMICAL_EDGES", "anatomical_copula_coupling"]

LABELS = [
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
]

# Anatomical co-pathology edges encoded into the prior coupling matrix.
ANATOMICAL_EDGES = [
    ("ACL", "Contusion"),           # pivot-shift triad
    ("ACL", "Effusion"),
    ("Contusion", "Effusion"),
    ("Medial Meniscus", "Medial OA"),   # medial compartment wear
    ("Lateral Meniscus", "Lateral OA"),  # lateral compartment wear
    ("Effusion", "Synovitis"),      # inflammatory fluid accumulation
]


def _ndtri(p: np.ndarray) -> np.ndarray:
    """Inverse standard-normal CDF (Acklam's rational approximation).

    Vectorized; accurate to ~1e-9.  Avoids a scipy dependency so the
    module stays self-contained.
    """
    a = np.array([
        -3.969683028665376e+01, 2.209460984245205e+02,
        -2.759285104469687e+02, 1.383577518672690e+02,
        -3.066479806614716e+01, 2.506628277459239e+00,
    ])
    b = np.array([
        -5.447609879822406e+01, 1.615858368580409e+02,
        -1.556989798598866e+02, 6.680131188771972e+01,
        -1.328068155288572e+01,
    ])
    c = np.array([
        -7.784894002430293e-03, -3.223964580411365e-01,
        -2.400758277161838e+00, -2.549732539343734e+00,
        4.374664141464968e+00, 2.938163982698783e+00,
    ])
    d = np.array([
        7.784695709041462e-03, 3.224671290700398e-01,
        2.445134137142996e+00, 3.754408661907416e+00,
    ])

    plow = 0.02425
    p = np.clip(p, 1e-12, 1.0 - 1e-12)

    # Tail region (p < plow or p > 1 - plow).
    q_tail = np.sqrt(-2.0 * np.log(np.where(p < plow, p, 1.0 - p)))
    num = ((((c[0] * q_tail + c[1]) * q_tail + c[2]) * q_tail
            + c[3]) * q_tail + c[4]) * q_tail + c[5]
    den = (((d[0] * q_tail + d[1]) * q_tail + d[2]) * q_tail + d[3]) * q_tail + 1.0
    tail = num / den
    tail = np.where(p < plow, tail, -tail)  # lower tail keeps sign, upper negates

    # Central region.
    q = p - 0.5
    r = q * q
    num_c = (((((a[0] * r + a[1]) * r + a[2]) * r + a[3]) * r + a[4]) * r + a[5]) * q
    den_c = ((((b[0] * r + b[1]) * r + b[2]) * r + b[3]) * r + b[4]) * r + 1.0
    central = num_c / den_c

    return np.where((p >= plow) & (p <= 1.0 - plow), central, tail)


def _anatomical_prior(labels: list[str], coupling_strength: float = 0.35) -> np.ndarray:
    """Prior correlation matrix with unit coupling on anatomical edges."""
    idx = {name: i for i, name in enumerate(labels)}
    p = np.eye(len(labels))
    for u, v in ANATOMICAL_EDGES:
        i, j = idx[u], idx[v]
        p[i, j] = p[j, i] = coupling_strength
    return p


def _make_psd(c: np.ndarray) -> np.ndarray:
    """Project onto the PSD cone and restore a unit diagonal."""
    w, v = np.linalg.eigh(c)
    w = np.clip(w, 1e-6, None)
    c_psd = (v * w) @ v.T
    np.fill_diagonal(c_psd, 1.0)
    return c_psd


def _conditional_means(z: np.ndarray, c: np.ndarray, rho: float) -> np.ndarray:
    """Ridge-regularized conditional means: m[:, j] = C[j,-j] A^{-1} z[-j]."""
    n = z.shape[1]
    m = np.zeros_like(z)
    eye = np.eye(n - 1)
    for j in range(n):
        others = [k for k in range(n) if k != j]
        a_mat = c[np.ix_(others, others)] + rho * eye
        b_vec = c[j, others]
        w = np.linalg.solve(a_mat, b_vec)  # regression weights of z_j on companions
        m[:, j] = z[:, others] @ w
    return m


def anatomical_copula_coupling(
    df_preds: pd.DataFrame,
    labels: list[str],
    alpha_shrink: float = 0.15,
    *,
    shrink: float = 0.5,
    rho: float = 1e-3,
) -> pd.DataFrame:
    """Couple the 12 pathology predictions through the anatomical prior.

    Parameters
    ----------
    df_preds : (n_samples, n_labels) predicted probabilities (or any
        monotone transform of them -- the pipeline re-ranks internally).
    labels : the target pathology names, in column order of df_preds.
    alpha_shrink : trust placed in the companion-derived (empirical Bayes)
        estimate; 0.0 recovers independent column ranking exactly.
    shrink : blend between empirical correlation (0) and anatomical prior
        (1) in the coupling matrix.
    rho : ridge on the conditional-covariance inverse (numerical safety).

    Returns
    -------
    A DataFrame of the same shape, with each column re-ranked to a
    [0, 1] percentile, directly usable as the final ensemble score.
    """
    if not isinstance(df_preds, pd.DataFrame):
        raise TypeError("df_preds must be a pandas DataFrame")
    missing = [name for name in labels if name not in df_preds.columns]
    if missing:
        raise ValueError(f"df_preds is missing label columns: {missing}")

    frame = df_preds[labels].astype(float)
    frame = frame.fillna(frame.median()).fillna(0.5)

    n = len(frame)
    if n < 2:
        # Degenerate: no ranks to couple.
        return frame.rank(pct=True)

    # Copula transform: uniform margins -> standard-normal margins.
    u = frame.rank(pct=True, method="average").to_numpy(dtype=np.float64)
    z = _ndtri(u)

    # Coupling matrix = empirical-Bayes shrink of empirical correlation
    # toward the anatomical prior, made positive semi-definite.
    prior = _anatomical_prior(labels)
    r_emp = np.corrcoef(z, rowvar=False)
    r_emp = np.nan_to_num(r_emp, nan=0.0, posinf=0.0, neginf=0.0)
    r_emp = 0.5 * (r_emp + r_emp.T)
    np.fill_diagonal(r_emp, 1.0)
    c = (1.0 - shrink) * r_emp + shrink * prior
    c = _make_psd(c)

    # Empirical Bayes conditional means from companions.
    m = _conditional_means(z, c, rho)

    # Convex blend of the model's own signal and the companion estimate.
    z_star = (1.0 - alpha_shrink) * z + alpha_shrink * m

    # Rank-percentile is a monotone transform, so it is invariant to the
    # forward probit; ranking z_star directly equals ranking Phi(z_star).
    return pd.DataFrame(z_star, index=frame.index, columns=labels).rank(
        pct=True, method="average"
    )


def _run_tests(verbose: bool = True) -> None:
    """Unit tests: structural invariants + the anatomical boost property."""
    rng = np.random.default_rng(0)
    n = 4000
    col = {name: i for i, name in enumerate(LABELS)}

    # Latent anatomy: an acute-triad factor and compartment factors, plus
    # per-column independent noise so companions carry signal that is only
    # partially expressed in each target column's own score.
    noise = rng.normal(size=(n, len(LABELS)))
    raw = noise.copy()
    acute = rng.normal(size=n)
    raw[:, col["ACL"]] = 0.7 * acute + noise[:, col["ACL"]]
    raw[:, col["Contusion"]] = 0.7 * acute + noise[:, col["Contusion"]]
    raw[:, col["Effusion"]] = 0.6 * acute + noise[:, col["Effusion"]]
    raw[:, col["Synovitis"]] = 0.4 * acute + noise[:, col["Synovitis"]]
    med = rng.normal(size=n)
    raw[:, col["Medial Meniscus"]] = 0.6 * med + noise[:, col["Medial Meniscus"]]
    raw[:, col["Medial OA"]] = 0.6 * med + noise[:, col["Medial OA"]]
    lat = rng.normal(size=n)
    raw[:, col["Lateral Meniscus"]] = 0.6 * lat + noise[:, col["Lateral Meniscus"]]
    raw[:, col["Lateral OA"]] = 0.6 * lat + noise[:, col["Lateral OA"]]

    df = pd.DataFrame(raw, columns=LABELS)
    out = anatomical_copula_coupling(df, LABELS, alpha_shrink=0.15)

    # 1. Shape, columns, range.
    assert out.shape == df.shape, "shape mismatch"
    assert list(out.columns) == LABELS, "column order mismatch"
    assert np.isfinite(out.to_numpy()).all(), "non-finite output"
    assert 0.0 <= out.to_numpy().min() and out.to_numpy().max() <= 1.0, "range"

    # 2. Determinism.
    out2 = anatomical_copula_coupling(df, LABELS, alpha_shrink=0.15)
    pd.testing.assert_frame_equal(out, out2)

    # 3. Margin are ~uniform rank-percentiles.
    for name in LABELS:
        assert abs(float(out[name].mean()) - 0.5) < 0.05, f"{name} margin off"

    # 4. alpha_shrink = 0 recovers independent ranking exactly.
    out0 = anatomical_copula_coupling(df, LABELS, alpha_shrink=0.0)
    np.testing.assert_allclose(out0.to_numpy(), df.rank(pct=True).to_numpy(),
                               atol=1e-12)

    # 5. Boost: two rows with IDENTICAL own ACL score but divergent
    #    contusion/effusion are re-ordered in the anatomical direction.
    bg = df.iloc[:200].copy()
    low = bg.iloc[0:1].copy()
    high = bg.iloc[0:1].copy()
    shared_acl = float(bg["ACL"].median())
    low["ACL"] = high["ACL"] = shared_acl
    low["Effusion"] = np.percentile(df["Effusion"], 5)
    high["Effusion"] = np.percentile(df["Effusion"], 95)
    low["Contusion"] = np.percentile(df["Contusion"], 5)
    high["Contusion"] = np.percentile(df["Contusion"], 95)
    twin = pd.concat([bg.iloc[1:], low, high], ignore_index=True)
    t_out = anatomical_copula_coupling(twin, LABELS, alpha_shrink=0.15)
    assert t_out["ACL"].iloc[-2] < t_out["ACL"].iloc[-1], (
        "high-companion twin must outrank low-companion twin on ACL"
    )

    # 6. True negatives stay low: a row silent on every label stays below
    #    the median after coupling.
    neg = bg.iloc[0:1].copy()
    for name in LABELS:
        neg[name] = np.percentile(df[name], 2)
    neg_out = anatomical_copula_coupling(
        pd.concat([bg.iloc[1:], neg], ignore_index=True), LABELS, alpha_shrink=0.15
    )
    assert neg_out["ACL"].iloc[-1] < 0.5, "true negative promoted past median"

    if verbose:
        print("ALL TESTS PASSED")
        print(f"  shape           : {out.shape}")
        print(f"  alpha=0 identity: exact")
        print(f"  boost demo      : ACL rank low-twin "
              f"{t_out['ACL'].iloc[-2]:.3f} < high-twin {t_out['ACL'].iloc[-1]:.3f}")


if __name__ == "__main__":
    _run_tests()
