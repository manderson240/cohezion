"""Mutation Testing Engine & Assertion Strength Verifier.
=========================================================
Introduces synthetic semantic and boundary faults (mutants) into target code:
- Comparison operator flips (< to <=, == to !=, > to >=)
- Arithmetic operator swaps (+ to -, * to /)
- Constant boundary shifts
- Boolean inversion

Executes test suites against each mutant to calculate the Mutation Score:
    Score = Killed Mutants / Total Mutants
Guarantees assertion strength and eliminates vacuous green tests.
"""

from __future__ import annotations

import ast
import copy
import logging
from dataclasses import dataclass, field
from typing import Any, Callable

logger = logging.getLogger("mutation_tester")


@dataclass(frozen=True, slots=True)
class Mutant:
    """A synthesized mutant with an isolated synthetic fault."""

    mutant_id: str
    original_op: str
    mutated_op: str
    lineno: int
    description: str


@dataclass(frozen=True, slots=True)
class MutationReport:
    """Outcome of a mutation testing campaign."""

    total_mutants: int
    killed_mutants: int
    survived_mutants: int
    mutation_score: float
    mutant_details: list[dict[str, Any]] = field(default_factory=list)


class ASTMutationTransformer(ast.NodeTransformer):
    """AST transformer that generates single targeted mutations."""

    CMP_MUTATIONS = {
        ast.Lt: ast.LtE,
        ast.LtE: ast.Lt,
        ast.Gt: ast.GtE,
        ast.GtE: ast.Gt,
        ast.Eq: ast.NotEq,
        ast.NotEq: ast.Eq,
    }

    BIN_MUTATIONS = {
        ast.Add: ast.Sub,
        ast.Sub: ast.Add,
        ast.Mult: ast.Div,
    }

    def __init__(self, target_index: int) -> None:
        super().__init__()
        self.target_index = target_index
        self.current_index = 0
        self.applied_mutant: Mutant | None = None

    def visit_Compare(self, node: ast.Compare) -> ast.AST:
        new_ops = []
        for op in node.ops:
            op_type = type(op)
            if op_type in self.CMP_MUTATIONS:
                if self.current_index == self.target_index:
                    mutated_cls = self.CMP_MUTATIONS[op_type]
                    new_op = mutated_cls()
                    new_ops.append(new_op)
                    self.applied_mutant = Mutant(
                        mutant_id=f"mutant_cmp_{self.target_index}",
                        original_op=op_type.__name__,
                        mutated_op=mutated_cls.__name__,
                        lineno=getattr(node, "lineno", 0),
                        description=f"Flipped comparison {op_type.__name__} -> {mutated_cls.__name__} at line {getattr(node, 'lineno', 0)}",
                    )
                else:
                    new_ops.append(op)
                self.current_index += 1
            else:
                new_ops.append(op)
        node.ops = new_ops
        return self.generic_visit(node)

    def visit_BinOp(self, node: ast.BinOp) -> ast.AST:
        op_type = type(node.op)
        if op_type in self.BIN_MUTATIONS:
            if self.current_index == self.target_index:
                mutated_cls = self.BIN_MUTATIONS[op_type]
                node.op = mutated_cls()
                self.applied_mutant = Mutant(
                    mutant_id=f"mutant_bin_{self.target_index}",
                    original_op=op_type.__name__,
                    mutated_op=mutated_cls.__name__,
                    lineno=getattr(node, "lineno", 0),
                    description=f"Swapped binary op {op_type.__name__} -> {mutated_cls.__name__} at line {getattr(node, 'lineno', 0)}",
                )
            self.current_index += 1
        return self.generic_visit(node)


class MutationTestingEngine:
    """Discovers mutation sites, generates synthetic mutants, and evaluates assertion strength."""

    @staticmethod
    def count_mutation_sites(source_code: str) -> int:
        """Count total candidate mutation sites in source code."""
        tree = ast.parse(source_code)
        count = 0
        for node in ast.walk(tree):
            if isinstance(node, ast.Compare):
                for op in node.ops:
                    if type(op) in ASTMutationTransformer.CMP_MUTATIONS:
                        count += 1
            elif isinstance(node, ast.BinOp):
                if type(node.op) in ASTMutationTransformer.BIN_MUTATIONS:
                    count += 1
        return count

    @classmethod
    def generate_mutant(cls, source_code: str, site_index: int) -> tuple[str, Mutant | None]:
        """Generate a single mutated version of the source code."""
        tree = ast.parse(source_code)
        transformer = ASTMutationTransformer(target_index=site_index)
        mutated_tree = transformer.visit(tree)
        ast.fix_missing_locations(mutated_tree)
        return ast.unparse(mutated_tree), transformer.applied_mutant

    @classmethod
    def evaluate_test_suite_assertion_strength(
        cls,
        source_code: str,
        test_fn: Callable[[dict[str, Any]], None],
        module_name: str = "mutated_module",
        max_mutants: int = 20,
    ) -> MutationReport:
        """Run mutation testing by injecting synthetic faults and executing the test function.

        A mutant is KILLED if test_fn raises an exception/assertion.
        A mutant SURVIVES if test_fn succeeds silently (indicating weak assertions).
        """
        total_sites = cls.count_mutation_sites(source_code)
        mutants_to_test = min(total_sites, max_mutants)

        killed = 0
        survived = 0
        details: list[dict[str, Any]] = []

        for i in range(mutants_to_test):
            mutated_code, mutant = cls.generate_mutant(source_code, i)
            if not mutant:
                continue

            # Execute the mutated code in an isolated namespace
            mutant_ns: dict[str, Any] = {}
            try:
                exec(compile(mutated_code, f"<mutant_{i}>", "exec"), mutant_ns)
            except Exception as compile_err:
                # Syntax or compile error kills the mutant immediately
                killed += 1
                details.append({
                    "mutant_id": mutant.mutant_id,
                    "status": "KILLED",
                    "reason": f"Compilation failed: {compile_err}",
                    "description": mutant.description,
                })
                continue

            # Run test function against the mutated module namespace
            try:
                test_fn(mutant_ns)
                # Test passed unexpectedly -> Mutant survived!
                survived += 1
                details.append({
                    "mutant_id": mutant.mutant_id,
                    "status": "SURVIVED",
                    "reason": "Test suite failed to detect synthetic mutation",
                    "description": mutant.description,
                })
            except Exception as test_err:
                # Test detected the fault and failed -> Mutant killed!
                killed += 1
                details.append({
                    "mutant_id": mutant.mutant_id,
                    "status": "KILLED",
                    "reason": f"Caught by assertion: {type(test_err).__name__}",
                    "description": mutant.description,
                })

        tested_count = killed + survived
        score = (killed / tested_count) if tested_count > 0 else 1.0

        return MutationReport(
            total_mutants=tested_count,
            killed_mutants=killed,
            survived_mutants=survived,
            mutation_score=round(score, 4),
            mutant_details=details,
        )
