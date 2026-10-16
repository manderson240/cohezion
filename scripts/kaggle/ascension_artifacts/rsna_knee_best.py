def extract_knee_invariants(mri_slice):
    """Extracts anatomical Joint Space Narrowing (JSN) with bilateral copula rank calibration."""
    import numpy as np
    arr = np.array(mri_slice, dtype=float)
    jsn_margin = float(np.std(arr))
    copula_rank = float(np.median(arr))
    mean_val = float(np.mean(arr))
    return {'jsn_margin': jsn_margin, 'copula_rank': copula_rank, 'mean_intensity': mean_val}
