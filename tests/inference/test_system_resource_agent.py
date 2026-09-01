"""Tests for SystemResourceAgent — silicon resource advisor.

Structural: import + assess() return contract.
Behavioural: deterministic path for offline-Lemonade, schema validation gate.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest

from cohezion.inference.system_resource_agent import (
    _VALID_ACTIONS,
    _VALID_TIERS,
    ResourceRecommendation,
    SystemResourceAgent,
)


# ── Structural ──────────────────────────────────────────────────────────────────


def test_assess_returns_recommendation():
    """assess() always returns a ResourceRecommendation, never raises."""
    advisor = SystemResourceAgent(lemonade_timeout=0.01)  # short timeout → deterministic path
    rec = advisor.assess()
    assert isinstance(rec, ResourceRecommendation)
    assert rec.tier in _VALID_TIERS
    assert rec.action in _VALID_ACTIONS
    assert 0.0 <= rec.pressure_score <= 1.0
    assert isinstance(rec.reason, str)
    assert rec.source in {"lemonade", "deterministic", "error"}


def test_assess_never_raises_on_broken_sources():
    """assess() is fail-open: broken guard/monitor yields a safe default."""
    advisor = SystemResourceAgent()
    advisor._guard = None
    advisor._monitor = None

    # Force a broken guard
    class _BrokenGuard:
        def get_temperature(self):
            raise RuntimeError("hw failure")

    class _BrokenMonitor:
        def get_stats(self):
            raise RuntimeError("psutil missing")

    advisor._guard = _BrokenGuard()
    advisor._monitor = _BrokenMonitor()
    rec = advisor.assess()  # must not raise
    assert rec.tier in _VALID_TIERS


# ── Deterministic path ──────────────────────────────────────────────────────────


@pytest.mark.parametrize(
    "temp,mem,lock,expected_action",
    [
        (45.0, 50.0, False, "proceed"),
        (76.0, 55.0, False, "throttle"),  # temp above throttle threshold
        (55.0, 85.0, False, "throttle"),  # mem above throttle threshold
        (90.0, 55.0, False, "pause"),  # temp above pause threshold
        (55.0, 95.0, False, "pause"),  # mem above pause threshold
        (45.0, 50.0, True, "pause"),  # pressure lock active
    ],
)
def test_deterministic_recommendation_thresholds(temp, mem, lock, expected_action):
    advisor = SystemResourceAgent()
    metrics = {"temp_c": temp, "memory_percent": mem, "available_gb": 64.0, "pressure_lock": lock}
    rec = advisor._deterministic_recommendation(metrics)
    assert rec.action == expected_action
    assert rec.source == "deterministic"
    assert rec.tier in _VALID_TIERS


# ── Lemonade path ───────────────────────────────────────────────────────────────


def test_lemonade_valid_response_parsed():
    """Valid Lemonade JSON is parsed into a ResourceRecommendation."""
    advisor = SystemResourceAgent()
    mock_body = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": '{"tier":"igpu","action":"throttle","reason":"temp elevated","pressure_score":0.5}'
                    }
                }
            ]
        }
    ).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        metrics = {
            "temp_c": 76.0,
            "memory_percent": 65.0,
            "available_gb": 50.0,
            "pressure_lock": False,
        }
        rec = advisor._lemonade_recommendation(metrics)
    assert rec is not None
    assert rec.tier == "igpu"
    assert rec.action == "throttle"
    assert rec.pressure_score == pytest.approx(0.5)
    assert rec.source == "lemonade"


def test_lemonade_invalid_tier_falls_back_to_none():
    """Invalid tier from Lemonade returns None (triggers deterministic fallback)."""
    advisor = SystemResourceAgent()
    mock_body = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "content": '{"tier":"xpu","action":"proceed","reason":"ok","pressure_score":0.1}'
                    }
                }
            ]
        }
    ).encode()
    mock_resp = MagicMock()
    mock_resp.read.return_value = mock_body
    mock_resp.__enter__ = lambda s: s
    mock_resp.__exit__ = MagicMock(return_value=False)
    with patch("urllib.request.urlopen", return_value=mock_resp):
        metrics = {
            "temp_c": 50.0,
            "memory_percent": 60.0,
            "available_gb": 60.0,
            "pressure_lock": False,
        }
        result = advisor._lemonade_recommendation(metrics)
    assert result is None


def test_lemonade_unavailable_returns_none():
    """URLError from Lemonade returns None silently."""
    import urllib.error

    advisor = SystemResourceAgent()
    with patch("urllib.request.urlopen", side_effect=urllib.error.URLError("conn refused")):
        metrics = {
            "temp_c": 50.0,
            "memory_percent": 60.0,
            "available_gb": 60.0,
            "pressure_lock": False,
        }
        result = advisor._lemonade_recommendation(metrics)
    assert result is None


# ── DegradationDetector feed ───────────────────────────────────────────────────


def test_assess_feeds_degradation_detector():
    """assess() calls detector.check_degradation() with silicon metrics when detector provided."""
    detector = MagicMock()
    advisor = SystemResourceAgent(degradation_detector=detector)
    # Force deterministic path (no real Lemonade hit needed)
    with patch.object(advisor, "_lemonade_recommendation", return_value=None):
        advisor.assess()
    detector.check_degradation.assert_called_once()
    call_kwargs = detector.check_degradation.call_args[0][0]
    assert "silicon_temp_c" in call_kwargs
    assert "memory_pressure" in call_kwargs


def test_assess_detector_feed_never_blocks_on_exception():
    """detector.check_degradation() raising must not prevent assess() from returning."""
    detector = MagicMock()
    detector.check_degradation.side_effect = RuntimeError("db gone")
    advisor = SystemResourceAgent(degradation_detector=detector)
    with patch.object(advisor, "_lemonade_recommendation", return_value=None):
        rec = advisor.assess()
    assert rec.tier in _VALID_TIERS  # still returned normally


# ── PSI gating (council item 6, 2026-09-01) ─────────────────────────────────────
# The 08-31 freezes were reclaim LIVELOCKS: available-GB looked survivable while
# tasks stalled in reclaim. PSI avg10 is the earliest signal for that class.
# Discriminating: pre-PSI code ignores the key entirely, so every test asserting a
# PSI-driven action change fails on it.


def _psi_metrics(psi, temp=45.0, mem=50.0, lock=False):
    return {
        "temp_c": temp,
        "memory_percent": mem,
        "available_gb": 64.0,
        "psi_avg10": psi,
        "pressure_lock": lock,
    }


def test_psi_pause_fires_when_mem_and_temp_are_fine():
    # avg10=15% stalled = livelock territory even with healthy free-bytes.
    rec = SystemResourceAgent()._deterministic_recommendation(_psi_metrics(psi=15.0))
    assert rec.action == "pause"
    assert "psi" in rec.reason


def test_psi_throttle_between_thresholds():
    rec = SystemResourceAgent()._deterministic_recommendation(_psi_metrics(psi=5.0))
    assert rec.action == "throttle"


def test_psi_none_preserves_prior_behavior():
    rec = SystemResourceAgent()._deterministic_recommendation(_psi_metrics(psi=None))
    assert rec.action == "proceed"


def test_psi_zero_is_healthy():
    rec = SystemResourceAgent()._deterministic_recommendation(_psi_metrics(psi=0.0))
    assert rec.action == "proceed"


def test_read_psi_avg10_parses_and_fails_none(tmp_path):
    from cohezion.inference.system_resource_agent import _read_psi_avg10

    p = tmp_path / "memory"
    p.write_text("some avg10=3.21 avg60=1.00 avg300=0.10 total=12345\n")
    assert _read_psi_avg10(p) == 3.21
    assert _read_psi_avg10(tmp_path / "absent") is None


def test_fallback_monitor_reads_real_meminfo_not_fabricated():
    # rv-gate HIGH-1 class: a fabricated {50%, 64GB} reader gates nothing. On Linux
    # the fallback must report the box's REAL MemAvailable; assert consistency with
    # a live /proc/meminfo reading taken moments apart.
    from pathlib import Path

    from cohezion.inference.system_resource_agent import _FallbackMonitor

    stats = _FallbackMonitor().get_stats()
    real_avail = None
    for line in Path("/proc/meminfo").read_text().splitlines():
        if line.startswith("MemAvailable"):
            real_avail = int(line.split()[1]) / 1048576.0
            break
    assert real_avail is not None
    assert abs(stats["available_memory_gb"] - real_avail) < 2.0
    assert 0.0 < stats["memory_percent"] < 100.0
