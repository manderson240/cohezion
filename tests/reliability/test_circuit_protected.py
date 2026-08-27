"""Discriminating tests for circuit_protected + CircuitOpenError.

Added on adversarial-review finding (correctness lane P1, 2026-08-14): the
decorator was ported from the retired reliability/circuit_breaker.py and
verified live, but had no checked-in test — a refactor could ship green.

Note (review P2): unlike the retired module, circuit_protected shares the
package-level _circuits registry with every get_circuit() caller — circuit
names are process-global, so decorator users must pick distinctive names.
"""

from __future__ import annotations

import pytest

from cohezion.reliability import CircuitOpenError, circuit_protected


@pytest.mark.asyncio
async def test_opens_after_threshold_and_fails_fast():
    """Discriminating: if failures are not recorded, the circuit never opens
    and the third call raises ValueError instead of CircuitOpenError."""

    @circuit_protected("cp-test-opens", failure_threshold=2)
    async def boom():
        raise ValueError("inner")

    for _ in range(2):
        with pytest.raises(ValueError):
            await boom()
    with pytest.raises(CircuitOpenError):
        await boom()


@pytest.mark.asyncio
async def test_success_keeps_circuit_closed_and_returns_value():
    calls = {"n": 0}

    @circuit_protected("cp-test-success", failure_threshold=2)
    async def ok():
        calls["n"] += 1
        return "value"

    for _ in range(5):
        assert await ok() == "value"
    assert calls["n"] == 5


@pytest.mark.asyncio
async def test_sync_function_supported():
    @circuit_protected("cp-test-sync", failure_threshold=2)
    def sync_fn(x):
        return x * 2

    assert await sync_fn(21) == 42


@pytest.mark.asyncio
async def test_exception_reraised_not_swallowed():
    """The wrapped exception must propagate (recorded, never suppressed)."""

    @circuit_protected("cp-test-reraise", failure_threshold=5)
    async def boom():
        raise KeyError("propagate-me")

    with pytest.raises(KeyError):
        await boom()


def test_wrapper_exposes_circuit_object():
    @circuit_protected("cp-test-attr", failure_threshold=3)
    async def fn():
        return 1

    circuit = getattr(fn, "circuit", None)
    assert circuit is not None
    assert circuit.name == "cp-test-attr"
