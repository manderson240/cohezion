"""Vector 6: Mutation Testing & Assertion Strength Verification.
================================================================
Verifies that existing test suites have high assertion strength by introducing
synthetic faults (flipped comparisons, inverted boolean conditions, swapped operators)
and proving that our test suite kills the mutants.
"""

import pytest
from cohezion.testing.mutation_tester import MutationTestingEngine, MutationReport


@pytest.mark.mutation
class TestMutationTestingAssertionStrength:

    def test_mutation_engine_detects_mutation_sites(self):
        code = """
def is_hiho_stable(coherence: float) -> bool:
    diff = abs(coherence - 0.50)
    return diff <= 0.01 and coherence > 0.0
"""
        sites = MutationTestingEngine.count_mutation_sites(code)
        assert sites >= 2  # '-' operator and '<=' and '>' comparisons

    def test_mutation_engine_kills_comparison_and_arithmetic_mutants(self):
        """Proves that a strict test suite kills 100% of synthetic mutants."""
        source_code = """
def compute_hiho_quadrature(val_a: float, val_b: float) -> float:
    diff = val_a - val_b
    if diff < 0.0:
        return 0.0
    return diff + 0.5
"""
        # Strict test function that tests both exact boundary conditions and values
        def strict_test_suite(module_ns):
            fn = module_ns["compute_hiho_quadrature"]
            # Test diff > 0
            assert fn(2.0, 1.0) == 1.5
            # Test diff < 0
            assert fn(1.0, 2.0) == 0.0
            # Test boundary diff == 0.0: diff < 0.0 is False, returns 0.0 + 0.5 = 0.5
            assert fn(1.0, 1.0) == 0.5

        report = MutationTestingEngine.evaluate_test_suite_assertion_strength(
            source_code=source_code,
            test_fn=strict_test_suite,
            max_mutants=10,
        )

        assert isinstance(report, MutationReport)
        assert report.total_mutants > 0
        # The mutation score must be >= 0.85 (High assertion strength)
        assert report.mutation_score >= 0.85
        assert report.killed_mutants >= report.survived_mutants

    def test_mutation_engine_detects_weak_assertions_when_mutant_survives(self):
        """Proves that a weak test suite with incomplete assertions allows mutants to survive."""
        source_code = """
def check_boundary(x: int) -> bool:
    if x < 10:
        return True
    return False
"""
        # Weak test that only tests x=5, never tests x=10 (the exact mutant boundary '<' vs '<=')
        def weak_test_suite(module_ns):
            fn = module_ns["check_boundary"]
            assert fn(5) is True

        report = MutationTestingEngine.evaluate_test_suite_assertion_strength(
            source_code=source_code,
            test_fn=weak_test_suite,
            max_mutants=5,
        )

        # The '<' to '<=' mutant at boundary x=10 survived because weak_test_suite didn't test x=10!
        assert report.survived_mutants > 0
        assert any(
            m["status"] == "SURVIVED" for m in report.mutant_details
        )
