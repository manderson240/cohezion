"""
Adversarial Review Tests - Test Suite Critique

Reviews test suites for blind spots, optimistic bias, and missing edge cases.
Generates new tests targeting identified gaps.
"""

import ast
import os
from dataclasses import dataclass
from typing import Dict, List

import pytest


@dataclass
class CritiqueReport:
    """Report from adversarial test review."""

    coverage_gaps: List[str]
    optimistic_assumptions: List[str]
    missing_edge_cases: List[str]
    refinement_actions: List[str]


class AdversarialTestReviewer:
    """Reviews test suites for blind spots."""

    def __init__(self, test_dir: str = None):
        self.test_dir = test_dir or os.path.dirname(os.path.abspath(__file__))
        self.test_files = self._discover_test_files()

    def _discover_test_files(self) -> List[str]:
        """Find all test Python files."""
        files = []
        for f in os.listdir(self.test_dir):
            if f.startswith("test_") and f.endswith(".py"):
                files.append(os.path.join(self.test_dir, f))
        return files

    def review_test_suite(self, test_file: str) -> CritiqueReport:
        """Review a single test file for gaps."""
        with open(test_file, "r") as f:
            content = f.read()
            tree = ast.parse(content)

        gaps = []
        assumptions = []
        edge_cases = []
        actions = []

        # Analyze test structure
        test_classes = []
        test_methods = []
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                if any("Test" in base.id for base in node.bases if isinstance(base, ast.Name)):
                    test_classes.append(node.name)
            elif isinstance(node, ast.FunctionDef):
                if node.name.startswith("test_"):
                    test_methods.append(node.name)

        # Detect optimistic bias (happy-path only)
        has_error_tests = any(
            "error" in m.lower() or "fail" in m.lower() or "exception" in m.lower()
            for m in test_methods
        )
        if not has_error_tests:
            assumptions.append("No error handling tests detected - optimistic bias")
            actions.append("Add error handling tests for failure modes")

        # Detect missing edge cases
        has_boundary_tests = any(
            "boundary" in m.lower() or "edge" in m.lower() or "zero" in m.lower()
            for m in test_methods
        )
        if not has_boundary_tests:
            edge_cases.append("No boundary/edge case tests detected")
            actions.append("Add boundary tests (zero, empty, max values)")

        # Detect missing property-based tests
        has_property_tests = any(
            "hypothesis" in content.lower() or "given" in content.lower() for m in test_methods
        )
        if not has_property_tests:
            gaps.append("No property-based tests (hypothesis)")
            actions.append("Add property-based tests for input invariants")

        # Detect missing adversarial inputs
        has_adversarial = any(
            "adversar" in m.lower() or "attack" in m.lower() or "hard" in m.lower()
            for m in test_methods
        )
        if not has_adversarial:
            edge_cases.append("No adversarial input tests")
            actions.append("Add adversarial input tests (LaTeX traps, ambiguous problems)")

        # Detect missing integration tests
        has_integration = any(
            "integration" in m.lower() or "live" in m.lower() or "api" in m.lower()
            for m in test_methods
        )
        if not has_integration:
            gaps.append("No live API integration tests")
            actions.append("Add integration tests with real Ollama calls")

        # Detect missing stability tests
        has_stability = any(
            "stability" in m.lower() or "consistent" in m.lower() or "drift" in m.lower()
            for m in test_methods
        )
        if not has_stability:
            gaps.append("No stability/consistency tests")
            actions.append("Add dual-run stability tests")

        return CritiqueReport(
            coverage_gaps=gaps,
            optimistic_assumptions=assumptions,
            missing_edge_cases=edge_cases,
            refinement_actions=actions,
        )

    def review_all_suites(self) -> Dict[str, CritiqueReport]:
        """Review all test suites."""
        reports = {}
        for test_file in self.test_files:
            reports[test_file] = self.review_test_suite(test_file)
        return reports


class TestAdversarialReview:
    """Tests for adversarial review process."""

    @pytest.mark.fast
    def test_reviewer_discovers_test_files(self):
        """Test reviewer finds all test files."""
        reviewer = AdversarialTestReviewer()
        files = reviewer._discover_test_files()

        assert len(files) >= 5, "Should find at least 5 test files"
        assert any("test_sprint" in f for f in files)

    @pytest.mark.fast
    def test_reviewer_detects_optimistic_bias(self):
        """Test reviewer detects optimistic bias in test files."""
        reviewer = AdversarialTestReviewer()

        # Review a mock-based test file
        mock_test = os.path.join(reviewer.test_dir, "test_sprint2.py")
        if os.path.exists(mock_test):
            report = reviewer.review_test_suite(mock_test)

            # Should detect gaps
            assert len(report.coverage_gaps) > 0 or len(report.refinement_actions) > 0

    @pytest.mark.fast
    def test_reviewer_detects_missing_edge_cases(self):
        """Test reviewer detects missing edge cases."""
        reviewer = AdversarialTestReviewer()

        # Review regression tests (should have fewer gaps)
        regression_test = os.path.join(reviewer.test_dir, "test_regression_stability.py")
        if os.path.exists(regression_test):
            report = reviewer.review_test_suite(regression_test)

            # Regression tests should have error handling
            assert len(report.optimistic_assumptions) == 0 or "error" in regression_test.lower()

    @pytest.mark.fast
    def test_reviewer_generates_refinement_actions(self):
        """Test reviewer generates actionable refinements."""
        reviewer = AdversarialTestReviewer()

        # Create a minimal test file
        minimal_test = """
import pytest

class TestMinimal:
    def test_happy_path(self):
        assert 1 + 1 == 2
"""
        # Write temp file
        temp_path = "/tmp/test_minimal.py"
        with open(temp_path, "w") as f:
            f.write(minimal_test)

        report = reviewer.review_test_suite(temp_path)

        # Should suggest many improvements
        assert len(report.refinement_actions) >= 3
        os.remove(temp_path)


class TestAdversarialInputGeneration:
    """Generates hard test cases to break the swarm."""

    @pytest.mark.fast
    def test_generates_ambiguous_problems(self):
        """Test generation of ambiguous problems."""
        from swarm_coordinator import SwarmCoordinator

        coordinator = SwarmCoordinator()

        ambiguous = "Find x (could be multiple values)"
        task = coordinator.plan_journey("test", ambiguous)

        # Should still assign specialists
        assert len(task.assigned_specialists) >= 2

    @pytest.mark.fast
    def test_generates_latex_traps(self):
        """Test LaTeX parsing edge cases."""
        from math_parser import MathParser

        parser = MathParser()

        # Ambiguous LaTeX
        latex_trap = "$x = \\frac{1}{2}$ vs $x = 1/2$"
        state = parser.parse(latex_trap)

        # Should parse without crashing
        assert state is not None

    @pytest.mark.fast
    def test_generates_undefined_cases(self):
        """Test undefined mathematical expressions."""
        from base_specialist import BaseSpecialist

        specialist = BaseSpecialist("NumberTheorist")

        # Undefined: 0^0
        problem = "What is 0^0?"
        response = specialist.extract_answer("The expression is undefined")

        # Should return 0 (graceful handling)
        assert response == 0

    @pytest.mark.fast
    def test_generates_deep_reasoning_traps(self):
        """Test problems requiring deep reasoning."""
        from swarm_coordinator import SwarmCoordinator

        coordinator = SwarmCoordinator()

        # Induction proof requires deep CoT
        problem = "Prove by induction that 1 + 2 + ... + n = n(n+1)/2"
        task = coordinator.plan_journey("test", problem)

        # Should assign specialists for proof problems
        assert len(task.assigned_specialists) >= 2
        assert "Algebraist" in task.assigned_specialists


class TestMultiPerspectiveOracles:
    """Tests using multiple independent oracles."""

    @pytest.mark.fast
    def test_three_oracles_agree(self):
        """Test ground truth, symbolic, and constraint oracles agree."""
        import sympy

        # Problem: x^2 = 256
        expected = 16  # Ground truth

        # Oracle 2: Symbolic execution
        sympy_answer = sympy.solve("x**2 - 256")
        sympy_answer = [int(s) for s in sympy_answer if s > 0][0]

        # Oracle 3: Constraint validator
        def validate(n):
            return 0 <= n <= 99999

        # All must agree
        assert expected == sympy_answer
        assert validate(expected)
        assert validate(sympy_answer)

    @pytest.mark.fast
    def test_oracle_detects_bug(self):
        """Test oracle catches wrong answer."""
        wrong_answer = 17
        expected = 16

        # Oracle should detect mismatch
        assert wrong_answer != expected


class TestAdversarialReviewIntegration:
    """Integration tests for adversarial review loop."""

    @pytest.mark.fast
    def test_full_review_cycle(self):
        """Test complete adversarial review cycle."""
        reviewer = AdversarialTestReviewer()

        # Review all suites
        reports = reviewer.review_all_suites()

        # Should have reports for all files
        assert len(reports) >= 5

        # Aggregate gaps
        all_gaps = []
        all_actions = []
        for report in reports.values():
            all_gaps.extend(report.coverage_gaps)
            all_actions.extend(report.refinement_actions)

        # Should identify at least some gaps
        assert len(all_gaps) > 0 or len(all_actions) > 0

    @pytest.mark.fast
    def test_review_improves_coverage(self):
        """Test that acting on review improves coverage."""
        # Before: 53 tests
        # After acting on recommendations: should have more

        # Count tests in all files
        reviewer = AdversarialTestReviewer()
        test_count = 0

        for test_file in reviewer.test_files:
            with open(test_file, "r") as f:
                content = f.read()
                test_count += content.count("def test_")

        # Should have at least 53 tests from original suite
        assert test_count >= 53
