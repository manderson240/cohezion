"""RS8 — the ambient residency tick joins the EXISTING pressure loop.

`ResidencyService.tick()` was built, mutation-verified and live-verified, and nothing called
it on a timer. That is the last mile between a capability and a running process — the same
dormancy line already crossed once this session with `handle_event`.

`PressureDriver.run()` already IS the loop: `while not stop(): self.tick(); sleep(interval_s)`,
with injectable `sleep` and `stop`. `hotswap`'s own docstring names why the pairing is right:

    "platform/oom_evictor.OOMEvictor really unloads, but only on a memory-pressure CRITICAL
     rising edge — it is pressure-driven, not demand-driven."

RS6 `tick()` is exactly the ambient/demand half that loop lacks. Adding a SECOND timer would
put two independent eviction loops on one fleet, which can race: both read residency, both
pick an LRU victim, both unload. So this is a callback on the existing loop, not a new daemon.
"""

from __future__ import annotations

import inspect

import pytest

from cohezion.platform.oom_evictor import PressureDriver


class _Stopper:
    """stop() returns False for n calls, then True — bounds the loop in tests."""

    def __init__(self, n: int) -> None:
        self.n = n

    def __call__(self) -> bool:
        self.n -= 1
        return self.n < 0


class TestRS8Structural:
    def test_pressure_driver_accepts_an_on_tick_callback(self):
        assert "on_tick" in inspect.signature(PressureDriver.__init__).parameters

    def test_on_tick_defaults_to_none_so_existing_callers_are_unchanged(self):
        assert inspect.signature(PressureDriver.__init__).parameters["on_tick"].default is None


class TestRS8Consumption:
    def test_DISCRIMINATING_on_tick_is_invoked_once_per_loop_iteration(self, monkeypatch):
        """The consumption invariant. An implementation that ACCEPTS the callback and never
        calls it passes every structural test above and fails here."""
        calls: list[int] = []
        drv = PressureDriver(monitor=_FakeMonitor(), on_tick=lambda: calls.append(1))
        ticks = drv.run(interval_s=0, stop=_Stopper(3), sleep=lambda s: None)
        assert ticks == 3
        assert len(calls) == 3, f"on_tick fired {len(calls)} times for {ticks} ticks"

    def test_POSITIVE_CONTROL_no_callback_still_runs_the_loop(self):
        """Proves the callback is optional, not load-bearing for the existing behaviour."""
        drv = PressureDriver(monitor=_FakeMonitor())
        assert drv.run(interval_s=0, stop=_Stopper(2), sleep=lambda s: None) == 2

    def test_DISCRIMINATING_a_raising_callback_does_not_kill_the_loop(self):
        """Fail-soft is the whole reason this driver exists. A residency tick that throws
        (health unreachable, an unload 500) must not end the background loop — otherwise one
        bad pass stops protecting the box against every subsequent good one."""

        def boom():
            raise RuntimeError("residency exploded")

        drv = PressureDriver(monitor=_FakeMonitor(), on_tick=boom)
        assert drv.run(interval_s=0, stop=_Stopper(3), sleep=lambda s: None) == 3

    def test_callback_failure_does_not_suppress_the_pressure_sample(self):
        """The pre-existing job must still happen when the new one fails."""
        mon = _FakeMonitor()
        drv = PressureDriver(monitor=mon, on_tick=lambda: (_ for _ in ()).throw(RuntimeError()))
        drv.run(interval_s=0, stop=_Stopper(2), sleep=lambda s: None)
        assert mon.evaluated == 2, "pressure sampling was skipped when the callback threw"


class _FakeMonitor:
    def __init__(self) -> None:
        self.evaluated = 0

    def evaluate(self, *, snapshot=None):
        self.evaluated += 1
        return "NORMAL"


if __name__ == "__main__":
    raise SystemExit(pytest.main([__file__, "-q"]))
