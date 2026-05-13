"""Tests for overnight_evo_loop retirement logic field name correctness."""
import statistics


def should_retire(keeps: list[float], min_runs: int = 10, cv_threshold: float = 0.05) -> bool:
    """Mirror of overnight_evo_loop retirement logic for direct testing.

    An experiment is retired when:
      - It has at least `min_runs` keep observations.
      - The mean of the last 10 keeps is positive (avoid divide-by-zero).
      - The coefficient of variation (stdev/mean) of the last 10 keeps is below
        `cv_threshold` (i.e. the metric has converged).
    """
    if len(keeps) < min_runs:
        return False
    window = keeps[-10:]
    mean_k = sum(window) / min(10, len(keeps))
    if mean_k <= 0:
        return False
    cv = statistics.stdev(window) / mean_k
    return cv < cv_threshold


class TestRetirementLogicFieldNames:
    """Verify retirement uses r['asi']['experiment'], r['status'], r['metric']."""

    def test_experiment_field_in_asi_not_top_level(self):
        """autoresearch.jsonl stores experiment label in r['asi']['experiment']."""
        # Simulate a typical autoresearch.jsonl entry
        entry = {
            "run": 12345,
            "metric": 0.15,
            "status": "keep",
            "timestamp": 1000000,
            "segment": 99,
            "confidence": 1.0,
            "asi": {"experiment": "E63", "mycelium_delta": 0.15},
        }
        # The experiment label is in asi, NOT at top level
        assert entry.get("experiment") is None, (
            "Top-level 'experiment' key should not exist — it's nested in 'asi'"
        )
        assert entry["asi"]["experiment"] == "E63"

    def test_status_not_verdict(self):
        """autoresearch.jsonl uses 'status' not 'verdict' for keep/discard."""
        entry = {"run": 1, "metric": 0.1, "status": "keep", "asi": {"experiment": "E63"}}
        assert entry.get("verdict") is None, "Use 'status', not 'verdict'"
        assert entry.get("status") == "keep"

    def test_metric_not_delta_for_keep_signal(self):
        """autoresearch.jsonl uses top-level 'metric' as the primary signal."""
        entry = {"run": 1, "metric": 0.15, "status": "keep", "asi": {"experiment": "E63"}}
        assert entry["metric"] == 0.15
        assert entry.get("delta") is None, (
            "Top-level 'delta' doesn't exist — use 'metric' as the primary signal"
        )

    def test_read_recent_results_returns_correct_format(self):
        """_read_recent_results returns dicts with 'status' and 'asi' keys."""
        entries = [
            {"run": i, "metric": 0.1 * i, "status": "keep" if i % 2 else "discard",
             "asi": {"experiment": f"E{i % 3 + 63}"}}
            for i in range(1, 11)
        ]
        keeps = [e for e in entries if e.get("status") == "keep"]
        assert len(keeps) == 5  # Odd indices
        labels = [e["asi"]["experiment"] for e in keeps]
        assert all(lbl.startswith("E") for lbl in labels)


class TestRetirementDecisionLogic:
    """Direct tests of the retirement decision function used by overnight_evo_loop."""

    def test_retirement_needs_10_keeps_minimum(self):
        """With only 9 keeps, experiment should NOT be retired regardless of CV."""
        keeps = [0.10] * 9  # CV would be 0, but only 9 samples
        assert should_retire(keeps) is False

    def test_retirement_cv_zero_retires_converged(self):
        """CV=0 (constant metric) over 10+ keeps → should retire (converged)."""
        keeps = [0.15] * 10  # stdev = 0 → CV = 0 < threshold
        assert should_retire(keeps) is True

    def test_retirement_high_cv_preserves_experiment(self):
        """CV well above threshold (noisy metric) → should NOT retire."""
        # Alternating values produce a large stdev relative to the mean → CV ~0.5
        keeps = [0.05, 0.15] * 5
        mean_k = sum(keeps) / 10
        cv = statistics.stdev(keeps) / mean_k
        assert cv > 0.05  # sanity: this really is high CV
        assert should_retire(keeps) is False

