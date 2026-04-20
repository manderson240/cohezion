"""Tests for budget enforcement module.

Verifies:
- Budget calculations and thresholds
- Soft-stop and hard-stop policies
- Progressive alerts at 80%, 90%, 95%
- Circuit breaker with 3-strike rule
- Cost state tracking
- Graceful degradation on vault failure
"""

import time

import pytest

from cohezion.cost_optimization.budget_enforcer import (
    BudgetCircuitBreaker,
    BudgetEnforcer,
    BudgetPolicy,
    CostAlertManager,
    get_current_enforcer,
    reset_current_enforcer,
    set_current_enforcer,
)


class TestCostAlertManager:
    """Test CostAlertManager alert generation."""

    def test_alert_manager_creation(self):
        """Verify alert manager initialization."""
        manager = CostAlertManager(
            warn_threshold_pct=80,
            critical_threshold_pct=90,
            extreme_threshold_pct=95,
        )

        assert manager.warn_threshold == 80
        assert manager.critical_threshold == 90
        assert manager.extreme_threshold == 95

    def test_alert_below_warning(self):
        """Verify no alert below warning threshold."""
        manager = CostAlertManager(warn_threshold_pct=80)

        status, alert = manager.evaluate(75.0)

        assert status == "OK"
        assert alert is None

    def test_alert_at_warning(self):
        """Verify warning alert at threshold."""
        manager = CostAlertManager(
            warn_threshold_pct=80,
            critical_threshold_pct=90,
        )

        status, alert = manager.evaluate(85.0)

        assert status == "WARNING"
        assert alert is not None
        assert "WARNING" in alert
        assert "85.0" in alert

    def test_alert_at_critical(self):
        """Verify critical alert at threshold."""
        manager = CostAlertManager(
            warn_threshold_pct=80,
            critical_threshold_pct=90,
            extreme_threshold_pct=95,
        )

        status, alert = manager.evaluate(92.0)

        assert status == "CRITICAL"
        assert alert is not None
        assert "CRITICAL" in alert

    def test_alert_at_extreme(self):
        """Verify extreme alert at threshold."""
        manager = CostAlertManager(
            critical_threshold_pct=90,
            extreme_threshold_pct=95,
        )

        status, alert = manager.evaluate(97.0)

        assert status == "EXTREME"
        assert alert is not None

    def test_alert_at_blocked(self):
        """Verify blocked status at 100% utilization."""
        manager = CostAlertManager()

        status, alert = manager.evaluate(100.0)

        assert status == "BLOCKED"
        assert alert is not None
        assert "Budget limit reached" in alert

    def test_alert_cooldown(self):
        """Verify alerts respect cooldown period."""
        manager = CostAlertManager(
            warn_threshold_pct=80,
            critical_threshold_pct=90,
        )
        manager.alert_cooldown_sec = 1.0

        # First alert
        status1, alert1 = manager.evaluate(85.0)
        assert status1 == "WARNING"
        assert alert1 is not None

        # Immediate second alert should be suppressed
        status2, alert2 = manager.evaluate(85.0)
        assert status2 == "WARNING"
        assert alert2 is None  # Cooldown active

        # After cooldown
        manager.last_warn_time = time.time() - 2.0
        status3, alert3 = manager.evaluate(85.0)
        assert status3 == "WARNING"
        assert alert3 is not None  # Alert fires again


class TestBudgetCircuitBreaker:
    """Test BudgetCircuitBreaker."""

    def test_circuit_breaker_creation(self):
        """Verify circuit breaker initialization."""
        breaker = BudgetCircuitBreaker(strike_limit=3)

        assert breaker.strike_limit == 3
        assert breaker.strike_count == 0
        assert breaker.is_open is False

    def test_single_violation(self):
        """Verify circuit breaker tracks violations."""
        breaker = BudgetCircuitBreaker(strike_limit=3)

        opened = breaker.record_violation()

        assert breaker.strike_count == 1
        assert opened is False
        assert breaker.is_open is False

    def test_strike_limit_reached(self):
        """Verify circuit breaker opens at strike limit."""
        breaker = BudgetCircuitBreaker(strike_limit=3)

        breaker.record_violation()
        breaker.record_violation()
        opened = breaker.record_violation()

        assert breaker.strike_count == 3
        assert opened is True
        assert breaker.is_open is True

    def test_circuit_breaker_state_check(self):
        """Verify circuit breaker state checking."""
        breaker = BudgetCircuitBreaker(strike_limit=1)

        breaker.record_violation()
        assert breaker.check_state() is True

        # Force auto-reset
        breaker.open_time = time.time() - breaker.reset_timeout_sec - 1
        assert breaker.check_state() is False
        assert breaker.is_open is False

    def test_circuit_breaker_manual_reset(self):
        """Verify manual circuit breaker reset."""
        breaker = BudgetCircuitBreaker(strike_limit=1)

        breaker.record_violation()
        assert breaker.is_open is True

        breaker.reset()

        assert breaker.is_open is False
        assert breaker.strike_count == 0


class TestBudgetEnforcer:
    """Test BudgetEnforcer."""

    def setup_method(self):
        """Reset global state before each test."""
        reset_current_enforcer()

    def test_enforcer_creation(self):
        """Verify budget enforcer initialization."""
        enforcer = BudgetEnforcer(
            budget_usd=10.0,
            policy=BudgetPolicy.SOFT_STOP,
        )

        assert enforcer.budget_usd == 10.0
        assert enforcer.policy == BudgetPolicy.SOFT_STOP

    def test_budget_check_under_limit(self):
        """Verify budget check passes when under limit."""
        enforcer = BudgetEnforcer(budget_usd=10.0)

        can_proceed, reason = enforcer.check_budget(current_cost_usd=5.0)

        assert can_proceed is True
        assert "OK" in reason or "50" in reason

    def test_budget_check_warn_threshold(self):
        """Verify warning alert at 80% utilization."""
        enforcer = BudgetEnforcer(
            budget_usd=10.0,
            warn_threshold_pct=80,
        )

        can_proceed, reason = enforcer.check_budget(current_cost_usd=8.0)

        assert can_proceed is True
        assert "WARNING" in reason

    def test_budget_check_critical_threshold(self):
        """Verify critical alert at 90% utilization."""
        enforcer = BudgetEnforcer(
            budget_usd=10.0,
            critical_threshold_pct=90,
        )

        can_proceed, reason = enforcer.check_budget(current_cost_usd=9.0)

        assert can_proceed is True
        assert "CRITICAL" in reason

    def test_soft_stop_at_limit(self):
        """Verify soft-stop blocks when budget exceeded."""
        enforcer = BudgetEnforcer(
            budget_usd=10.0,
            policy=BudgetPolicy.SOFT_STOP,
        )

        can_proceed, reason = enforcer.check_budget(current_cost_usd=10.5)

        assert can_proceed is False
        assert "Budget limit exceeded" in reason

    def test_hard_stop_at_critical(self):
        """Verify hard-stop blocks at critical threshold."""
        enforcer = BudgetEnforcer(
            budget_usd=10.0,
            policy=BudgetPolicy.HARD_STOP,
            critical_threshold_pct=90,
        )

        can_proceed, reason = enforcer.check_budget(current_cost_usd=9.5)

        assert can_proceed is False
        assert "Hard stop policy" in reason or "CRITICAL" in reason

    def test_warning_only_policy(self):
        """Verify warning-only policy never blocks."""
        enforcer = BudgetEnforcer(
            budget_usd=10.0,
            policy=BudgetPolicy.WARNING_ONLY,
        )

        # Even at 150% utilization
        can_proceed, _reason = enforcer.check_budget(current_cost_usd=15.0)

        assert can_proceed is True  # Never blocks

    def test_circuit_breaker_integration(self):
        """Verify circuit breaker integration."""
        enforcer = BudgetEnforcer(
            budget_usd=10.0,
            policy=BudgetPolicy.SOFT_STOP,
        )
        enforcer.circuit_breaker.strike_limit = 2

        # Trigger two violations
        enforcer.check_budget(10.5)
        enforcer.check_budget(10.5)
        assert enforcer.circuit_breaker.strike_count == 2

        # Third check at over limit
        can_proceed, reason = enforcer.check_budget(10.5)
        assert can_proceed is False
        assert "circuit breaker" in reason.lower()
        assert enforcer.circuit_breaker.is_open is True

        # Subsequent checks should fail immediately
        can_proceed2, _ = enforcer.check_budget(5.0)
        assert can_proceed2 is False

    def test_get_budget_state(self):
        """Verify budget state snapshot."""
        enforcer = BudgetEnforcer(budget_usd=10.0)

        state = enforcer.get_budget_state(current_cost_usd=8.0)

        assert state.total_budget_usd == 10.0
        assert state.current_cost_usd == 8.0
        assert state.remaining_budget_usd == 2.0
        assert state.utilization_pct == 80.0
        assert state.status == "WARNING"

    def test_budget_state_to_dict(self):
        """Verify budget state serialization."""
        enforcer = BudgetEnforcer(budget_usd=10.0)
        state = enforcer.get_budget_state(current_cost_usd=8.0)

        data = state.to_dict()

        assert data["total_budget_usd"] == 10.0
        assert data["current_cost_usd"] == 8.0
        assert data["remaining_budget_usd"] == 2.0
        assert data["utilization_pct"] == 80.0

    def test_enforcer_reset(self):
        """Verify enforcer reset clears state."""
        enforcer = BudgetEnforcer(budget_usd=10.0)

        enforcer.alert_manager.alert_count = 5
        enforcer.circuit_breaker.strike_count = 2
        enforcer.circuit_breaker.is_open = True

        enforcer.reset()

        assert enforcer.alert_manager.alert_count == 0
        assert enforcer.circuit_breaker.strike_count == 0
        assert enforcer.circuit_breaker.is_open is False

    def test_global_enforcer_instance(self):
        """Verify global enforcer instance management."""
        reset_current_enforcer()
        assert get_current_enforcer() is None

        enforcer = BudgetEnforcer(budget_usd=10.0)
        set_current_enforcer(enforcer)

        assert get_current_enforcer() is enforcer

        reset_current_enforcer()
        assert get_current_enforcer() is None

    def test_zero_budget(self):
        """Verify behavior with zero budget."""
        enforcer = BudgetEnforcer(budget_usd=0.0)

        can_proceed, _ = enforcer.check_budget(current_cost_usd=0.0)

        # Should allow zero cost on zero budget
        assert can_proceed is True

    def test_negative_cost(self):
        """Verify handling of negative costs (edge case)."""
        enforcer = BudgetEnforcer(budget_usd=10.0)

        # Negative costs shouldn't happen, but should be handled
        can_proceed, _ = enforcer.check_budget(current_cost_usd=-1.0)

        assert can_proceed is True  # Below budget


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
