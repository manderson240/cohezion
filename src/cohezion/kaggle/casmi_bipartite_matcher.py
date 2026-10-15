"""
CASMI Exact Bipartite Spectrum Matcher
======================================
Elegantly simple, mathematically optimal mass spectrometry peak matching.
Replaces greedy tolerance heuristics with exact Maximum-Weight Bipartite Matching
via Linear Sum Assignment (Hungarian / Jonker-Volgenant) on ppm-bounded mass defect matrices.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

import numpy as np
from scipy.optimize import linear_sum_assignment


@dataclass(frozen=True, slots=True)
class PeakMatch:
    exp_idx: int
    theo_idx: int
    exp_mz: float
    theo_mz: float
    ppm_error: float
    intensity_weight: float


@dataclass(frozen=True, slots=True)
class SpectrumMatchResult:
    matches: list[PeakMatch]
    total_matched: int
    total_exp_peaks: int
    total_theo_peaks: int
    mean_ppm_error: float
    explained_intensity_ratio: float
    coverage_score: float


class CasmiBipartiteMatcher:
    """Exact bipartite matching engine between experimental MS/MS and theoretical fragments."""

    def __init__(self, tolerance_ppm: float = 15.0):
        self.tolerance_ppm = tolerance_ppm

    def match_spectra(
        self,
        exp_mz: Sequence[float],
        theo_mz: Sequence[float],
        exp_intensities: Sequence[float] | None = None,
    ) -> SpectrumMatchResult:
        """Find globally optimal 1-to-1 peak assignment minimizing total ppm error.

        Parameters
        ----------
        exp_mz : Sequence[float]
            Experimental m/z values.
        theo_mz : Sequence[float]
            Theoretical candidate fragment m/z values.
        exp_intensities : Sequence[float] | None
            Experimental peak intensities for weighted coverage calculation.
        """
        m = len(exp_mz)
        k = len(theo_mz)

        if m == 0 or k == 0:
            return SpectrumMatchResult(
                matches=[],
                total_matched=0,
                total_exp_peaks=m,
                total_theo_peaks=k,
                mean_ppm_error=0.0,
                explained_intensity_ratio=0.0,
                coverage_score=0.0,
            )

        intensities = (
            np.ones(m, dtype=np.float64)
            if exp_intensities is None
            else np.asarray(exp_intensities, dtype=np.float64)
        )
        total_intensity = float(np.sum(intensities)) if np.sum(intensities) > 0 else 1.0

        # High penalty cost for non-edges
        INF_COST = 1e6
        cost_matrix = np.full((m, k), INF_COST, dtype=np.float64)

        # Build candidate edges with tolerance window tau
        # delta_ppm = |e - t| / t * 1e6 <= tolerance_ppm
        for i, e in enumerate(exp_mz):
            for j, t in enumerate(theo_mz):
                if t <= 0:
                    continue
                ppm = abs(e - t) / t * 1e6
                if ppm <= self.tolerance_ppm:
                    # Cost combines ppm error with intensity priority
                    # Lower cost is preferred by linear_sum_assignment
                    cost_matrix[i, j] = ppm

        # Solve exact bipartite matching
        row_ind, col_ind = linear_sum_assignment(cost_matrix)

        matches: list[PeakMatch] = []
        matched_intensity = 0.0

        for r, c in zip(row_ind, col_ind):
            cost = cost_matrix[r, c]
            if cost < INF_COST:
                e_val = float(exp_mz[r])
                t_val = float(theo_mz[c])
                ppm_err = abs(e_val - t_val) / t_val * 1e6
                inte = float(intensities[r])
                matched_intensity += inte
                matches.append(
                    PeakMatch(
                        exp_idx=r,
                        theo_idx=c,
                        exp_mz=e_val,
                        theo_mz=t_val,
                        ppm_error=ppm_err,
                        intensity_weight=inte,
                    )
                )

        total_matched = len(matches)
        mean_ppm = float(np.mean([m.ppm_error for m in matches])) if matches else 0.0
        exp_ratio = matched_intensity / total_intensity
        # Coverage combines matched fraction and explained intensity
        theo_coverage = total_matched / k if k > 0 else 0.0
        coverage_score = float(0.5 * theo_coverage + 0.5 * exp_ratio)

        return SpectrumMatchResult(
            matches=matches,
            total_matched=total_matched,
            total_exp_peaks=m,
            total_theo_peaks=k,
            mean_ppm_error=mean_ppm,
            explained_intensity_ratio=exp_ratio,
            coverage_score=coverage_score,
        )
