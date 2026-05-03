"""Tests for cohezion.core.timeit."""
from __future__ import annotations

import time

import pytest

from cohezion.core.timeit import TimeitStats, get_stats, timeit


class TestTimeitDecorator:
    def test_timeit_attaches_stats(self):
        @timeit()
        def fast():
            return 42
        assert hasattr(fast, "_timeit_stats")
        assert isinstance(fast._timeit_stats, TimeitStats)
        assert fast._timeit_stats.count == 0

    def test_single_call(self):
        @timeit()
        def inc():
            return 1
        inc()
        assert inc._timeit_stats.count == 1
        assert inc._timeit_stats.total > 0
        assert inc._timeit_stats.min <= inc._timeit_stats.max

    def test_multiple_calls(self):
        @timeit()
        def noop():
            pass
        for _ in range(5):
            noop()
        assert noop._timeit_stats.count == 5
        assert noop._timeit_stats.mean > 0

    def test_get_stats(self):
        @timeit()
        def identity(x):
            return x
        identity("hello")
        s = get_stats(identity)
        assert s.count == 1

    def test_get_stats_raises_on_undecorated(self):
        def plain():
            pass
        with pytest.raises(AttributeError):
            get_stats(plain)

    def test_threshold_warning(self, caplog):
        caplog.set_level("WARN", logger="cohezion.core.timeit")
        @timeit(threshold_ms=0.001)
        def slow():
            time.sleep(0.02)
        slow()
        assert "slow took" in caplog.text
        assert "threshold 0.00" in caplog.text

    def test_as_dict(self):
        @timeit()
        def work():
            return sum(range(10))
        work()
        s = get_stats(work)
        d = s.as_dict()
        assert d["count"] == 1
        assert d["total"] > 0
        assert d["min"] == d["max"] == d["total"]

    def test_stats_persistence(self):
        times = [2, 5, 8]
        stats = TimeitStats()
        for t in times:
            stats.record(t)
        assert stats.count == 3
        assert stats.total == 15
        assert stats.min == 2
        assert stats.max == 8
        assert stats.mean == 5.0
