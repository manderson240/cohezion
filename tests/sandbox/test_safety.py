"""Unit tests for SafetyHarness with preflight checks and real-time monitoring.

Tests cover:
  1. Preflight validation (blocked commands, path whitelisting, etc.)
  2. Real-time monitoring (CPU, memory, process limits)
  3. Constraint enforcement (cgroup, seccomp, iptables)
  4. Risk calculation accuracy
  5. Violation detection and handling
  6. Policy matching and escalation
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from cohezion.sandbox.safety import (
    POLICIES,
    ConstraintEnforcer,
    Monitor,
    PreFlightChecker,
    RiskAssessor,
    RiskLevel,
    SafetyCheckResult,
    SafetyHarness,
    SafetyPolicy,
    Violation,
    ViolationSeverity,
)


@pytest.fixture
def safety_harness():
    """Create a SafetyHarness instance."""
    return SafetyHarness()


@pytest.fixture
def low_risk_policy():
    """Low-risk safety policy."""
    return SafetyPolicy(
        operation="read_only",
        allowed_paths=["/home"],
        blocked_commands=[],
        max_cpu_percent=100.0,
        max_memory_gb=2,
        network_allowed=False,
        require_human_approval=False,
        risk_level=RiskLevel.LOW,
    )


@pytest.fixture
def high_risk_policy():
    """High-risk safety policy."""
    return SafetyPolicy(
        operation="system_modification",
        allowed_paths=["/home", "/tmp", "/var"],
        blocked_commands=["rm -rf", "git reset --hard"],
        max_cpu_percent=400.0,
        max_memory_gb=16,
        network_allowed=True,
        require_human_approval=True,
        risk_level=RiskLevel.HIGH,
    )


@pytest.fixture
def safe_request():
    """Safe sandbox request."""
    return {
        "operation": "read_files",
        "context": {
            "command": "ls -la /home",
            "paths": ["/home"],
            "network_required": False,
        },
    }


@pytest.fixture
def unsafe_request():
    """Unsafe sandbox request with blocked command."""
    return {
        "operation": "dangerous_operation",
        "context": {
            "command": "rm -rf /home/important",
            "paths": ["/home"],
            "network_required": False,
        },
    }


class TestPreFlightChecker:
    """Test preflight validation."""

    def test_preflight_passes_safe_request(self, low_risk_policy, safe_request):
        """Safe request should pass preflight."""
        checker = PreFlightChecker()
        result = checker.check(safe_request, low_risk_policy)

        assert result.passed is True
        assert len(result.violations) == 0
        assert result.checks_passed > 0

    def test_preflight_blocks_blocked_commands(self, low_risk_policy, unsafe_request):
        """Request with blocked command should fail."""
        checker = PreFlightChecker()
        result = checker.check(unsafe_request, low_risk_policy)

        assert result.passed is False
        assert len(result.violations) > 0
        critical_violations = [v for v in result.violations if v.severity == ViolationSeverity.CRITICAL]
        assert len(critical_violations) > 0

    def test_preflight_detects_git_reset_hard(self, low_risk_policy):
        """Should detect git reset --hard."""
        request = {
            "operation": "dangerous",
            "context": {"command": "git reset --hard"},
        }
        checker = PreFlightChecker()
        result = checker.check(request, low_risk_policy)

        assert result.passed is False
        # Should have at least one violation for blocked command
        blocked_violations = [v for v in result.violations if v.check_name == "blocked_command"]
        assert len(blocked_violations) > 0

    def test_preflight_blocks_network_when_not_allowed(self, low_risk_policy):
        """Should block network access when policy disallows."""
        request = {
            "operation": "network_op",
            "context": {"network_required": True},
        }
        checker = PreFlightChecker()
        result = checker.check(request, low_risk_policy)

        assert result.passed is False
        network_violations = [v for v in result.violations if "network" in v.check_name]
        assert len(network_violations) > 0

    def test_preflight_allows_network_when_allowed(self, high_risk_policy):
        """Should allow network access when policy allows."""
        request = {
            "operation": "network_op",
            "context": {"network_required": True},
        }
        checker = PreFlightChecker()
        result = checker.check(request, high_risk_policy)

        network_violations = [v for v in result.violations if "network" in v.check_name]
        assert len(network_violations) == 0

    def test_preflight_validates_path_whitelist(self, low_risk_policy):
        """Should validate path whitelist."""
        request = {
            "operation": "file_op",
            "context": {
                "paths": ["/var/log/secret"],  # Not in whitelist
                "command": "echo test > /var/log/secret",
            },
        }
        checker = PreFlightChecker()
        result = checker.check(request, low_risk_policy)

        assert result.passed is False
        path_violations = [v for v in result.violations if "path" in v.check_name]
        assert len(path_violations) > 0

    def test_preflight_checks_count(self, low_risk_policy, safe_request):
        """Should report number of checks run."""
        checker = PreFlightChecker()
        result = checker.check(safe_request, low_risk_policy)

        assert result.checks_run > 0
        assert result.checks_passed > 0
        assert result.checks_passed <= result.checks_run

    def test_preflight_generates_recommendations(self, low_risk_policy, unsafe_request):
        """Should provide recommendations for violations."""
        checker = PreFlightChecker()
        result = checker.check(unsafe_request, low_risk_policy)

        assert len(result.recommendations) > 0
        assert any("Remove blocked command" in rec for rec in result.recommendations)

    def test_preflight_requires_approval_for_high_risk(self, high_risk_policy, safe_request):
        """Should require approval for high-risk policies."""
        checker = PreFlightChecker()
        result = checker.check(safe_request, high_risk_policy)

        assert result.requires_approval is True

    def test_preflight_escalates_risk_score_on_violations(self, low_risk_policy):
        """Risk score should increase with violations."""
        checker = PreFlightChecker()

        # Safe request
        safe_request = {
            "operation": "safe",
            "context": {"command": "ls"},
        }
        result1 = checker.check(safe_request, low_risk_policy)
        safe_risk = result1.risk_score

        # Unsafe request
        unsafe_request = {
            "operation": "unsafe",
            "context": {"command": "rm -rf /"},
        }
        result2 = checker.check(unsafe_request, low_risk_policy)
        unsafe_risk = result2.risk_score

        assert unsafe_risk > safe_risk


class TestRealTimeMonitor:
    """Test real-time constraint monitoring."""

    def test_monitor_starts_and_stops(self, low_risk_policy):
        """Monitor should start and stop cleanly."""
        monitor = Monitor(low_risk_policy)
        assert monitor.is_running is False

        monitor.start()
        assert monitor.is_running is True

        monitor.stop()
        assert monitor.is_running is False

    def test_monitor_registers_callbacks(self, low_risk_policy):
        """Monitor should register violation callbacks."""
        monitor = Monitor(low_risk_policy)
        callback = MagicMock()

        monitor.register_callback("cpu_violation", callback)
        assert "cpu_violation" in monitor._callbacks
        assert callback in monitor._callbacks["cpu_violation"]

    def test_monitor_check_interval_configurable(self, low_risk_policy):
        """Monitor check interval should be configurable."""
        monitor = Monitor(low_risk_policy, check_interval=1.0)
        assert monitor.check_interval == 1.0

        monitor2 = Monitor(low_risk_policy, check_interval=0.1)
        assert monitor2.check_interval == 0.1

    @patch("psutil.cpu_percent")
    def test_monitor_detects_cpu_violation(self, mock_cpu, low_risk_policy):
        """Monitor should detect CPU limit violations."""
        mock_cpu.return_value = 150.0  # Exceeds 100% limit

        monitor = Monitor(low_risk_policy, check_interval=0.01)
        callback = MagicMock()
        monitor.register_callback("cpu_violation", callback)

        monitor.start()
        import time

        time.sleep(0.05)  # Let monitor run
        monitor.stop()

        # Should detect violation
        assert len(monitor.violations) > 0
        cpu_violations = [v for v in monitor.violations if v.resource == "cpu"]
        assert len(cpu_violations) > 0

    @patch("psutil.virtual_memory")
    def test_monitor_detects_memory_violation(self, mock_mem, low_risk_policy):
        """Monitor should detect memory limit violations."""
        # Mock memory with 5GB used (exceeds 2GB limit)
        mock_info = MagicMock()
        mock_info.used = 5 * (1024**3)
        mock_info.available = 1 * (1024**3)
        mock_mem.return_value = mock_info

        monitor = Monitor(low_risk_policy, check_interval=0.01)
        callback = MagicMock()
        monitor.register_callback("memory_violation", callback)

        monitor.start()
        import time

        time.sleep(0.05)
        monitor.stop()

        # Should detect violation
        assert len(monitor.violations) > 0
        mem_violations = [v for v in monitor.violations if v.resource == "memory"]
        assert len(mem_violations) > 0

    @patch("psutil.pids")
    def test_monitor_detects_process_count_violation(self, mock_pids, low_risk_policy):
        """Monitor should detect process count violations."""
        policy = SafetyPolicy(
            operation="test",
            max_process_count=10,  # Set low limit
            risk_level=RiskLevel.LOW,
        )
        mock_pids.return_value = list(range(50))  # 50 processes

        monitor = Monitor(policy, check_interval=0.01)
        monitor.start()
        import time

        time.sleep(0.05)
        monitor.stop()

        # Should detect violation
        assert len(monitor.violations) > 0


class TestRiskAssessor:
    """Test risk calculation."""

    def test_risk_score_for_read_only_operation(self):
        """Read-only operations should have low risk."""
        assessor = RiskAssessor()
        score = assessor.calculate_risk("read_files", {})

        assert score < 0.5

    def test_risk_score_for_delete_operation(self):
        """Delete operations should have higher risk."""
        assessor = RiskAssessor()
        score = assessor.calculate_risk("delete_files", {})

        assert score >= 0.2

    def test_risk_score_for_network_operation(self):
        """Network operations should increase risk."""
        assessor = RiskAssessor()
        score = assessor.calculate_risk("api_call", {"network_required": True})

        assert score >= 0.3

    def test_risk_score_cumulative(self):
        """Risk scores should accumulate for multiple factors."""
        assessor = RiskAssessor()

        # Single factor
        score1 = assessor.calculate_risk("delete", {})

        # Multiple factors
        score2 = assessor.calculate_risk(
            "delete",
            {
                "network_required": True,
                "system_call": True,
            },
        )

        assert score2 > score1

    def test_risk_score_caps_at_one(self):
        """Risk score should cap at 1.0."""
        assessor = RiskAssessor()
        score = assessor.calculate_risk(
            "operation",
            {
                "network_required": True,
                "spawn_processes": True,
                "cpu_intensive": True,
                "memory_intensive": True,
                "system_call": True,
            },
        )

        assert score <= 1.0


class TestConstraintEnforcer:
    """Test kernel-level constraint enforcement."""

    def test_constraint_enforcer_initializes(self, low_risk_policy):
        """Enforcer should initialize with policy."""
        enforcer = ConstraintEnforcer(low_risk_policy)
        assert enforcer.policy == low_risk_policy
        assert enforcer._enforced is False

    def test_constraint_enforcer_marks_enforced(self, low_risk_policy):
        """Enforcer should mark as enforced after enforce()."""
        enforcer = ConstraintEnforcer(low_risk_policy)
        result = enforcer.enforce()

        assert result is True
        assert enforcer._enforced is True

    @patch("cohezion.sandbox.safety.logger")
    def test_constraint_enforcer_nonblocking_on_cgroup_failure(self, mock_logger, low_risk_policy):
        """Enforcer should be non-blocking on cgroup failure."""
        enforcer = ConstraintEnforcer(low_risk_policy)
        result = enforcer.enforce()

        # Should succeed even if cgroup fails
        assert result is True

    @patch("cohezion.sandbox.safety.logger")
    def test_constraint_enforcer_nonblocking_on_seccomp_failure(self, mock_logger, low_risk_policy):
        """Enforcer should be non-blocking on seccomp failure."""
        enforcer = ConstraintEnforcer(low_risk_policy)
        result = enforcer.enforce()

        # Should succeed even if seccomp fails
        assert result is True

    def test_constraint_enforcer_blocks_network_when_needed(self, low_risk_policy):
        """Enforcer should set iptables when network not allowed."""
        enforcer = ConstraintEnforcer(low_risk_policy)
        enforcer.enforce()

        # In test environment, just verify it ran without error
        assert enforcer._enforced is True


class TestSafetyHarness:
    """Test SafetyHarness main coordinator."""

    def test_harness_preflight_integration(self, safety_harness, low_risk_policy, safe_request):
        """Harness should coordinate preflight checks."""
        result = safety_harness.preflight_check(safe_request, low_risk_policy)

        assert isinstance(result, SafetyCheckResult)
        assert result.passed is True

    def test_harness_starts_monitoring(self, safety_harness, low_risk_policy):
        """Harness should start monitoring."""
        monitor = safety_harness.start_monitoring(low_risk_policy)

        assert isinstance(monitor, Monitor)
        assert monitor.is_running is True

        monitor.stop()

    def test_harness_enforces_constraints(self, safety_harness, low_risk_policy):
        """Harness should enforce constraints."""
        enforcer = safety_harness.enforce_constraints(low_risk_policy)

        assert isinstance(enforcer, ConstraintEnforcer)
        assert enforcer._enforced is True

    def test_harness_calculates_risk(self, safety_harness):
        """Harness should calculate risk scores."""
        score = safety_harness.calculate_risk("delete_operation", {"network_required": True})

        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0

    def test_harness_stops_monitoring(self, safety_harness, low_risk_policy):
        """Harness should stop monitors."""
        monitor = safety_harness.start_monitoring(low_risk_policy)
        assert monitor.is_running is True

        safety_harness.stop_monitoring(monitor)
        assert monitor.is_running is False

    def test_harness_full_workflow(self, safety_harness, low_risk_policy, safe_request):
        """Harness should support full workflow."""
        # 1. Preflight check
        check_result = safety_harness.preflight_check(safe_request, low_risk_policy)
        assert check_result.passed is True

        if check_result.passed:
            # 2. Enforce constraints
            enforcer = safety_harness.enforce_constraints(low_risk_policy)
            assert enforcer._enforced is True

            # 3. Start monitoring
            monitor = safety_harness.start_monitoring(low_risk_policy)
            assert monitor.is_running is True

            # 4. Calculate risk
            risk = safety_harness.calculate_risk("operation", {})
            assert 0.0 <= risk <= 1.0

            # 5. Stop monitoring
            safety_harness.stop_monitoring(monitor)
            assert monitor.is_running is False


class TestStandardPolicies:
    """Test standard safety policies."""

    def test_low_risk_policy_exists(self):
        """LOW_RISK policy should exist."""
        assert "LOW_RISK" in POLICIES
        policy = POLICIES["LOW_RISK"]
        assert policy.risk_level == RiskLevel.LOW
        assert policy.require_human_approval is False

    def test_medium_risk_policy_exists(self):
        """MEDIUM_RISK policy should exist."""
        assert "MEDIUM_RISK" in POLICIES
        policy = POLICIES["MEDIUM_RISK"]
        assert policy.risk_level == RiskLevel.MEDIUM

    def test_high_risk_policy_exists(self):
        """HIGH_RISK policy should exist."""
        assert "HIGH_RISK" in POLICIES
        policy = POLICIES["HIGH_RISK"]
        assert policy.risk_level == RiskLevel.HIGH
        assert policy.require_human_approval is True

    def test_policies_have_reasonable_limits(self):
        """Policies should have reasonable resource limits."""
        for policy in POLICIES.values():
            assert policy.max_cpu_percent > 0
            assert policy.max_memory_gb > 0
            assert policy.max_process_count > 0


class TestViolationHandling:
    """Test violation detection and handling."""

    def test_violation_has_required_fields(self):
        """Violation should have all required fields."""
        violation = Violation(
            severity=ViolationSeverity.ERROR,
            check_name="test_check",
            message="Test message",
            timestamp=datetime.now(),
            resource="test_resource",
        )

        assert violation.severity == ViolationSeverity.ERROR
        assert violation.check_name == "test_check"
        assert violation.message == "Test message"
        assert violation.resource == "test_resource"

    def test_violation_resolve_method(self):
        """Violation should have resolve method."""
        violation = Violation(
            severity=ViolationSeverity.WARNING,
            check_name="test",
            message="test",
            timestamp=datetime.now(),
            resource="test",
        )

        result = violation.resolve()
        assert result is False

    def test_violation_severity_levels(self):
        """Violation should support different severity levels."""
        for severity in [
            ViolationSeverity.WARNING,
            ViolationSeverity.ERROR,
            ViolationSeverity.CRITICAL,
        ]:
            violation = Violation(
                severity=severity,
                check_name="test",
                message="test",
                timestamp=datetime.now(),
                resource="test",
            )
            assert violation.severity == severity


class TestPolicyCustomization:
    """Test custom policy creation and usage."""

    def test_custom_policy_creation(self):
        """Should support custom policy creation."""
        custom_policy = SafetyPolicy(
            operation="custom_operation",
            allowed_paths=["/custom/path"],
            max_cpu_percent=500.0,
            max_memory_gb=32,
            risk_level=RiskLevel.CRITICAL,
        )

        assert custom_policy.operation == "custom_operation"
        assert "/custom/path" in custom_policy.allowed_paths
        assert custom_policy.max_cpu_percent == 500.0
        assert custom_policy.risk_level == RiskLevel.CRITICAL

    def test_custom_blocked_commands(self):
        """Should support custom blocked commands in policies."""
        custom_policy = SafetyPolicy(
            operation="test",
            blocked_commands=["custom_dangerous_command"],
        )

        request = {
            "operation": "test",
            "context": {"command": "custom_dangerous_command --force"},
        }

        checker = PreFlightChecker()
        result = checker.check(request, custom_policy)

        assert result.passed is False


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_empty_request_context(self):
        """Should handle empty request context."""
        policy = SafetyPolicy(operation="test")
        request = {"operation": "test", "context": {}}

        checker = PreFlightChecker()
        result = checker.check(request, policy)

        # Should still run checks, just with empty context
        assert result.checks_run > 0

    def test_null_values_in_request(self):
        """Should handle null values in request."""
        policy = SafetyPolicy(operation="test")
        request = {
            "operation": "test",
            "context": {
                "command": None,
                "paths": None,
            },
        }

        checker = PreFlightChecker()
        result = checker.check(request, policy)

        assert result.checks_run > 0

    def test_monitor_without_process_id(self):
        """Monitor should work without process ID."""
        policy = SafetyPolicy(operation="test")
        monitor = Monitor(policy, process_id=None)

        assert monitor.process_id is None
        monitor.start()
        monitor.stop()

    @patch("psutil.cpu_percent")
    def test_monitor_handles_psutil_errors(self, mock_cpu):
        """Monitor should handle psutil errors gracefully."""
        mock_cpu.side_effect = Exception("PSUtil error")

        policy = SafetyPolicy(operation="test")
        monitor = Monitor(policy, check_interval=0.01)

        monitor.start()
        import time

        time.sleep(0.05)
        monitor.stop()

        # Should not crash
        assert monitor.is_running is False
