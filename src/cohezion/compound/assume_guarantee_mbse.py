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

from dataclasses import dataclass, field
import inspect
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("assume_guarantee_mbse")


@dataclass(frozen=True)
class ContractPredicate:
    """A deterministic predicate over a state dictionary."""
    name: str
    description: str
    predicate: Callable[[Dict[str, Any]], bool]

    def evaluate(self, state: Dict[str, Any]) -> bool:
        try:
            return bool(self.predicate(state))
        except Exception as exc:
            logger.debug("Predicate '%s' raised exception: %s", self.name, exc)
            return False


@dataclass
class AssumeGuaranteeContract:
    """Formal Assume-Guarantee Contract C = <A, G>."""
    name: str
    assumptions: List[ContractPredicate] = field(default_factory=list)
    guarantees: List[ContractPredicate] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def check_assumptions(self, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Verify whether the environment state satisfies all contract assumptions."""
        failures = [p.name for p in self.assumptions if not p.evaluate(state)]
        return len(failures) == 0, failures

    def check_guarantees(self, state: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Verify whether the agent/subsystem state satisfies all contract guarantees."""
        failures = [p.name for p in self.guarantees if not p.evaluate(state)]
        return len(failures) == 0, failures

    def evaluate_step(self, pre_state: Dict[str, Any], post_state: Dict[str, Any]) -> Tuple[bool, str]:
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

    def refines(self, abstract_spec: AssumeGuaranteeContract, test_samples: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, Optional[str]]:
        """Check if self refines abstract_spec (self <= abstract_spec).
        
        Refinement Condition:
        1. Weaker or equal assumptions: abstract_spec.A => self.A
           (Every sample satisfying abstract_spec.A must also satisfy self.A).
        2. Stronger or equal guarantees: self.G => abstract_spec.G
           (Every sample satisfying self.G must also satisfy abstract_spec.G).
        """
        if not test_samples:
            # Static check by predicate name containment if no state space provided
            self_a_names = {p.name for p in self.assumptions}
            spec_a_names = {p.name for p in abstract_spec.assumptions}
            self_g_names = {p.name for p in self.guarantees}
            spec_g_names = {p.name for p in abstract_spec.guarantees}

            # Implementation should guarantee at least what spec guarantees
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
        interaction_state: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
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
        seen_a: Set[str] = set()
        comp_a: List[ContractPredicate] = []
        for p in contract_a.assumptions + contract_b.assumptions:
            if p.name not in seen_a:
                seen_a.add(p.name)
                comp_a.append(p)

        # Composite guarantees: union of guarantees
        seen_g: Set[str] = set()
        comp_g: List[ContractPredicate] = []
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
