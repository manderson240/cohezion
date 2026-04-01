"""Tests for reliability/__init__.py (Circuit Breaker).

Covers failure thresholding and state transitions.
"""

from __future__ import annotations

import time

from cohezion.reliability import CircuitBreaker, CircuitState, get_circuit


def test_circuit_breaker_open_close():
    """[P0] Should open circuit after failures and close on success."""
    breaker = CircuitBreaker(name="test", failure_threshold=2, recovery_timeout=0.1)
    
    # Initial state
    assert breaker.state == CircuitState.CLOSED
    assert breaker.allow_request() is True
    
    # 1st failure - stay closed
    breaker.record_failure()
    assert breaker.state == CircuitState.CLOSED
    
    # 2nd failure - open
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    assert breaker.allow_request() is False
    
    # Wait for recovery
    time.sleep(0.15)
    assert breaker.state == CircuitState.HALF_OPEN
    assert breaker.allow_request() is True # First call in half-open
    
    # Success in half-open -> Closed
    breaker.record_success()
    assert breaker.state == CircuitState.CLOSED
    assert breaker.get_stats()["failures"] == 0

def test_circuit_breaker_half_open_failure():
    """[P0] Should re-open if failure occurs in half-open state."""
    breaker = CircuitBreaker(name="test", failure_threshold=1, recovery_timeout=0.1)
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN
    
    time.sleep(0.15)
    assert breaker.state == CircuitState.HALF_OPEN
    
    breaker.record_failure()
    assert breaker.state == CircuitState.OPEN

def test_get_circuit_singleton():
    """[P0] Should return same circuit instance."""
    c1 = get_circuit("ollama")
    c2 = get_circuit("ollama")
    assert c1 is c2
    assert c1.name == "ollama"
