"""Property-based tests for AutoresearchEngine.generate_next_experiments.

Tests fundamental properties (contracts) that must hold for ALL inputs,
not just example-based cases. Uses parametrize for combinatorial coverage.
"""

import asyncio
from itertools import product

import pytest

from cohezion.compound.autoresearch import AutoresearchEngine


def _run(coro):
    return asyncio.run(coro)


class TestGenerateNextExperimentsProperties:
    """Property: generate_next_experiments contracts."""

    @pytest.mark.parametrize("n", [1, 2, 3, 5, 10, 15, 20])
    def test_always_returns_exactly_n(self, n):
        """P1: Output length == n for any valid n."""
        engine = AutoresearchEngine()
        result = _run(engine.generate_next_experiments(n=n, session_metrics={}))
        assert len(result) == n, f"Expected {n} experiments, got {len(result)}"

    @pytest.mark.parametrize("coherence", [0.0, 0.1, 0.3, 0.5, 0.7, 0.9, 1.0])
    def test_mode_is_always_valid(self, coherence):
        """P2: Mode is always 'exploit' or 'explore' for any coherence."""
        engine = AutoresearchEngine()
        result = _run(
            engine.generate_next_experiments(n=5, session_metrics={"avg_coherence": coherence})
        )
        for exp in result:
            assert exp["mode"] in ("exploit", "explore"), (
                f"Invalid mode '{exp['mode']}' for coherence={coherence}"
            )

    @pytest.mark.parametrize("coherence", [0.0, 0.1, 0.3, 0.49])
    def test_all_explore_when_below_threshold(self, coherence):
        """P3: When coherence < HIHO_THRESHOLD (0.5), all experiments are 'explore'."""
        engine = AutoresearchEngine()
        result = _run(
            engine.generate_next_experiments(n=5, session_metrics={"avg_coherence": coherence})
        )
        for exp in result:
            assert exp["mode"] == "explore", (
                f"Expected 'explore' for coherence={coherence}, got '{exp['mode']}'"
            )

    @pytest.mark.parametrize("coherence", [0.5, 0.6, 0.8, 1.0])
    def test_all_exploit_when_at_or_above_threshold(self, coherence):
        """P4: When coherence >= HIHO_THRESHOLD (0.5), all experiments are 'exploit'."""
        engine = AutoresearchEngine()
        result = _run(
            engine.generate_next_experiments(n=5, session_metrics={"avg_coherence": coherence})
        )
        for exp in result:
            assert exp["mode"] == "exploit", (
                f"Expected 'exploit' for coherence={coherence}, got '{exp['mode']}'"
            )

    @pytest.mark.parametrize("retired_count,n", [(1, 1), (2, 2), (3, 5), (1, 5)])
    def test_retired_labels_appear_in_results(self, retired_count, n):
        """P5: All retired_labels appear as 'replaces' in the first retired_count results."""
        engine = AutoresearchEngine()
        retired = [f"E{i}_test" for i in range(retired_count)]
        result = _run(
            engine.generate_next_experiments(n=n, session_metrics={}, retired_labels=retired)
        )
        result_replaces = {exp.get("replaces") for exp in result if exp.get("replaces")}
        for label in retired:
            assert label in result_replaces, (
                f"Retired label '{label}' not found in result 'replaces' fields: {result_replaces}"
            )

    def test_hypothesis_field_always_present(self):
        """P6: Every experiment result has a 'hypothesis' field."""
        engine = AutoresearchEngine()
        for coherence in [0.0, 0.5, 1.0]:
            result = _run(
                engine.generate_next_experiments(n=10, session_metrics={"avg_coherence": coherence})
            )
            for exp in result:
                assert "hypothesis" in exp, f"Missing 'hypothesis' in {exp}"
                assert isinstance(exp["hypothesis"], str)
                assert len(exp["hypothesis"]) > 0

    def test_empty_retired_labels_no_replaces(self):
        """P7: With no retired_labels, no result should have 'replaces' set."""
        engine = AutoresearchEngine()
        result = _run(engine.generate_next_experiments(n=5, session_metrics={}))
        replaces = [exp.get("replaces") for exp in result if exp.get("replaces")]
        assert len(replaces) == 0, f"Unexpected 'replaces' in {replaces}"

    @pytest.mark.parametrize("n,coherence", list(product([1, 3, 5], [0.2, 0.5, 0.8])))
    def test_priority_always_set(self, n, coherence):
        """P8: Every experiment has a 'priority' field."""
        engine = AutoresearchEngine()
        result = _run(
            engine.generate_next_experiments(n=n, session_metrics={"avg_coherence": coherence})
        )
        for exp in result:
            assert "priority" in exp, f"Missing 'priority' in {exp}"
