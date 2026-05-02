"""Tests for the circuit breaker module (cohezion.reliability)."""

from __future__ import annotations

import time

from cohezion.reliability import (
    CircuitBreaker,
    CircuitState,
    CircuitStats,
    _circuits,
    get_circuit,
)


class TestCircuitState:
    def test_states_exist(self):
        assert CircuitState.CLOSED.value == "closed"
        assert CircuitState.OPEN.value == "open"
        assert CircuitState.HALF_OPEN.value == "half_open"


class TestCircuitStats:
    def test_defaults(self):
        stats = CircuitStats()
        assert stats.failures == 0
        assert stats.successes == 0
        assert stats.last_failure_time == 0.0
        assert stats.last_success_time == 0.0


class TestCircuitBreaker:
    def setup_method(self):
        self.breaker = CircuitBreaker(
            name="test",
            failure_threshold=3,
            recovery_timeout=1.0,
            half_open_max_calls=2,
        )

    def test_initial_state_closed(self):
        assert self.breaker.state == CircuitState.CLOSED

    def test_allow_request_when_closed(self):
        assert self.breaker.allow_request() is True

    def test_record_success_stays_closed(self):
        self.breaker.record_success()
        assert self.breaker.state == CircuitState.CLOSED
        assert self.breaker._stats.successes == 1

    def test_failures_below_threshold_stay_closed(self):
        self.breaker.record_failure()
        self.breaker.record_failure()
        assert self.breaker.state == CircuitState.CLOSED

    def test_failures_at_threshold_open_circuit(self):
        for _ in range(3):
            self.breaker.record_failure()
        assert self.breaker.state == CircuitState.OPEN

    def test_open_rejects_requests(self):
        for _ in range(3):
            self.breaker.record_failure()
        assert self.breaker.allow_request() is False

    def test_open_transitions_to_half_open_after_timeout(self):
        for _ in range(3):
            self.breaker.record_failure()
        assert self.breaker.state == CircuitState.OPEN

        # Simulate timeout elapsed
        self.breaker._stats.last_failure_time = time.time() - 2.0
        assert self.breaker.state == CircuitState.HALF_OPEN

    def test_half_open_allows_limited_requests(self):
        for _ in range(3):
            self.breaker.record_failure()
        self.breaker._stats.last_failure_time = time.time() - 2.0

        assert self.breaker.allow_request() is True  # Call 1
        assert self.breaker.allow_request() is True  # Call 2
        assert self.breaker.allow_request() is False  # Exceeded limit

    def test_half_open_success_closes_circuit(self):
        for _ in range(3):
            self.breaker.record_failure()
        self.breaker._stats.last_failure_time = time.time() - 2.0

        # Trigger state check to transition to HALF_OPEN
        _ = self.breaker.state
        assert self.breaker.state == CircuitState.HALF_OPEN

        self.breaker.record_success()
        assert self.breaker.state == CircuitState.CLOSED
        assert self.breaker._stats.failures == 0

    def test_half_open_failure_reopens_circuit(self):
        for _ in range(3):
            self.breaker.record_failure()
        self.breaker._stats.last_failure_time = time.time() - 2.0

        _ = self.breaker.state  # Transition to HALF_OPEN
        self.breaker.record_failure()
        assert self.breaker.state == CircuitState.OPEN

    def test_reset(self):
        for _ in range(3):
            self.breaker.record_failure()
        assert self.breaker.state == CircuitState.OPEN

        self.breaker.reset()
        assert self.breaker.state == CircuitState.CLOSED
        assert self.breaker._stats.failures == 0

    def test_get_stats(self):
        self.breaker.record_success()
        self.breaker.record_failure()
        stats = self.breaker.get_stats()
        assert stats["name"] == "test"
        assert stats["failures"] == 1
        assert stats["successes"] == 1
        assert stats["state"] == "closed"

    def test_full_lifecycle(self):
        """CLOSED -> OPEN -> HALF_OPEN -> CLOSED"""
        # CLOSED: normal operation
        assert self.breaker.state == CircuitState.CLOSED
        self.breaker.record_success()

        # Trigger threshold -> OPEN
        for _ in range(3):
            self.breaker.record_failure()
        assert self.breaker.state == CircuitState.OPEN

        # Wait for recovery -> HALF_OPEN
        self.breaker._stats.last_failure_time = time.time() - 2.0
        assert self.breaker.state == CircuitState.HALF_OPEN

        # Success -> CLOSED
        self.breaker.record_success()
        assert self.breaker.state == CircuitState.CLOSED


class TestGetCircuit:
    def setup_method(self):
        _circuits.clear()

    def test_creates_new_circuit(self):
        cb = get_circuit("test_service")
        assert isinstance(cb, CircuitBreaker)
        assert cb.name == "test_service"

    def test_returns_same_instance(self):
        cb1 = get_circuit("singleton_test")
        cb2 = get_circuit("singleton_test")
        assert cb1 is cb2

    def test_different_names_different_instances(self):
        cb1 = get_circuit("service_a")
        cb2 = get_circuit("service_b")
        assert cb1 is not cb2

    def test_custom_threshold(self):
        cb = get_circuit("custom", failure_threshold=10)
        assert cb.failure_threshold == 10

    def test_update_threshold_on_existing(self):
        cb = get_circuit("update_test", failure_threshold=5)
        get_circuit("update_test", failure_threshold=10)
        assert cb.failure_threshold == 10

    def teardown_method(self):
        _circuits.clear()
