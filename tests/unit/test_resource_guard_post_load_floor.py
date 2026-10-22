"""ResourceGuard.can_load_model must keep the 16 GiB floor AFTER the load (harness N3).

Measured 2026-09-21: with 34,927 MB available the gate approved a 21 GiB model
(qwen3.6-moe:35b-a3b on FLM) — "fits: 23552MB needed <= 34927MB available" — which would have
left ~11 GiB, while inference.hotswap's floor-aware check refused the same load. The floor was
defined on the guard (min_ram_available_mb) but only is_healthy() read it.

Lives in tests/unit/ so it is gated: the SR1 contract tests in tests/reliability/ and
tests/vmodel/ were red for weeks because neither CI gate runs those directories.
"""

from __future__ import annotations

from unittest.mock import patch

from cohezion.reliability.resource_guard import ResourceGuard, SystemVitals


def _guard_with(available_mb: int, cpu: float = 1.0) -> ResourceGuard:
    guard = ResourceGuard()  # production defaults: 16384 MB floor, 2048 MB margin
    vitals = SystemVitals(
        cpu_load_1m=cpu, ram_available_mb=available_mb, ram_percent=60.0, swap_used_mb=0
    )
    patcher = patch.object(guard, "get_vitals", return_value=vitals)
    patcher.start()
    return guard


def test_the_measured_2026_09_21_load_is_refused() -> None:
    ok, reason = _guard_with(34927).can_load_model(21 * 1024)
    assert ok is False, reason
    assert "floor" in reason


def test_a_load_that_keeps_the_floor_is_allowed() -> None:
    # 21 GiB + 2 GiB margin from 40 GiB leaves 17 GiB >= 16 GiB.
    ok, reason = _guard_with(40 * 1024).can_load_model(21 * 1024)
    assert ok is True, reason


def test_floor_boundary_is_inclusive() -> None:
    guard = _guard_with(16384 + 2048 + 1000)
    assert guard.can_load_model(1000)[0] is True  # leaves exactly the floor
    assert guard.can_load_model(1001)[0] is False  # one MB under


def test_zero_estimate_still_opts_out() -> None:
    """execute_fn_aligned's soft preflight passes 0; that contract is unchanged."""
    assert _guard_with(4096).can_load_model(0)[0] is True


def test_overloaded_cpu_refuses_a_load() -> None:
    ok, reason = _guard_with(64 * 1024, cpu=99.0).can_load_model(1024)
    assert ok is False
    assert "cpu" in reason.lower()
