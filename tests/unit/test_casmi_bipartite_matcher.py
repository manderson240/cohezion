from cohezion.kaggle.casmi_bipartite_matcher import CasmiBipartiteMatcher


def test_casmi_exact_match():
    # True theoretical fragments
    theo_mz = [100.0, 200.0, 300.0]
    # Experimental peaks with small ppm shift (<10 ppm)
    exp_mz = [100.0005, 200.0010, 300.0015]
    exp_int = [10.0, 50.0, 100.0]

    matcher = CasmiBipartiteMatcher(tolerance_ppm=15.0)
    res = matcher.match_spectra(exp_mz, theo_mz, exp_int)

    assert res.total_matched == 3
    assert res.explained_intensity_ratio == 1.0
    assert res.mean_ppm_error < 10.0


def test_casmi_multiplet_disambiguation():
    # Two theoretical peaks very close to each other
    theo_mz = [150.0000, 150.0015]
    # Two experimental peaks
    exp_mz = [150.0001, 150.0016]

    matcher = CasmiBipartiteMatcher(tolerance_ppm=15.0)
    res = matcher.match_spectra(exp_mz, theo_mz)

    # Must find global 1-to-1 match without double-assigning
    assert res.total_matched == 2
    matched_theos = {m.theo_idx for m in res.matches}
    matched_exps = {m.exp_idx for m in res.matches}
    assert matched_theos == {0, 1}
    assert matched_exps == {0, 1}


def test_casmi_empty_spectra():
    matcher = CasmiBipartiteMatcher()
    res = matcher.match_spectra([], [100.0])
    assert res.total_matched == 0
    assert res.coverage_score == 0.0
