"""Unit tests for the BugBountyHarness formal verification engine."""

from __future__ import annotations

import pytest

from cohezion.security.bounty_harness import (
    BugBountyHarness,
    InvariantCategory,
    InvariantSeverity,
)


@pytest.fixture
def harness() -> BugBountyHarness:
    """Provide a standard BugBountyHarness instance."""
    return BugBountyHarness(target_name="ProtocolVault")


def test_clean_code_has_no_violations(harness: BugBountyHarness) -> None:
    """Ensure properly structured code produces a clean audit."""
    clean_code = """
def calculate_reward(principal: int, rate_bps: int, divisor: int = 10000) -> int:
    scaled = (principal * rate_bps) // divisor
    return scaled

class SafeVault:
    def __init__(self) -> None:
        self.balance = 0

    @requires_admin
    def withdraw(self, amount: int) -> None:
        self.balance -= amount
        self.transfer(amount)
"""
    report = harness.audit_python_source(clean_code)
    assert report.is_clean
    assert report.max_severity == InvariantSeverity.INFORMATIONAL
    assert report.analyzed_lines > 0
    assert report.execution_time_ms < 50.0  # Ultra-fast sub-millisecond execution


def test_detects_unprotected_privileged_mutation(harness: BugBountyHarness) -> None:
    """Ensure missing authorization on privileged methods triggers Critical severity."""
    vulnerable_code = """
class VulnerableVault:
    def __init__(self) -> None:
        self.owner = "admin"

    def set_admin(self, new_owner: str) -> None:
        self.owner = new_owner

    def withdraw_funds(self, recipient: str, amount: int) -> None:
        pass
"""
    report = harness.audit_python_source(vulnerable_code)
    assert not report.is_clean
    assert report.max_severity == InvariantSeverity.CRITICAL

    crit_findings = [v for v in report.violations if v.severity == InvariantSeverity.CRITICAL]
    assert len(crit_findings) >= 1
    assert crit_findings[0].category == InvariantCategory.ACCESS_CONTROL
    assert "set_admin" in crit_findings[0].description


def test_detects_checks_effects_interactions_violation(harness: BugBountyHarness) -> None:
    """Ensure mutating state after an external transfer triggers High severity."""
    reentrancy_code = """
class ReentrantTarget:
    def __init__(self) -> None:
        self.user_balances = {}

    @requires_auth
    def payout(self, user: str, amount: int) -> None:
        self.call_external(user, amount)
        self.user_balances[user] -= amount
"""
    report = harness.audit_python_source(reentrancy_code)
    assert not report.is_clean
    assert report.max_severity == InvariantSeverity.HIGH

    cei_findings = [
        v for v in report.violations if v.category == InvariantCategory.CHECKS_EFFECTS_INTERACTIONS
    ]
    assert len(cei_findings) == 1
    assert "reentrancy" in cei_findings[0].rule_name


def test_detects_precision_loss_division_before_multiplication(harness: BugBountyHarness) -> None:
    """Ensure integer division before multiplication triggers precision warning."""
    math_code = """
def compute_shares(amount: int, total_shares: int, total_assets: int) -> int:
    shares = (amount // total_assets) * total_shares
    return shares
"""
    report = harness.audit_python_source(math_code)
    assert not report.is_clean

    math_findings = [
        v for v in report.violations if v.category == InvariantCategory.ARITHMETIC_PRECISION
    ]
    assert len(math_findings) == 1
    assert math_findings[0].severity == InvariantSeverity.MEDIUM


def test_markdown_report_generation(harness: BugBountyHarness) -> None:
    """Ensure audit findings format into a complete, professional disclosure report."""
    vulnerable_code = """
class UnprotectedPool:
    def transfer_ownership(self, new_owner: str) -> None:
        self.owner = new_owner
"""
    report = harness.audit_python_source(vulnerable_code)
    markdown = report.to_markdown()

    assert "# Formal Invariant Audit Report: ProtocolVault" in markdown
    assert "CRITICAL" in markdown
    assert "transfer_ownership" in markdown
    assert "Formal Proof Trace:" in markdown
    assert "Defensive Remediation:" in markdown


def test_detects_solidity_state_desynchronization(harness: BugBountyHarness) -> None:
    """Ensure cancelCall missing tokenBalanceHistory synchronization triggers High severity."""
    solidity_code = """
contract DlnExternalCallAdapter {
    mapping(address => uint256) public tokenBalanceHistory;

    function cancelCall(
        bytes32 _orderId,
        address _callAuthority,
        address _tokenAddress,
        uint256 _tokenAmount,
        address _recipient,
        bytes32 _externalCallHash
    ) external {
        externalCallStatus[callId] = CallStatus.Cancelled;
        _sendToken(_tokenAddress, _tokenAmount, _recipient);
    }
}
"""
    report = harness.audit_solidity_source(solidity_code, contract_name="DlnExternalCallAdapter")
    assert not report.is_clean
    assert report.max_severity == InvariantSeverity.HIGH
    desync_findings = [
        v for v in report.violations if v.category == InvariantCategory.STATE_DESYNCHRONIZATION
    ]
    assert len(desync_findings) == 1
    assert "unaccounted_token_withdrawal_desynchronization" in desync_findings[0].rule_name
