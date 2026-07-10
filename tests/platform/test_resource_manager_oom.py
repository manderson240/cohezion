"""Discriminating tests for the strengthened OOM safety gate (2026-06-05).

Adds enforcement of harness K1 / strix-halo rule 5 ("never pin a >20 GB model while swap
>=50%"), which existed only as prose before. `oom_safe_to_load` is pure (snapshot is
injectable), so each test pins a boundary a plausible wrong impl would miss:
  - a gate that only checks free memory and ignores SWAP (would let a 25 GB load through at
    60% swap and invite the OOM killer),
  - a swap guard that fires for SMALL models too (over-blocking),
  - strict-`>` vs `>=` at the 50% swap / 20 GB boundaries,
  - a non-fail-soft impl that blocks everything when psutil is missing.
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.platform.resource_manager import (
    LARGE_MODEL_GB,
    SWAP_PRESSURE_PCT,
    oom_safe_to_load,
)


def test_ample_memory_low_swap_is_ok() -> None:
    ok, reason = oom_safe_to_load(5.0, snapshot=(50.0, 10.0))
    assert ok is True and reason == "ok"


def test_large_model_under_swap_pressure_is_blocked_despite_ample_memory() -> None:
    # THE K1 invariant: 60 GiB free is plenty for a 25 GiB model, but 60% swap blocks it.
    # A free-memory-only gate would WRONGLY allow this and risk the OOM killer.
    ok, reason = oom_safe_to_load(25.0, snapshot=(60.0, 60.0))
    assert ok is False
    assert "swap" in reason.lower()


def test_large_model_low_swap_is_ok() -> None:
    ok, _ = oom_safe_to_load(25.0, snapshot=(60.0, 30.0))
    assert ok is True


def test_small_model_high_swap_still_ok() -> None:
    # Swap guard applies ONLY to large models; a 2 GiB load is fine even at 90% swap.
    ok, _ = oom_safe_to_load(2.0, snapshot=(50.0, 90.0))
    assert ok is True


def test_swap_and_size_boundaries_are_inclusive() -> None:
    # >= on both: exactly 20 GiB at exactly 50% swap must block.
    ok, _ = oom_safe_to_load(LARGE_MODEL_GB, snapshot=(60.0, SWAP_PRESSURE_PCT))
    assert ok is False


def test_insufficient_real_memory_is_blocked() -> None:
    # need = 40 * 1.2 = 48 GiB > 45 GiB available.
    ok, reason = oom_safe_to_load(40.0, snapshot=(45.0, 5.0))
    assert ok is False and "memory" in reason.lower()


def test_psutil_unavailable_fails_soft_open() -> None:
    # A safety gate must not block ALL loads just because psutil is missing — the budget
    # model remains the primary guard. Fail-soft -> (True, ...).
    with patch("cohezion.platform.resource_manager._read_system_memory", return_value=None):
        ok, reason = oom_safe_to_load(5.0)
    assert ok is True and "psutil" in reason.lower()
