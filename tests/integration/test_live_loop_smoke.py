"""Integration smoke — the V-model's missing upper rung (see .claude/rules/verification-depth.md).

UN-MOCKED end-to-end: assemble the REAL make_executor / make_local_execute_fn and run a REAL task
through the live local loop. This single test would have caught — in one shot — the dead-port keystone
(make_local_execute_fn hitting the offline :13306 → empty output → degenerate all-CPU routing), the
thinking-model empty-reply class, and the constant-REROUTE JEPA gate. NONE of those were catchable by
the mocked unit tests, which verify logic against an imagined boundary.

Skips gracefully when local inference is down (CI without lemonade); when the :13305 OmniRouter is up,
the loop MUST produce non-empty output on a real engine — anything else is the failure mode this rung
exists to catch.
"""
from __future__ import annotations

import pytest


def _lemonade_up() -> bool:
    try:
        from cohezion.compound.local_inference import lemonade_available

        return lemonade_available(npu_port=13305)
    except Exception:
        return False


pytestmark = pytest.mark.skipif(
    not _lemonade_up(),
    reason="local inference (:13305) down — integration smoke requires the live boundary",
)


def test_live_loop_produces_nonempty_output_on_a_real_engine():
    """The dead-port/empty-output catcher: a real task through the real execute_fn must return a
    NON-EMPTY answer tagged with a real engine. A wrong endpoint / empty thinking-reply / dormant
    cascade all surface here as empty output or tier_used='unknown' — invisible to mocked tests."""
    from cohezion.compound.local_inference import make_local_execute_fn

    out, metrics = make_local_execute_fn()("Reply with ONE word, POSITIVE or NEGATIVE: I love this.")

    assert (out or "").strip(), "live loop produced EMPTY output — dead-port / empty-reply / dormant cascade"
    assert metrics.get("tier_used") in ("npu", "igpu", "cpu"), (
        f"no real engine recorded (tier_used={metrics.get('tier_used')!r}) — the engine-feedback loop is dead"
    )


def test_make_executor_assembles_a_live_provider():
    """make_executor must build the real inference provider — the #4 dead-port liveness probe (:13306)
    silently made it None on the live box. (Consumption is a separate open item; assembly is the smoke.)"""
    from unittest.mock import MagicMock

    from cohezion.compound import make_executor

    ex = make_executor(MagicMock())
    assert ex._inference_provider is not None, (
        "exec_provider is None on a live box — make_executor liveness probe is hitting a dead port"
    )
