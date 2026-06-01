"""TDD tests for the OOM guardrail: ResourceGuard.can_load_model().

The system can sit below the 16 GB healthy floor (observed 9.2 GB available).
Loading an in-process model larger than free RAM triggers an OOM kill. K1 in the
harness rules requires checking memory before loading any model >~5 GB.

can_load_model(estimated_mb) is a HARD gate:
  - returns (False, reason) when the model would not fit within a safety margin
  - returns (True, msg) when it fits
  - require_can_load(estimated_mb) raises MemoryError on refusal (for call sites
    that must abort rather than branch)

Written FIRST — these fail until can_load_model / require_can_load exist.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.reliability.resource_guard import ResourceGuard, SystemVitals


def _vitals(available_mb: int) -> SystemVitals:
    return SystemVitals(
        cpu_load_1m=1.0,
        ram_available_mb=available_mb,
        ram_percent=50.0,
        swap_used_mb=0,
    )


def test_can_load_model_exists():
    assert hasattr(ResourceGuard, "can_load_model"), "can_load_model() missing"
    assert hasattr(ResourceGuard, "require_can_load"), "require_can_load() missing"


def test_refuses_when_model_exceeds_available():
    """8 GB model, 9.2 GB available, 2 GB margin -> refuse (8 + 2 > 9.2)."""
    g = ResourceGuard()
    with patch.object(g, "get_vitals", return_value=_vitals(9215)):
        ok, reason = g.can_load_model(8192)
        assert ok is False
        assert "8192" in reason or "8" in reason  # mentions the size
        assert "MB" in reason or "RAM" in reason.upper()


def test_allows_when_model_fits_with_margin():
    """2 GB model, 9.2 GB available -> allowed (2 + 2 margin < 9.2)."""
    g = ResourceGuard()
    with patch.object(g, "get_vitals", return_value=_vitals(9215)):
        ok, _reason = g.can_load_model(2048)
        assert ok is True


def test_margin_is_enforced():
    """A model that fits raw available but NOT with the safety margin is refused."""
    g = ResourceGuard(model_load_margin_mb=2048)
    # 5 GB available, 4 GB model: 4 + 2 = 6 > 5 -> refuse despite 4 < 5.
    with patch.object(g, "get_vitals", return_value=_vitals(5120)):
        ok, _ = g.can_load_model(4096)
        assert ok is False


def test_require_can_load_raises_on_refusal():
    g = ResourceGuard()
    with patch.object(g, "get_vitals", return_value=_vitals(4096)), pytest.raises(MemoryError):
        g.require_can_load(8192)


def test_require_can_load_passes_when_fits():
    g = ResourceGuard()
    with patch.object(g, "get_vitals", return_value=_vitals(32768)):
        g.require_can_load(4096)  # must not raise


def test_zero_or_negative_estimate_is_allowed():
    """A 0/unknown estimate must not block (caller opted out of an estimate)."""
    g = ResourceGuard()
    with patch.object(g, "get_vitals", return_value=_vitals(4096)):
        ok, _ = g.can_load_model(0)
        assert ok is True


# --- baseline coverage the existing class lacked entirely ---


def test_is_healthy_true_with_ample_resources():
    g = ResourceGuard()
    with patch.object(g, "get_vitals", return_value=_vitals(32768)):
        healthy, _ = g.is_healthy()
        assert healthy is True


def test_is_healthy_false_below_floor():
    g = ResourceGuard(min_ram_available_mb=16384)
    with patch.object(g, "get_vitals", return_value=_vitals(9215)):
        healthy, reason = g.is_healthy()
        assert healthy is False
        assert "RAM available too low" in reason
