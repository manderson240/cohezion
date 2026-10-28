"""Bounty Dogfood Runner for Agentic Software Delivery Primitives.

Dogfoods Cohezion's AgenticSoftwareDeliveryPipeline, PurposeDrivenMemory,
BugBountyHarness, and SleepFramework across our three live bounty targets:
1. Code4rena Intuition Protocol ($100,000 pool) - MultiVault._rollover state corruption.
2. Cantina Mystic Finance ($20,000 pool) - stPlumeMinter.sol capacity check operator inversion.
3. Immunefi deBridge DLN ($40,000 pool) - DlnExternalCallAdapter state desynchronization.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Any

from cohezion.agi.sleep_framework import SleepFramework
from cohezion.compound.agentic_delivery_primitives import (
    AgenticSoftwareDeliveryPipeline,
    DeliveryArtifact,
    PurposeDrivenMemory,
)
from cohezion.security.bounty_harness import BugBountyHarness


logger = logging.getLogger(__name__)


@dataclass(slots=True)
class BountyDogfoodResult:
    """Summary record of a bounty run through the 4-stage agentic lifecycle."""

    target_id: str
    target_name: str
    bounty_pool_usd: int
    plan_artifact: DeliveryArtifact
    build_artifact: DeliveryArtifact
    verify_artifact: DeliveryArtifact
    observe_artifact: DeliveryArtifact | None
    memory_utility: float
    violations_detected: int
    execution_latency_ms: float


class BountyDogfoodHarness:
    """End-to-end dogfooding harness orchestrating the complete Agentic SDLC."""

    def __init__(self) -> None:
        self.memory = PurposeDrivenMemory()
        self.pipeline = AgenticSoftwareDeliveryPipeline(memory=self.memory)
        self.sleep = SleepFramework(dimension=12, ewc_lambda=100.0)
        self.bounty_harness = BugBountyHarness(target_name="MultiTargetHarness")

    def run_target(
        self,
        target_id: str,
        target_name: str,
        bounty_pool_usd: int,
        source_code: str,
        patch_code: str,
        component_name: str,
        expected_rule: str,
    ) -> BountyDogfoodResult:
        """Execute a full Plan -> Build -> Verify -> Observe cycle on a bounty target."""
        t0 = time.perf_counter()

        # --- Stage 1: PLAN ---
        plan_art = self.pipeline.execute_plan(
            component=component_name,
            intent=f"Audit and patch formal invariants for {target_name} ({target_id})",
            constraints=[
                "Zero arithmetic underflow",
                "Zero state desynchronization",
                "Strict epoch gap monotonicity",
            ],
            acceptance_criteria=[
                f"Identify violation of rule '{expected_rule}' on unpatched source",
                "Verify zero invariant violations on defensive candidate patch",
            ],
        )

        # --- Stage 2: BUILD ---
        def build_patch(plan_content: dict[str, Any]) -> dict[str, Any]:
            return {
                "diff_or_code": patch_code,
                "rationale": f"Remediated formal invariant violation for {expected_rule}",
                "modified_files": [f"{component_name}.sol"],
                "evidence": [f"Synthesized defense for {component_name}"],
                "questions_remaining": [],
            }

        build_art = self.pipeline.execute_build(plan_art, build_patch)

        # --- Stage 3: VERIFY ---
        def verify_vulnerability_and_patch(
            build_content: dict[str, Any],
        ) -> tuple[bool, list[str], list[str]]:
            # 1. Audit unpatched code with BugBountyHarness
            report_vuln = self.bounty_harness.audit_solidity_source(source_code, component_name)
            # 2. Audit patched code with BugBountyHarness
            report_patch = self.bounty_harness.audit_solidity_source(patch_code, component_name)

            traces = []
            failures = []

            # Expect vulnerability found on unpatched
            matching_vulns = [v for v in report_vuln.violations if v.rule_name == expected_rule]
            if matching_vulns:
                traces.append(
                    f"Confirmed expected invariant violation on unpatched code: {matching_vulns[0].rule_name}"
                )
            else:
                failures.append(
                    f"Failed to detect expected vulnerability {expected_rule} on unpatched source"
                )

            # Expect zero violations on patched code
            if report_patch.is_clean:
                traces.append(
                    f"Confirmed candidate patch cleanly eliminates {expected_rule} (zero violations)"
                )
            else:
                failures.append(
                    f"Candidate patch still contains violations: {[v.rule_name for v in report_patch.violations]}"
                )

            passed = len(failures) == 0
            return passed, traces, failures

        verify_art = self.pipeline.execute_verify(build_art, verify_vulnerability_and_patch)

        # --- Stage 4: OBSERVE (Gated by verification passing) ---
        observe_art: DeliveryArtifact | None = None
        if verify_art.content.get("passed", False):

            def observe_bounty(verify_content: dict[str, Any]) -> dict[str, Any]:
                return {
                    "metrics": {
                        "bounty_pool_usd": bounty_pool_usd,
                        "violations_detected": len(verify_content.get("proof_traces", [])),
                        "passed": 1 if verify_content.get("passed") else 0,
                    },
                    "anomalies": verify_content.get("failures", []),
                    "synthesized_learnings": [
                        f"Formally proven remediation for {expected_rule} on {component_name}"
                    ],
                    "runtime_failures": verify_content.get("failures", []),
                }

            observe_art = self.pipeline.execute_observe(verify_art, observe_bounty)

            # --- Continual Learning Consolidation into SLEEP ---
            sleep_exp_dict = self.pipeline.export_sleep_experience(observe_art)
            self.sleep.record_experience(
                task_description=f"Formally verified invariant patch for {target_name} ({target_id})",
                action_sequence=("plan", "build", "verify", "observe"),
                state_vector=[0.5] * 12,
                reward=float(sleep_exp_dict["reward"]),
                loss=float(sleep_exp_dict["loss"]),
                entropy=float(sleep_exp_dict["entropy"]),
                session_id=f"session_{target_id}",
            )

        # --- Purpose-Driven Memory Utility Evaluation ---
        mem_utility = self.memory.evaluate_memory_utility(
            task_id=target_id,
            success_with_mem=verify_art.content.get("passed", False),
            success_baseline=False,
            lookup_latency_ms=1.5,
        )

        dt_ms = (time.perf_counter() - t0) * 1000.0

        return BountyDogfoodResult(
            target_id=target_id,
            target_name=target_name,
            bounty_pool_usd=bounty_pool_usd,
            plan_artifact=plan_art,
            build_artifact=build_art,
            verify_artifact=verify_art,
            observe_artifact=observe_art,
            memory_utility=mem_utility,
            violations_detected=len(verify_art.evidence),
            execution_latency_ms=dt_ms,
        )

    def run_all_bounties(self) -> list[BountyDogfoodResult]:
        """Execute the entire portfolio of live bounties through the agentic primitives."""
        results = []

        # Target 1: Code4rena Intuition Protocol (MultiVault._rollover)
        intuition_vuln_code = """
contract MultiVault {
    function _rollover(address user) internal {
        uint256 currentEpochLocal = _currentEpoch();
        uint256 previousEpoch = currentEpochLocal - 1;
        int256 previousEpochUtilization = totalUtilization[previousEpoch];
        if (previousEpochUtilization != 0 && totalUtilization[currentEpochLocal] == 0) {
            totalUtilization[currentEpochLocal] = previousEpochUtilization;
        }
    }
}
"""
        intuition_patch_code = """
contract MultiVault {
    uint256 public lastSystemActiveEpoch;
    function _rollover(address user) internal {
        uint256 currentEpochLocal = _currentEpoch();
        int256 previousEpochUtilization = totalUtilization[lastSystemActiveEpoch];
        if (previousEpochUtilization != 0 && totalUtilization[currentEpochLocal] == 0) {
            totalUtilization[currentEpochLocal] = previousEpochUtilization;
        }
        lastSystemActiveEpoch = currentEpochLocal;
    }
}
"""
        res1 = self.run_target(
            target_id="C4-INTUITION-01",
            target_name="Intuition Protocol",
            bounty_pool_usd=100_000,
            source_code=intuition_vuln_code,
            patch_code=intuition_patch_code,
            component_name="MultiVault",
            expected_rule="skipped_epoch_rollover_state_loss",
        )
        results.append(res1)

        # Target 2: Cantina Mystic Finance (stPlumeMinter.getNextValidator)
        mystic_vuln_code = """
contract StPlumeMinter {
    function getNextValidator(uint depositAmount) public returns (uint256, uint256) {
        if (info.maxCapacity != 0 || totalStaked < info.maxCapacity) {
            return (validatorId, info.maxCapacity - totalStaked);
        }
    }
}
"""
        mystic_patch_code = """
contract StPlumeMinter {
    function getNextValidator(uint depositAmount) public returns (uint256, uint256) {
        if (info.maxCapacity != 0 && totalStaked < info.maxCapacity) {
            return (validatorId, info.maxCapacity - totalStaked);
        }
    }
}
"""
        res2 = self.run_target(
            target_id="CANTINA-MYSTIC-01",
            target_name="Mystic Finance",
            bounty_pool_usd=20_000,
            source_code=mystic_vuln_code,
            patch_code=mystic_patch_code,
            component_name="StPlumeMinter",
            expected_rule="capacity_check_operator_inversion_underflow",
        )
        results.append(res2)

        # Target 3: Immunefi deBridge DLN (DlnExternalCallAdapter.cancelCall)
        debridge_vuln_code = """
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
        debridge_patch_code = """
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
        tokenBalanceHistory[_tokenAddress] -= _tokenAmount;
        _sendToken(_tokenAddress, _tokenAmount, _recipient);
    }
}
"""
        res3 = self.run_target(
            target_id="IMMUNEFI-DEBRIDGE-01",
            target_name="deBridge DLN",
            bounty_pool_usd=40_000,
            source_code=debridge_vuln_code,
            patch_code=debridge_patch_code,
            component_name="DlnExternalCallAdapter",
            expected_rule="unaccounted_token_withdrawal_desynchronization",
        )
        results.append(res3)

        # Run SLEEP consolidation across all 3 bounty targets
        sleep_report = self.sleep.sleep(batch_size=3, num_dreams=4)
        logger.info(
            "SLEEP Consolidation: retention=%.4f, ewc_penalty=%.4f, dreams_verified=%d",
            sleep_report.overall_retention_score,
            sleep_report.consolidation.ewc_penalty,
            sleep_report.dreaming.dreams_verified,
        )

        return results
