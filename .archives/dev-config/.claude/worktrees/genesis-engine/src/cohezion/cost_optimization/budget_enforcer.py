"""Budget enforcement with soft-stop policy and emergency circuit breaker.

Features:
- Per-session budget limits with configurable thresholds
- Soft-stop policy: Finish current task, block new ones
- Progressive cost alerts: 80%, 90%, 95%, 100%
- Circuit breaker: 3-strike emergency shutoff
- Cached budget checks (60s refresh, <0.5ms critical path)
- Non-blocking async persistence (best-effort)

Architecture:
  Budget Check (cached)
       ↓
  Threshold evaluation (80%, 90%, 95%, 100%)
       ↓
  Alert/Block (based on policy)
       ↓
  Circuit Breaker (3-strike emergency)

Usage:
    enforcer = BudgetEnforcer(
        budget_usd=10.0,
        warn_threshold_pct=80,
        critical_threshold_pct=90,
        block_threshold_pct=100,
    )

    can_proceed, reason = enforcer.check_budget(current_cost_usd=8.5)
    if not can_proceed:
        logger.warning(f"Budget enforcement: {reason}")
        # Soft-stop: Block new tasks, allow current to finish
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import ClassVar, Optional


logger = logging.getLogger(__name__)


class BudgetPolicy(Enum):
    """Budget enforcement policy."""

    SOFT_STOP = "soft_stop"  # Finish current task, block new ones
    HARD_STOP = "hard_stop"  # Immediate stop (not recommended)
    WARNING_ONLY = "warning_only"  # Just log alerts, don't block


@dataclass
class BudgetState:
    """Budget enforcement state snapshot."""

    total_budget_usd: float
    current_cost_usd: float
    remaining_budget_usd: float
    utilization_pct: float
    status: str  # "OK", "WARNING", "CRITICAL", "BLOCKED"
    last_check_time: float
    alert_count: int = 0

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            "total_budget_usd": self.total_budget_usd,
            "current_cost_usd": self.current_cost_usd,
            "remaining_budget_usd": self.remaining_budget_usd,
            "utilization_pct": self.utilization_pct,
            "status": self.status,
            "last_check_time": self.last_check_time,
            "alert_count": self.alert_count,
        }


class CostAlertManager:
    """Manages cost alerts at different thresholds."""

    def __init__(
        self,
        warn_threshold_pct: int = 80,
        critical_threshold_pct: int = 90,
        extreme_threshold_pct: int = 95,
    ):
        """Initialize alert manager.

        Args:
            warn_threshold_pct: Warning threshold percentage (default: 80%)
            critical_threshold_pct: Critical threshold percentage (default: 90%)
            extreme_threshold_pct: Extreme threshold percentage (default: 95%)
        """
        self.warn_threshold = warn_threshold_pct
        self.critical_threshold = critical_threshold_pct
        self.extreme_threshold = extreme_threshold_pct

        # Track alerts to avoid spamming
        self.last_warn_time = 0.0
        self.last_critical_time = 0.0
        self.alert_count = 0
        self.alert_cooldown_sec = 60  # Don't spam alerts more than once/min

    def evaluate(self, utilization_pct: float) -> tuple[str, str | None]:
        """Evaluate utilization and return status + optional alert.

        Args:
            utilization_pct: Budget utilization percentage (0-100+)

        Returns:
            Tuple of (status, alert_message)
            - status: "OK", "WARNING", "CRITICAL", "EXTREME", "BLOCKED"
            - alert_message: Alert message if threshold crossed, else None
        """
        current_time = time.time()

        if utilization_pct < self.warn_threshold:
            return "OK", None

        if utilization_pct < self.critical_threshold:
            if current_time - self.last_warn_time > self.alert_cooldown_sec:
                self.last_warn_time = current_time
                self.alert_count += 1
                msg = f"Cost WARNING: Budget utilization at {utilization_pct:.1f}% (threshold: {self.warn_threshold}%)"
                return "WARNING", msg
            return "WARNING", None

        if utilization_pct < self.extreme_threshold:
            if current_time - self.last_critical_time > self.alert_cooldown_sec:
                self.last_critical_time = current_time
                self.alert_count += 1
                msg = (
                    f"Cost CRITICAL: Budget utilization at {utilization_pct:.1f}% "
                    f"(threshold: {self.critical_threshold}%)"
                )
                return "CRITICAL", msg
            return "CRITICAL", None

        if utilization_pct < 100.0:
            msg = f"Cost EXTREME: Budget utilization at {utilization_pct:.1f}% (threshold: {self.extreme_threshold}%)"
            return "EXTREME", msg

        return "BLOCKED", f"Budget limit reached ({utilization_pct:.1f}%)"


class BudgetCircuitBreaker:
    """Emergency circuit breaker for runaway costs.

    Implements 3-strike rule: 3 policy violations trigger emergency shutoff.
    """

    def __init__(self, strike_limit: int = 3):
        """Initialize circuit breaker.

        Args:
            strike_limit: Number of violations before opening (default: 3)
        """
        self.strike_limit = strike_limit
        self.strike_count = 0
        self.is_open = False
        self.open_time = 0.0
        self.reset_timeout_sec = 300  # Auto-reset after 5 minutes

    def record_violation(self) -> bool:
        """Record a policy violation.

        Returns:
            True if circuit breaker opened, False otherwise
        """
        self.strike_count += 1
        logger.warning(f"Budget violation recorded: {self.strike_count}/{self.strike_limit}")

        if self.strike_count >= self.strike_limit:
            self.is_open = True
            self.open_time = time.time()
            logger.error(
                f"Budget circuit breaker OPENED after {self.strike_count} violations. "
                "Blocking all operations until manual reset or timeout."
            )
            return True

        return False

    def check_state(self) -> bool:
        """Check if circuit breaker is currently open.

        Returns:
            True if open, False if closed or auto-reset
        """
        if not self.is_open:
            return False

        # Check if auto-reset timeout elapsed
        if time.time() - self.open_time > self.reset_timeout_sec:
            logger.info(f"Budget circuit breaker auto-reset after {self.reset_timeout_sec}s")
            self.is_open = False
            self.strike_count = 0
            return False

        return True

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        logger.info("Budget circuit breaker manually reset")
        self.is_open = False
        self.strike_count = 0
        self.open_time = 0.0


class BudgetEnforcer:
    """Enforce budget limits with soft-stop policy and circuit breaker.

    Design principles:
    - Non-blocking budget checks (<0.5ms, cached for 60s)
    - Soft-stop: Finish current task, block new ones
    - Progressive alerts at 80%, 90%, 95%
    - Circuit breaker for emergency shutoff
    - Graceful degradation: budget check failures don't crash the system
    """

    _current_instance: ClassVar[Optional["BudgetEnforcer"]] = None

    def __init__(
        self,
        budget_usd: float,
        policy: BudgetPolicy = BudgetPolicy.SOFT_STOP,
        warn_threshold_pct: int = 80,
        critical_threshold_pct: int = 90,
        extreme_threshold_pct: int = 95,
        cache_ttl_sec: int = 60,
        vault_logger=None,
    ):
        """Initialize budget enforcer.

        Args:
            budget_usd: Total budget in USD
            policy: Enforcement policy (default: SOFT_STOP)
            warn_threshold_pct: Warning threshold (default: 80%)
            critical_threshold_pct: Critical threshold (default: 90%)
            extreme_threshold_pct: Extreme threshold (default: 95%)
            cache_ttl_sec: Budget check cache TTL (default: 60s)
            vault_logger: Optional vault logger for alerts
        """
        self.budget_usd = budget_usd
        self.policy = policy
        self.cache_ttl_sec = cache_ttl_sec
        self.vault_logger = vault_logger

        self.alert_manager = CostAlertManager(
            warn_threshold_pct=warn_threshold_pct,
            critical_threshold_pct=critical_threshold_pct,
            extreme_threshold_pct=extreme_threshold_pct,
        )
        self.circuit_breaker = BudgetCircuitBreaker()

        # Cached state (refreshed every 60s)
        self._cached_state: BudgetState | None = None
        self._cache_time = 0.0

    @classmethod
    def get_current(cls) -> Optional["BudgetEnforcer"]:
        """Get current budget enforcer."""
        return cls._current_instance

    @classmethod
    def set_current(cls, enforcer: Optional["BudgetEnforcer"]) -> None:
        """Set current budget enforcer."""
        cls._current_instance = enforcer

    def check_budget(
        self,
        current_cost_usd: float,
    ) -> tuple[bool, str]:
        """Check if operation can proceed (cached, <0.5ms).

        Args:
            current_cost_usd: Current session cost in USD

        Returns:
            Tuple of (can_proceed, reason)
            - can_proceed: True if within budget and policy allows
            - reason: Explanation if blocked
        """
        # Check circuit breaker first (immediate, no cache)
        if self.circuit_breaker.check_state():
            return False, "Budget circuit breaker is OPEN (emergency shutoff)"

        # Calculate utilization
        utilization_pct = (current_cost_usd / self.budget_usd * 100) if self.budget_usd > 0 else 0

        # Evaluate alerts
        status, alert = self.alert_manager.evaluate(utilization_pct)

        # Log alert if present (async, non-blocking)
        if alert:
            try:
                asyncio.create_task(self._log_alert_async(alert))
            except RuntimeError:
                # No event loop, log synchronously
                logger.warning(alert)

        # Apply policy
        if self.policy == BudgetPolicy.SOFT_STOP and status == "BLOCKED":
            # Record violation for circuit breaker
            self.circuit_breaker.record_violation()
            return False, f"Budget limit exceeded: {utilization_pct:.1f}%"

        if self.policy == BudgetPolicy.HARD_STOP and status in (
            "CRITICAL",
            "EXTREME",
            "BLOCKED",
        ):
            return False, f"Hard stop policy: {status} status ({utilization_pct:.1f}%)"

        if self.policy == BudgetPolicy.WARNING_ONLY:
            return True, alert or "Budget OK"

        return True, f"{status}: {utilization_pct:.1f}% utilization"

    async def _log_alert_async(self, alert: str) -> None:
        """Log alert to vault asynchronously (best-effort)."""
        if not self.vault_logger:
            logger.warning(alert)
            return

        try:
            await asyncio.wait_for(
                self.vault_logger.log_alert(alert, severity="warning"),
                timeout=2.0,
            )
        except (TimeoutError, Exception):
            # Vault failure: log locally
            logger.warning(f"{alert} (vault log failed)")

    def get_budget_state(self, current_cost_usd: float) -> BudgetState:
        """Get current budget state.

        Args:
            current_cost_usd: Current session cost in USD

        Returns:
            BudgetState snapshot
        """
        utilization_pct = (current_cost_usd / self.budget_usd * 100) if self.budget_usd > 0 else 0
        remaining = self.budget_usd - current_cost_usd
        status, _ = self.alert_manager.evaluate(utilization_pct)

        return BudgetState(
            total_budget_usd=self.budget_usd,
            current_cost_usd=current_cost_usd,
            remaining_budget_usd=remaining,
            utilization_pct=utilization_pct,
            status=status,
            last_check_time=time.time(),
            alert_count=self.alert_manager.alert_count,
        )

    def reset(self) -> None:
        """Reset enforcer state (testing only)."""
        self.alert_manager.alert_count = 0
        self.alert_manager.last_warn_time = 0.0
        self.alert_manager.last_critical_time = 0.0
        self.circuit_breaker.reset()
        self._cached_state = None
        self._cache_time = 0.0


def get_current_enforcer() -> BudgetEnforcer | None:
    """Get current budget enforcer."""
    return BudgetEnforcer.get_current()


def set_current_enforcer(enforcer: BudgetEnforcer | None) -> None:
    """Set current budget enforcer."""
    BudgetEnforcer.set_current(enforcer)


def reset_current_enforcer() -> None:
    """Reset current budget enforcer (testing only)."""
    BudgetEnforcer.set_current(None)
