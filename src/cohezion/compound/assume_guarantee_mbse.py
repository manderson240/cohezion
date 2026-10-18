#!/usr/bin/env python3
"""Assume-Guarantee Model-Based Systems Engineering (MBSE) Engine.
===================================================================
Implements formal contract-based design and compositional verification for agentic swarms:
- Contract Specification: C = <A, G> (Assumptions on environment/inputs, Guarantees on agent behavior/outputs).
- Refinement Check: C_impl <= C_spec (A_spec subseteq A_impl and G_impl subseteq G_spec).
- Compositional Algebra: C_1 (x) C_2 computes the composite contract across collaborating agents.
- Runtime Verification: Evaluates state transitions and returns deterministic counterexamples.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any


logger = logging.getLogger("assume_guarantee_mbse")


@dataclass(frozen=True)
class ContractPredicate:
    """A deterministic predicate over a state dictionary."""
    name: str
    description: str
    predicate: Callable[[dict[str, Any]], bool]

    def evaluate(self, state: dict[str, Any]) -> bool:
        try:
            return bool(self.predicate(state))
        except Exception as exc:
            logger.debug("Predicate '%s' raised exception: %s", self.name, exc)
            return False


@dataclass
class AssumeGuaranteeContract:
    """Formal Assume-Guarantee Contract C = <A, G>."""
    name: str
    assumptions: list[ContractPredicate] = field(default_factory=list)
    guarantees: list[ContractPredicate] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def check_assumptions(self, state: dict[str, Any]) -> tuple[bool, list[str]]:
        """Verify whether the environment state satisfies all contract assumptions."""
        failures = [p.name for p in self.assumptions if not p.evaluate(state)]
        return len(failures) == 0, failures

    def check_guarantees(self, state: dict[str, Any]) -> tuple[bool, list[str]]:
        """Verify whether the agent/subsystem state satisfies all contract guarantees."""
        failures = [p.name for p in self.guarantees if not p.evaluate(state)]
        return len(failures) == 0, failures

    def evaluate_step(self, pre_state: dict[str, Any], post_state: dict[str, Any]) -> tuple[bool, str]:
        """Evaluate a state transition under the contract.

        Rule: If assumptions hold on pre_state, guarantees MUST hold on post_state.
        If assumptions fail, the contract is vacuously satisfied (environment assumption broken).
        """
        assumptions_held, failed_a = self.check_assumptions(pre_state)
        if not assumptions_held:
            return True, f"Vacuously satisfied: environment assumptions not met ({', '.join(failed_a)})"

        guarantees_held, failed_g = self.check_guarantees(post_state)
        if not guarantees_held:
            return False, f"Contract violation: guarantees failed ({', '.join(failed_g)})"

        return True, "Contract satisfied: guarantees upheld under assumptions"

    def refines(self, abstract_spec: AssumeGuaranteeContract, test_samples: list[dict[str, Any]] | None = None) -> tuple[bool, str | None]:
        """Check if self refines abstract_spec (self <= abstract_spec).

        Refinement Condition:
        1. Weaker or equal assumptions: abstract_spec.A => self.A
           (Every sample satisfying abstract_spec.A must also satisfy self.A).
        2. Stronger or equal guarantees: self.G => abstract_spec.G
           (Every sample satisfying self.G must also satisfy abstract_spec.G).
        """
        if not test_samples:
            # Static check: implementation must guarantee at least what spec guarantees
            self_g_names = {p.name for p in self.guarantees}
            spec_g_names = {p.name for p in abstract_spec.guarantees}
            if not spec_g_names.issubset(self_g_names):
                missing = spec_g_names - self_g_names
                return False, f"Implementation lacks required guarantees: {missing}"
            return True, None

        # Sample-based state-space verification
        for state in test_samples:
            # 1. Spec assumption implies self assumption
            spec_a_ok, _ = abstract_spec.check_assumptions(state)
            if spec_a_ok:
                self_a_ok, failed_a = self.check_assumptions(state)
                if not self_a_ok:
                    return False, f"Counterexample: Spec assumption holds but self assumption failed on: {failed_a}"

            # 2. Self guarantee implies spec guarantee
            self_g_ok, _ = self.check_guarantees(state)
            if self_g_ok:
                spec_g_ok, failed_g = abstract_spec.check_guarantees(state)
                if not spec_g_ok:
                    return False, f"Counterexample: Self guarantee holds but spec guarantee failed on: {failed_g}"

        return True, None


class ContractCompositionEngine:
    """Composes multiple agent contracts into a system-level contract."""

    @staticmethod
    def check_compatibility(
        agent1_contract: AssumeGuaranteeContract,
        agent2_contract: AssumeGuaranteeContract,
        interaction_state: dict[str, Any]
    ) -> tuple[bool, list[str]]:
        """Verify whether agent1 and agent2 can safely compose.

        Compatibility requires:
        - Output guarantees of Agent 1 satisfy the input assumptions of Agent 2 on shared interfaces.
        """
        issues = []
        # Agent 1 guarantees vs Agent 2 assumptions
        for p in agent2_contract.assumptions:
            if not p.evaluate(interaction_state):
                issues.append(f"Agent 2 assumption '{p.name}' not satisfied by Agent 1 output state")

        return len(issues) == 0, issues

    @staticmethod
    def compose(
        contract_a: AssumeGuaranteeContract,
        contract_b: AssumeGuaranteeContract,
        composite_name: str
    ) -> AssumeGuaranteeContract:
        """Compute parallel composition C_comp = C_a (x) C_b."""
        # Composite assumptions: union of assumptions
        seen_a: set[str] = set()
        comp_a: list[ContractPredicate] = []
        for p in contract_a.assumptions + contract_b.assumptions:
            if p.name not in seen_a:
                seen_a.add(p.name)
                comp_a.append(p)

        # Composite guarantees: union of guarantees
        seen_g: set[str] = set()
        comp_g: list[ContractPredicate] = []
        for p in contract_a.guarantees + contract_b.guarantees:
            if p.name not in seen_g:
                seen_g.add(p.name)
                comp_g.append(p)

        return AssumeGuaranteeContract(
            name=composite_name,
            assumptions=comp_a,
            guarantees=comp_g,
            metadata={"composition": [contract_a.name, contract_b.name]}
        )


class ContractRegistry:
    """Thread-safe in-memory registry for Assume-Guarantee contracts."""

    _contracts: dict[str, AssumeGuaranteeContract] = {}

    @classmethod
    def register(cls, target_name: str, contract: AssumeGuaranteeContract) -> None:
        """Register a formal contract for a skill, agent, or operation type."""
        cls._contracts[target_name] = contract
        logger.debug("Registered contract '%s' for target '%s'", contract.name, target_name)

    @classmethod
    def get(cls, target_name: str) -> AssumeGuaranteeContract | None:
        """Retrieve the registered contract for a target, if any."""
        return cls._contracts.get(target_name)

    @classmethod
    def has(cls, target_name: str) -> bool:
        """Check if a contract exists for the target."""
        return target_name in cls._contracts

    @classmethod
    def clear(cls) -> None:
        """Clear all registered contracts."""
        cls._contracts.clear()

    @classmethod
    def all_contracts(cls) -> dict[str, AssumeGuaranteeContract]:
        """Return a copy of all registered contracts."""
        return dict(cls._contracts)


def make_standard_task_contract(name: str) -> AssumeGuaranteeContract:
    """Creates a standard baseline Assume-Guarantee contract for compound tasks.

    Assumptions:
    - valid_task_description: Non-empty string with at least 3 characters.
    - valid_operation_type: Defined operation type.

    Guarantees:
    - non_empty_output: Output is non-empty string.
    - non_degraded_execution: Execution metrics do not indicate degradation.
    """
    return AssumeGuaranteeContract(
        name=name,
        assumptions=[
            ContractPredicate(
                name="valid_task_description",
                description="Task description must be a non-empty string with len >= 3",
                predicate=lambda state: isinstance(state.get("task_description"), str)
                and len(state.get("task_description", "").strip()) >= 3,
            ),
            ContractPredicate(
                name="valid_operation_type",
                description="Operation type must be defined",
                predicate=lambda state: bool(state.get("operation_type")),
            ),
        ],
        guarantees=[
            ContractPredicate(
                name="non_empty_output",
                description="Execution output must be non-empty",
                predicate=lambda state: bool(str(state.get("output", "")).strip()),
            ),
            ContractPredicate(
                name="non_degraded_execution",
                description="Execution must not be marked degraded",
                predicate=lambda state: not state.get("metrics", {}).get("degraded", False),
            ),
        ],
    )

