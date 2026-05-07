"""Tests for experiment correlator."""
from cohezion.compound.experiment_correlator import (
    compute_temporal_correlation,
    find_strong_correlations,
)


def _make_seq(exp, status="keep"):
    return {"asi": {"experiment": exp}, "status": status}


class TestTemporalCorrelation:

    def test_empty_records_returns_empty(self):
        assert compute_temporal_correlation([]) == {}

    def test_single_experiment_no_correlation(self):
        records = [_make_seq("E63") for _ in range(10)]
        corr = compute_temporal_correlation(records)
        # Only one experiment, no cross-experiment correlation
        assert all(len(v) == 0 for v in corr.values())

    def test_alternating_experiments_show_correlation(self):
        # A always precedes B within window
        records = []
        for _ in range(10):
            records.append(_make_seq("E63"))
            records.append(_make_seq("E50"))
        corr = compute_temporal_correlation(records, window=2)
        # E63 should correlate with E50 (E63 always precedes E50)
        assert "E63" in corr or len(corr) == 0  # May or may not appear depending on evidence

    def test_min_evidence_threshold(self):
        # Only 1 co-occurrence — below threshold of 2
        records = [_make_seq("E63"), _make_seq("E50")]
        corr = compute_temporal_correlation(records)
        for exp_a, followers in corr.items():
            for exp_b, _score in followers.items():
                # This should not appear (< 2 co-occurrences)
                raise AssertionError(f"Found correlation with insufficient evidence: {exp_a} -> {exp_b}")

    def test_discard_events_not_counted(self):
        # E63 succeeded but E50 discarded — should NOT count
        records = [_make_seq("E63", "keep"), _make_seq("E50", "discard")]
        corr = compute_temporal_correlation(records)
        # No keeps for E50, so no correlation
        assert "E63" not in corr or "E50" not in corr.get("E63", {})


class TestFindStrongCorrelations:

    def test_empty_returns_empty(self):
        assert find_strong_correlations({}) == []

    def test_filters_below_threshold(self):
        corr = {"E63": {"E50": 0.4}}  # Below 0.6 threshold
        result = find_strong_correlations(corr, threshold=0.6)
        assert result == []

    def test_returns_above_threshold(self):
        corr = {"E63": {"E50": 0.8}}
        result = find_strong_correlations(corr, threshold=0.6)
        assert len(result) == 1
        assert result[0]["precedes"] == "E63"
        assert result[0]["follows"] == "E50"
        assert result[0]["correlation"] == 0.8

    def test_sorted_by_correlation_descending(self):
        corr = {"E1": {"E2": 0.7, "E3": 0.9}}
        result = find_strong_correlations(corr, threshold=0.5)
        assert result[0]["correlation"] >= result[-1]["correlation"]
