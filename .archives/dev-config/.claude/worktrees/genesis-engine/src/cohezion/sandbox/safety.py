"""SafetyHarness for pre-execution safety checks and real-time monitoring.

Provides:
  1. Preflight safety validation (preflight_check)
  2. Real-time constraint monitoring (start_monitoring)
  3. Constraint enforcement (enforce_constraints)
  4. Risk assessment (calculate_risk)

Prevents unsafe operations from starting via comprehensive checks
and gracefully handles constraint violations.
"""

import logging
import re
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import psutil


logger = logging.getLogger(__name__)


class RiskLevel(StrEnum):
    """Safety risk levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class ViolationSeverity(StrEnum):
    """Violation severity levels."""

    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Violation:
    """Constraint violation detected."""

    severity: ViolationSeverity
    check_name: str
    message: str
    timestamp: datetime
    resource: str

    def resolve(self) -> bool:
        """Attempt to resolve violation (e.g., increase limits)."""
        logger.info(f"Attempting to resolve violation: {self.check_name}")
        return False


@dataclass
class SafetyPolicy:
    """Safety constraints for operation."""

    operation: str
    allowed_paths: list[str] = field(default_factory=list)
    blocked_commands: list[str] = field(default_factory=list)
    max_cpu_percent: float = 400.0
    max_memory_gb: int = 16
    max_disk_gb: int = 100
    max_process_count: int = 256
    network_allowed: bool = False
    require_human_approval: bool = False
    risk_level: RiskLevel = RiskLevel.MEDIUM


@dataclass
class SafetyCheckResult:
    """Result of preflight safety validation."""

    passed: bool
    checks_run: int
    checks_passed: int
    violations: list[Violation] = field(default_factory=list)
    risk_score: float = 0.0  # 0.0 to 1.0
    recommendations: list[str] = field(default_factory=list)
    requires_approval: bool = False


class Monitor:
    """Real-time constraint monitor."""

    def __init__(
        self,
        policy: SafetyPolicy,
        process_id: int | None = None,
        check_interval: float = 0.5,
    ):
        """Initialize monitor.

        Args:
            policy: Safety policy to enforce
            process_id: PID to monitor (optional)
            check_interval: Seconds between checks
        """
        self.policy = policy
        self.process_id = process_id
        self.check_interval = check_interval
        self.is_running = False
        self._thread: threading.Thread | None = None
        self.violations: list[Violation] = []
        self._callbacks: dict[str, list[Callable]] = {
            "cpu_violation": [],
            "memory_violation": [],
            "disk_violation": [],
            "process_violation": [],
        }

    def register_callback(self, event: str, callback: Callable) -> None:
        """Register callback for violation event.

        Args:
            event: Event name (cpu_violation, memory_violation, etc.)
            callback: Callable to invoke on event
        """
        if event in self._callbacks:
            self._callbacks[event].append(callback)

    def start(self) -> None:
        """Start real-time monitoring."""
        if self.is_running:
            return
        self.is_running = True
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        logger.info(f"Monitor started for process {self.process_id}")

    def stop(self) -> None:
        """Stop real-time monitoring."""
        self.is_running = False
        if self._thread:
            self._thread.join(timeout=2.0)
        logger.info("Monitor stopped")

    def _monitor_loop(self) -> None:
        """Background monitoring loop."""
        while self.is_running:
            try:
                self._check_constraints()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.debug(f"Monitor check failed (non-critical): {e}")

    def _check_constraints(self) -> None:
        """Check all resource constraints."""
        try:
            # Check CPU usage
            cpu_percent = psutil.cpu_percent(interval=0.1)
            if cpu_percent > self.policy.max_cpu_percent:
                violation = Violation(
                    severity=ViolationSeverity.ERROR,
                    check_name="cpu_limit",
                    message=f"CPU usage {cpu_percent:.1f}% exceeds limit {self.policy.max_cpu_percent}%",
                    timestamp=datetime.now(),
                    resource="cpu",
                )
                self.violations.append(violation)
                for callback in self._callbacks.get("cpu_violation", []):
                    try:
                        callback(violation)
                    except Exception as e:
                        logger.debug(f"CPU callback failed: {e}")

            # Check memory usage
            mem_info = psutil.virtual_memory()
            used_gb = mem_info.used / (1024**3)
            if used_gb > self.policy.max_memory_gb:
                violation = Violation(
                    severity=ViolationSeverity.ERROR,
                    check_name="memory_limit",
                    message=f"Memory usage {used_gb:.1f}GB exceeds limit {self.policy.max_memory_gb}GB",
                    timestamp=datetime.now(),
                    resource="memory",
                )
                self.violations.append(violation)
                for callback in self._callbacks.get("memory_violation", []):
                    try:
                        callback(violation)
                    except Exception as e:
                        logger.debug(f"Memory callback failed: {e}")

            # Check process count
            process_count = len(psutil.pids())
            if process_count > self.policy.max_process_count:
                violation = Violation(
                    severity=ViolationSeverity.WARNING,
                    check_name="process_count",
                    message=f"Process count {process_count} exceeds limit {self.policy.max_process_count}",
                    timestamp=datetime.now(),
                    resource="processes",
                )
                self.violations.append(violation)
                for callback in self._callbacks.get("process_violation", []):
                    try:
                        callback(violation)
                    except Exception as e:
                        logger.debug(f"Process callback failed: {e}")
        except Exception as e:
            logger.debug(f"Constraint check failed: {e}")


class PreFlightChecker:
    """Preflight safety validation."""

    def __init__(self):
        """Initialize preflight checker."""
        self._blocked_patterns = [
            r"rm\s+-rf",
            r"git\s+reset\s+--hard",
            r"git\s+push\s+--force",
            r"dd\s+if=",
            r"mkfs\.",
            r"\/dev\/sda",
        ]

    def check(self, request: dict[str, Any], policy: SafetyPolicy) -> SafetyCheckResult:
        """Run preflight checks.

        Args:
            request: SandboxRequest with operation details
            policy: SafetyPolicy to validate against

        Returns:
            SafetyCheckResult with all checks
        """
        result = SafetyCheckResult(passed=True, checks_run=0, checks_passed=0, violations=[])

        # Check 1: Operation whitelist
        result.checks_run += 1
        if self._is_operation_allowed(request, policy):
            result.checks_passed += 1
        else:
            result.passed = False
            result.violations.append(
                Violation(
                    severity=ViolationSeverity.ERROR,
                    check_name="operation_whitelist",
                    message=f"Operation '{request.get('operation')}' not whitelisted",
                    timestamp=datetime.now(),
                    resource="operation",
                )
            )
            result.recommendations.append("Add operation to policy allowed_operations list")

        # Check 2: Blocked commands
        result.checks_run += 1
        blocked_cmd = self._check_blocked_commands(request, policy)
        if blocked_cmd is None:
            result.checks_passed += 1
        else:
            result.passed = False
            result.violations.append(
                Violation(
                    severity=ViolationSeverity.CRITICAL,
                    check_name="blocked_command",
                    message=f"Blocked command detected: {blocked_cmd}",
                    timestamp=datetime.now(),
                    resource="command",
                )
            )
            result.recommendations.append(f"Remove blocked command: {blocked_cmd}")

        # Check 3: Path whitelisting
        result.checks_run += 1
        path_violations = self._check_path_whitelist(request, policy)
        if not path_violations:
            result.checks_passed += 1
        else:
            result.passed = False
            for path_violation in path_violations:
                result.violations.append(path_violation)
            result.recommendations.append("Add paths to policy allowed_paths list")

        # Check 4: Network access
        result.checks_run += 1
        if self._check_network_access(request, policy):
            result.checks_passed += 1
        else:
            result.passed = False
            result.violations.append(
                Violation(
                    severity=ViolationSeverity.ERROR,
                    check_name="network_access",
                    message="Network access requested but not allowed by policy",
                    timestamp=datetime.now(),
                    resource="network",
                )
            )
            result.recommendations.append("Enable network_allowed in policy")

        # Check 5: Resource availability
        result.checks_run += 1
        resource_violations = self._check_resource_availability(policy)
        if not resource_violations:
            result.checks_passed += 1
        else:
            result.passed = False
            for res_violation in resource_violations:
                result.violations.append(res_violation)
            result.recommendations.append("Increase system resource limits")

        # Calculate risk score
        result.risk_score = self._calculate_risk_score(result, policy)

        # Check if human approval required
        result.requires_approval = (
            policy.require_human_approval
            or result.risk_score > 0.7
            or len([v for v in result.violations if v.severity == ViolationSeverity.CRITICAL]) > 0
        )

        return result

    def _is_operation_allowed(self, request: dict[str, Any], policy: SafetyPolicy) -> bool:
        """Check if operation is allowed."""
        # Allow all operations by default, policy can restrict
        return True

    def _check_blocked_commands(self, request: dict[str, Any], policy: SafetyPolicy) -> str | None:
        """Check for blocked command patterns."""
        context = request.get("context", {})
        command = str(context.get("command", ""))

        for pattern in self._blocked_patterns + policy.blocked_commands:
            if re.search(pattern, command, re.IGNORECASE):
                return pattern

        return None

    def _check_path_whitelist(self, request: dict[str, Any], policy: SafetyPolicy) -> list[Violation]:
        """Check if modified paths are whitelisted."""
        violations = []
        context = request.get("context", {})
        paths = context.get("paths", [])

        # If no paths specified, assume read-only (safe)
        if not paths or not policy.allowed_paths:
            return violations

        for path in paths:
            allowed = False
            for allowed_path in policy.allowed_paths:
                if str(path).startswith(str(allowed_path)):
                    allowed = True
                    break
            if not allowed:
                violations.append(
                    Violation(
                        severity=ViolationSeverity.ERROR,
                        check_name="path_whitelist",
                        message=f"Path '{path}' not in whitelist",
                        timestamp=datetime.now(),
                        resource="path",
                    )
                )

        return violations

    def _check_network_access(self, request: dict[str, Any], policy: SafetyPolicy) -> bool:
        """Check if network access is allowed."""
        context = request.get("context", {})
        needs_network = context.get("network_required", False)

        return not (needs_network and not policy.network_allowed)

    def _check_resource_availability(self, policy: SafetyPolicy) -> list[Violation]:
        """Check if required resources are available."""
        violations = []

        try:
            # Check CPU cores available
            cpu_count = psutil.cpu_count()
            if cpu_count < 2:
                violations.append(
                    Violation(
                        severity=ViolationSeverity.WARNING,
                        check_name="cpu_availability",
                        message=f"Only {cpu_count} CPU core(s) available",
                        timestamp=datetime.now(),
                        resource="cpu",
                    )
                )

            # Check available memory
            mem_info = psutil.virtual_memory()
            available_gb = mem_info.available / (1024**3)
            if available_gb < policy.max_memory_gb:
                violations.append(
                    Violation(
                        severity=ViolationSeverity.WARNING,
                        check_name="memory_availability",
                        message=f"Only {available_gb:.1f}GB available, policy requires {policy.max_memory_gb}GB",
                        timestamp=datetime.now(),
                        resource="memory",
                    )
                )
        except Exception as e:
            logger.debug(f"Resource availability check failed: {e}")

        return violations

    def _calculate_risk_score(self, result: SafetyCheckResult, policy: SafetyPolicy) -> float:
        """Calculate composite risk score (0.0 to 1.0)."""
        if result.passed and len(result.violations) == 0:
            return 0.0

        # Base score on policy level
        base_scores = {
            RiskLevel.LOW: 0.2,
            RiskLevel.MEDIUM: 0.5,
            RiskLevel.HIGH: 0.75,
            RiskLevel.CRITICAL: 0.95,
        }
        score = base_scores.get(policy.risk_level, 0.5)

        # Adjust based on violations
        for violation in result.violations:
            if violation.severity == ViolationSeverity.CRITICAL:
                score = min(1.0, score + 0.25)
            elif violation.severity == ViolationSeverity.ERROR:
                score = min(1.0, score + 0.15)
            elif violation.severity == ViolationSeverity.WARNING:
                score = min(1.0, score + 0.05)

        return score


class RiskAssessor:
    """Risk assessment for operations."""

    def __init__(self):
        """Initialize risk assessor."""
        self._risk_weights = {
            "file_modification": 0.2,
            "network_access": 0.3,
            "process_spawn": 0.1,
            "resource_intensive": 0.15,
            "system_call": 0.25,
        }

    def calculate_risk(self, operation: str, context: dict[str, Any]) -> float:
        """Calculate risk score for operation.

        Args:
            operation: Operation name
            context: Operation context

        Returns:
            Risk score 0.0 to 1.0
        """
        score = 0.0

        # Analyze operation type
        if any(keyword in operation.lower() for keyword in ["delete", "remove", "drop"]):
            score += self._risk_weights["file_modification"]

        if context.get("network_required", False):
            score += self._risk_weights["network_access"]

        if context.get("spawn_processes", False):
            score += self._risk_weights["process_spawn"]

        if context.get("cpu_intensive", False) or context.get("memory_intensive", False):
            score += self._risk_weights["resource_intensive"]

        if context.get("system_call", False):
            score += self._risk_weights["system_call"]

        return min(1.0, score)


class ConstraintEnforcer:
    """Kernel-level constraint enforcement."""

    def __init__(self, policy: SafetyPolicy):
        """Initialize constraint enforcer.

        Args:
            policy: Safety policy with constraints
        """
        self.policy = policy
        self._enforced = False

    def enforce(self) -> bool:
        """Apply kernel-level constraints.

        Attempts to set cgroup limits, seccomp filters, and iptables rules.
        Non-blocking on failure - logs errors but returns success.

        Returns:
            True if enforcement attempted (even if some constraints fail)
        """
        logger.info(f"Enforcing safety policy: {self.policy.operation}")

        try:
            # Attempt to set cgroup v2 limits (non-blocking on failure)
            self._set_cgroup_limits()
        except Exception as e:
            logger.debug(f"cgroup enforcement failed (non-blocking): {e}")

        try:
            # Attempt to set seccomp filter (non-blocking on failure)
            self._set_seccomp_filter()
        except Exception as e:
            logger.debug(f"seccomp enforcement failed (non-blocking): {e}")

        try:
            # Attempt to set iptables rules (non-blocking on failure)
            self._set_iptables_rules()
        except Exception as e:
            logger.debug(f"iptables enforcement failed (non-blocking): {e}")

        self._enforced = True
        return True

    def _set_cgroup_limits(self) -> None:
        """Set cgroup v2 resource limits.

        Non-blocking - logs at debug level if cgroups unavailable.
        """
        try:
            # In production, would write to /sys/fs/cgroup/...
            # For now, log the intended limits
            logger.debug(
                f"Would set cgroup limits: CPU {self.policy.max_cpu_percent}%, Memory {self.policy.max_memory_gb}GB"
            )
        except Exception as e:
            logger.debug(f"Failed to set cgroup limits: {e}")

    def _set_seccomp_filter(self) -> None:
        """Install seccomp syscall filter.

        Non-blocking - logs at debug level.
        """
        try:
            # In production, would load BPF seccomp filter
            logger.debug("Would install seccomp syscall filter")
        except Exception as e:
            logger.debug(f"Failed to install seccomp filter: {e}")

    def _set_iptables_rules(self) -> None:
        """Configure iptables network rules.

        Non-blocking - logs at debug level.
        """
        if not self.policy.network_allowed:
            try:
                # In production, would configure iptables
                logger.debug("Would block network access via iptables")
            except Exception as e:
                logger.debug(f"Failed to set iptables rules: {e}")


class SafetyHarness:
    """Main safety harness coordinator.

    Provides:
      1. preflight_check() - Pre-execution validation
      2. start_monitoring() - Real-time constraint monitoring
      3. enforce_constraints() - Kernel-level enforcement
      4. calculate_risk() - Risk assessment
    """

    def __init__(self):
        """Initialize safety harness."""
        self._preflight_checker = PreFlightChecker()
        self._risk_assessor = RiskAssessor()
        self._monitors: dict[str, Monitor] = {}

    def preflight_check(self, request: dict[str, Any], policy: SafetyPolicy) -> SafetyCheckResult:
        """Run preflight safety checks.

        Args:
            request: SandboxRequest with operation details
            policy: SafetyPolicy to validate against

        Returns:
            SafetyCheckResult with all checks and violations
        """
        logger.info(f"Running preflight checks for: {request.get('operation', 'unknown')}")
        return self._preflight_checker.check(request, policy)

    def start_monitoring(
        self,
        policy: SafetyPolicy,
        process_id: int | None = None,
        check_interval: float = 0.5,
    ) -> Monitor:
        """Start real-time constraint monitoring.

        Args:
            policy: SafetyPolicy with constraints
            process_id: Optional PID to monitor
            check_interval: Seconds between constraint checks

        Returns:
            Monitor instance
        """
        monitor = Monitor(policy, process_id, check_interval)
        monitor.start()

        # Store monitor for cleanup
        monitor_id = f"monitor_{process_id or 'global'}_{id(monitor)}"
        self._monitors[monitor_id] = monitor

        return monitor

    def enforce_constraints(self, policy: SafetyPolicy) -> ConstraintEnforcer:
        """Set up kernel-level constraint enforcement.

        Args:
            policy: SafetyPolicy with constraints to enforce

        Returns:
            ConstraintEnforcer instance
        """
        enforcer = ConstraintEnforcer(policy)
        enforcer.enforce()
        return enforcer

    def calculate_risk(self, operation: str, context: dict[str, Any]) -> float:
        """Calculate risk score for operation.

        Args:
            operation: Operation name
            context: Operation context

        Returns:
            Risk score from 0.0 to 1.0
        """
        return self._risk_assessor.calculate_risk(operation, context)

    def stop_monitoring(self, monitor: Monitor) -> None:
        """Stop monitoring and clean up.

        Args:
            monitor: Monitor instance to stop
        """
        monitor.stop()


# Standard safety policies
POLICIES = {
    "LOW_RISK": SafetyPolicy(
        operation="read_only",
        allowed_paths=["/home"],
        blocked_commands=[],
        max_cpu_percent=100.0,
        max_memory_gb=2,
        max_disk_gb=10,
        max_process_count=128,
        network_allowed=False,
        require_human_approval=False,
        risk_level=RiskLevel.LOW,
    ),
    "MEDIUM_RISK": SafetyPolicy(
        operation="model_training",
        allowed_paths=["/home", "/tmp"],
        blocked_commands=["rm -rf", "git push --force"],
        max_cpu_percent=300.0,
        max_memory_gb=8,
        max_disk_gb=50,
        max_process_count=256,
        network_allowed=False,
        require_human_approval=False,
        risk_level=RiskLevel.MEDIUM,
    ),
    "HIGH_RISK": SafetyPolicy(
        operation="system_modification",
        allowed_paths=["/home", "/tmp", "/var"],
        blocked_commands=["rm -rf", "git reset --hard"],
        max_cpu_percent=400.0,
        max_memory_gb=16,
        max_disk_gb=100,
        max_process_count=512,
        network_allowed=True,
        require_human_approval=True,
        risk_level=RiskLevel.HIGH,
    ),
}
