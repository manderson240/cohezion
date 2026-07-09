"""Unit tests for cohezion_state — full system state awareness."""

from __future__ import annotations

from unittest.mock import patch

from cohezion.compound.cohezion_state import format_state_for_context, get_full_state


class TestGetFullState:
    def test_returns_required_keys(self):
        s = get_full_state()
        assert "timestamp" in s
        assert "silicon" in s
        assert "autodqa" in s
        assert "autoresearch" in s
        assert "lemonade" in s

    def test_silicon_has_up_flags(self):
        s = get_full_state()
        si = s["silicon"]
        assert isinstance(si.get("npu_up"), bool)
        assert isinstance(si.get("igpu_up"), bool)

    def test_lemonade_has_available_key(self):
        s = get_full_state()
        lem = s["lemonade"]
        assert "available" in lem
        assert isinstance(lem["available"], bool)

    def test_autodqa_has_session_results(self):
        s = get_full_state()
        dqa = s["autodqa"]
        assert "session_results" in dqa
        assert isinstance(dqa["session_results"], int)

    def test_autoresearch_has_total_runs(self):
        s = get_full_state()
        ar = s["autoresearch"]
        assert "total_runs" in ar

    def test_does_not_raise_when_services_offline(self):
        """get_full_state must be fail-safe — never raise on offline services."""
        with patch("cohezion.compound.cohezion_state._probe_lemonade", return_value=False):
            s = get_full_state()
        assert s is not None

    def test_timestamp_is_iso_format(self):
        s = get_full_state()
        ts = s["timestamp"]
        assert isinstance(ts, str)
        assert "T" in ts  # ISO 8601 separator

    def test_total_runs_non_negative(self):
        s = get_full_state()
        assert s["autoresearch"]["total_runs"] >= 0


class TestFormatStateForContext:
    def test_returns_string(self):
        result = format_state_for_context()
        assert isinstance(result, str)

    def test_contains_silicon_status(self):
        result = format_state_for_context()
        assert "NPU" in result or "silicon" in result.lower()

    def test_contains_autodqa_info(self):
        result = format_state_for_context()
        assert "AUTODQA" in result.upper() or "autodqa" in result.lower()

    def test_accepts_prebuilt_state(self):
        fake_state = {
            "silicon": {"npu_up": True, "igpu_up": False},
            "autodqa": {"session_results": 42, "accept_rate": 0.85, "fd": 1.45},
            "autoresearch": {"total_runs": 80212, "segment": 6},
            "lemonade": {"available": True},
        }
        result = format_state_for_context(fake_state)
        assert "UP" in result
        assert "80212" in result

    def test_newline_separated_lines(self):
        result = format_state_for_context()
        lines = result.strip().split("\n")
        assert len(lines) >= 2  # at least silicon + autodqa lines
