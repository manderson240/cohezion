"""Discriminating tests for the resource-guard actuator + visibility (2026-08-31).

The 08-31 freeze happened with the guard WATCHING: ``below_floor:true`` for 8+ consecutive
polls, ``hazards:0``, and nothing acted — the floor breach emitted a log line no consumer
read while lemond loaded a 35B MoE into 10.4 GB of headroom. This wires the actuator into
the poll loop the incident proved is the only thing still running under pressure, and adds
the observability the 08-15 forensics said was the biggest single miss (GTT is invisible to
every standard counter; the guard recorded only available_gb).

Each test kills a plausible wrong implementation:
  - a guard that stays a watcher (never calls the evictor no matter how long the breach),
  - one that fires on a single transient dip (no consecutive-breach debounce),
  - a breach counter that never resets on recovery,
  - severity derived from the floor alone (blind to swap pressure).
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import cohezion.core.resource_management.session_monitor as sm
from cohezion.core.resource_management.session_monitor import GuardState, poll_once


def _snap(available_gb: float) -> MagicMock:
    snap = MagicMock()
    snap.available_gb = available_gb
    snap.used_gb = 122.0 - available_gb
    snap.total_gb = 122.0
    return snap


def _poll(i: int, available_gb: float, state: GuardState, swap_pct: float = 0.0) -> dict:
    with (
        patch.object(sm.MemorySnapshot, "capture", return_value=_snap(available_gb)),
        patch.object(sm, "_read_swap_pct", return_value=swap_pct),
        patch.object(sm, "_read_gtt_used_gb", return_value=42.5),
        patch.object(sm, "_uma_committed_gb", return_value=None),
        patch.object(sm, "_build_evictor", return_value=None),
    ):
        return poll_once(i, state=state)


class TestVisibility:
    def test_record_carries_gtt_swap_and_severity(self) -> None:
        rec = _poll(1, available_gb=50.0, state=GuardState())
        assert rec["gtt_used_gb"] == 42.5
        assert rec["swap_used_pct"] == 0.0
        assert rec["severity"] == "ok"

    def test_severity_warn_below_floor(self) -> None:
        rec = _poll(1, available_gb=10.5, state=GuardState())  # the 08-31 profile
        assert rec["severity"] == "warn"
        assert rec["below_floor"] is True

    def test_severity_critical_below_critical_avail(self) -> None:
        rec = _poll(1, available_gb=4.0, state=GuardState())
        assert rec["severity"] == "critical"

    def test_severity_critical_on_swap_pressure_even_with_ram(self) -> None:
        # A floor-only severity is blind to the rule-5 OOM precursor (swap >= 50%).
        rec = _poll(1, available_gb=50.0, state=GuardState(), swap_pct=60.0)
        assert rec["severity"] == "critical"

    def test_gtt_reader_failure_is_failsoft(self) -> None:
        with (
            patch.object(sm.MemorySnapshot, "capture", return_value=_snap(50.0)),
            patch.object(sm, "_read_swap_pct", return_value=None),
            patch.object(sm, "_read_gtt_used_gb", return_value=None),
        ):
            rec = poll_once(1, state=GuardState())
        assert rec["gtt_used_gb"] is None  # recorded as unknown, never a crash


class TestDefaultStateWiring:
    def test_module_singleton_persists_breaches_across_bare_calls(self) -> None:
        # main() calls poll_once(i) with NO state kwarg — production runs entirely on the
        # module singleton. Every other test injects state=, so without this one a
        # refactor that localizes _state (resetting the debounce every poll) stays green
        # while production silently never actuates (adversarial review, finding 10).
        saved = sm.GuardState(
            consecutive_breaches=sm._state.consecutive_breaches,
            breach_started_at=sm._state.breach_started_at,
            cooldown_polls=sm._state.cooldown_polls,
            evictor=sm._state.evictor,
        )
        sm._state.consecutive_breaches = 0
        sm._state.breach_started_at = None
        sm._state.cooldown_polls = 0
        sm._state.evictor = MagicMock(evict_until_relieved=MagicMock(return_value=[]))
        try:
            with (
                patch.object(sm.MemorySnapshot, "capture", return_value=_snap(10.5)),
                patch.object(sm, "_read_swap_pct", return_value=0.0),
                patch.object(sm, "_read_gtt_used_gb", return_value=42.5),
                patch.object(sm, "_uma_committed_gb", return_value=None),
                patch.object(sm, "_build_evictor", return_value=None),
            ):
                first = poll_once(1)
                second = poll_once(2)
            assert first["consecutive_breaches"] == 1
            assert second["consecutive_breaches"] == 2  # persisted, not reset per call
        finally:
            sm._state.consecutive_breaches = saved.consecutive_breaches
            sm._state.breach_started_at = saved.breach_started_at
            sm._state.cooldown_polls = saved.cooldown_polls
            sm._state.evictor = saved.evictor


class TestBreachCounter:
    def test_consecutive_breaches_count_and_reset(self) -> None:
        state = GuardState()
        assert _poll(1, 10.0, state)["consecutive_breaches"] == 1
        assert _poll(2, 10.0, state)["consecutive_breaches"] == 2
        assert _poll(3, 50.0, state)["consecutive_breaches"] == 0  # recovery resets
        assert _poll(4, 10.0, state)["consecutive_breaches"] == 1  # counts anew


class TestActuator:
    def test_evictor_fires_after_sustained_breach(self) -> None:
        # THE incident test: 8 consecutive below-floor polls preceded the 08-31 freeze
        # with zero actuation. After EVICT_AFTER_BREACHES sustained breaches the guard
        # must call evict_until_relieved with ITS OWN reading and the N3 floor target.
        state = GuardState()
        evictor = MagicMock()
        evictor.evict_until_relieved.return_value = []
        state.evictor = evictor

        for i in range(1, sm.EVICT_AFTER_BREACHES):
            _poll(i, 10.5, state)
        assert evictor.evict_until_relieved.call_count == 0  # debounced until threshold

        _poll(sm.EVICT_AFTER_BREACHES, 10.5, state, swap_pct=5.0)
        assert evictor.evict_until_relieved.call_count == 1
        args, kwargs = evictor.evict_until_relieved.call_args
        assert args[0] == 10.5  # seeded with the poll's own reading
        assert args[1] == 5.0
        assert kwargs.get("target_available_gb") == sm.N3_FLOOR_GB

    def test_single_transient_dip_does_not_evict(self) -> None:
        state = GuardState()
        evictor = MagicMock()
        state.evictor = evictor
        _poll(1, 10.5, state)
        _poll(2, 50.0, state)
        _poll(3, 10.5, state)
        assert evictor.evict_until_relieved.call_count == 0

    def test_evictions_recorded_in_poll_record(self) -> None:
        state = GuardState()
        evictor = MagicMock()
        ev = MagicMock()
        ev.model_id = "Qwen3.6-35B-A3B-GGUF"
        ev.succeeded = True
        evictor.evict_until_relieved.return_value = [ev]
        state.evictor = evictor

        rec = {}
        for i in range(1, sm.EVICT_AFTER_BREACHES + 1):
            rec = _poll(i, 10.5, state)
        assert rec["evictions"] == ["Qwen3.6-35B-A3B-GGUF"]

    def test_missing_evictor_is_failsoft(self) -> None:
        # If the evictor can't be built (lemonade down, import failure) the guard must
        # keep polling as a watcher — degraded, never dead.
        state = GuardState()
        state.evictor = None
        rec: dict = {}
        for i in range(1, sm.EVICT_AFTER_BREACHES + 1):
            rec = _poll(i, 10.5, state)
        assert rec["evictions"] == []

    def test_critical_severity_bypasses_debounce(self) -> None:
        # Inside the death band (avail < 8 GB) there is no time for a 3-poll debounce —
        # the 08-31 box was dead within seconds of entering it.
        state = GuardState()
        evictor = MagicMock()
        evictor.evict_until_relieved.return_value = []
        state.evictor = evictor
        _poll(1, 4.0, state)  # first poll, already critical
        assert evictor.evict_until_relieved.call_count == 1

    def test_wall_clock_breach_triggers_despite_few_polls(self) -> None:
        # The 08-31 livelock stretched polls to ~18 min: 2 polls can span an hour. A
        # poll-count-only debounce silently becomes 'N x 18 minutes' exactly when it
        # matters (the 08-15 forensics lesson, verbatim).
        state = GuardState()
        evictor = MagicMock()
        evictor.evict_until_relieved.return_value = []
        state.evictor = evictor
        _poll(1, 10.5, state)  # starts the wall clock; 1 < EVICT_AFTER_BREACHES
        assert state.breach_started_at is not None
        state.breach_started_at -= sm.EVICT_AFTER_BREACHES * sm.POLL_SECONDS + 1
        _poll(2, 10.5, state)  # only 2 polls, but the floor has been breached for ages
        assert evictor.evict_until_relieved.call_count == 1

    def test_cooldown_prevents_per_poll_unload_war(self) -> None:
        # After a pass, the guard must re-earn its debounce: acting every poll re-attacks
        # a fleet production is actively reloading (unload-vs-reload thrash) when the
        # floor is held by non-fleet memory (tmpfs/GTT — the actual 08-15 holder).
        state = GuardState()
        evictor = MagicMock()
        evictor.evict_until_relieved.return_value = []
        state.evictor = evictor
        for i in range(1, sm.EVICT_AFTER_BREACHES + 1):
            _poll(i, 10.5, state)
        assert evictor.evict_until_relieved.call_count == 1
        # Still below floor: the very next polls must NOT fire again (cooldown + reset).
        _poll(sm.EVICT_AFTER_BREACHES + 1, 10.5, state)
        _poll(sm.EVICT_AFTER_BREACHES + 2, 10.5, state)
        assert evictor.evict_until_relieved.call_count == 1

    def test_failed_build_retries_after_countdown(self) -> None:
        # A transient build failure must not latch the actuator off for the service's
        # lifetime — that re-creates 'floor warning with no consumer' behind a flag.
        state = GuardState()
        state.evictor = None
        state.evictor_retry_countdown = 0
        good = MagicMock()
        good.evict_until_relieved.return_value = []
        # First eligible poll: build fails -> countdown armed.
        for i in range(1, sm.EVICT_AFTER_BREACHES + 1):
            _poll(i, 10.5, state)
        assert state.evictor is None
        assert state.evictor_retry_countdown == sm.EVICTOR_RETRY_POLLS
        # Fast-forward the countdown; the next eligible poll must retry the build.
        state.evictor_retry_countdown = 1
        state.cooldown_polls = 0
        state.consecutive_breaches = sm.EVICT_AFTER_BREACHES
        with (
            patch.object(sm.MemorySnapshot, "capture", return_value=_snap(10.5)),
            patch.object(sm, "_read_swap_pct", return_value=0.0),
            patch.object(sm, "_read_gtt_used_gb", return_value=42.5),
            patch.object(sm, "_uma_committed_gb", return_value=None),
            patch.object(sm, "_build_evictor", return_value=good) as build,
        ):
            poll_once(99, state=state)  # countdown 1 -> 0, no build yet
            state.consecutive_breaches = sm.EVICT_AFTER_BREACHES
            state.cooldown_polls = 0
            poll_once(100, state=state)  # countdown exhausted -> rebuild succeeds
        assert build.call_count == 1
        assert state.evictor is good
