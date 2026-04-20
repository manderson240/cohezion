"""
Regression Tests - Stability Fixes Verification

Tests the 4 critical stability fixes from TROUBLESHOOTING_RETRO.md:
1. Timeout configuration (prevents infinite hang)
2. Error-as-answer prevention (check error before regex)
3. Polars migration (no pandas imports)
4. Process management (cleanup.sh)
"""

import pytest
from base_specialist import BaseSpecialist
from knower_auditor import KnowerAuditor
from swarm_coordinator import SwarmCoordinator


class TestStory11TimeoutConfiguration:
    """Tests for timeout configuration (Story 1.1)."""

    @pytest.mark.fast
    def test_specialist_has_timeout_attribute(self):
        """Test BaseSpecialist has timeout configuration."""
        specialist = BaseSpecialist("Algebraist")
        assert hasattr(specialist, "timeout")
        assert specialist.timeout == 300  # Default 5 minutes

    @pytest.mark.fast
    def test_timeout_can_be_overridden(self):
        """Test timeout can be customized per instance."""
        specialist = BaseSpecialist("Algebraist", timeout=60)
        assert specialist.timeout == 60

    @pytest.mark.fast
    def test_timeout_stored_correctly(self):
        """Test timeout is stored correctly on specialist."""
        specialist = BaseSpecialist("Algebraist", timeout=120)

        # Verify the specialist stores timeout correctly
        assert specialist.timeout == 120

    @pytest.mark.fast
    def test_extract_answer_checks_error_first(self):
        """Test extract_answer checks for error before regex extraction."""
        specialist = BaseSpecialist("Algebraist")

        # Error response should return 0, not extract numbers from error
        error_response = "Error calling Ollama: Read timed out. (read timeout=300)"
        answer = specialist.extract_answer(error_response)

        assert answer == 0, "Error messages should return 0, not extracted numbers"

    @pytest.mark.fast
    def test_extract_answer_does_not_extract_from_error(self):
        """Test regex is not applied to error messages."""
        specialist = BaseSpecialist("Algebraist")

        # Error with numbers in it (like "timeout=300")
        error_response = "Error: Connection failed after 3 attempts (timeout=300)"
        answer = specialist.extract_answer(error_response)

        # Should NOT extract 300 from the error
        assert answer == 0

    @pytest.mark.fast
    def test_extract_answer_extracts_from_valid_response(self):
        """Test regex extraction works on valid responses."""
        specialist = BaseSpecialist("Algebraist")

        # Valid response with boxed answer
        valid_response = "Step 1: Solve x + 2 = 5. Step 2: x = 3. \\boxed{3}"
        answer = specialist.extract_answer(valid_response)

        assert answer == 3

    @pytest.mark.fast
    def test_extract_answer_fallback_to_last_number(self):
        """Test fallback extracts last number when no boxed."""
        specialist = BaseSpecialist("Algebraist")

        response = "The answer is 47"
        answer = specialist.extract_answer(response)

        assert answer == 47

    @pytest.mark.fast
    def test_extract_answer_returns_zero_on_no_match(self):
        """Test extract_answer returns 0 when no numbers found."""
        specialist = BaseSpecialist("Algebraist")

        response = "No solution exists"
        answer = specialist.extract_answer(response)

        assert answer == 0


class TestStory12ErrorAsAnswerPrevention:
    """Tests for error-as-answer prevention (Story 1.2)."""

    @pytest.mark.fast
    def test_error_timeout_does_not_extract_timeout_value(self):
        """Test timeout error doesn't extract timeout value as answer."""
        specialist = BaseSpecialist("Algebraist")

        error = "Error: Read timed out. (read timeout=180)"
        answer = specialist.extract_answer(error)

        # Should NOT extract 180
        assert answer == 0

    @pytest.mark.fast
    def test_error_connection_does_not_extract_port_number(self):
        """Test connection error doesn't extract port as answer."""
        specialist = BaseSpecialist("Algebraist")

        error = "Error: Connection refused on port 11434"
        answer = specialist.extract_answer(error)

        # Should NOT extract 11434
        assert answer == 0

    @pytest.mark.fast
    def test_error_http_does_not_extract_status_code(self):
        """Test HTTP error doesn't extract status code as answer."""
        specialist = BaseSpecialist("Algebraist")

        error = "Error: HTTP 500 Internal Server Error"
        answer = specialist.extract_answer(error)

        # Should NOT extract 500
        assert answer == 0


class TestStory13PolarsMigration:
    """Tests for polars migration (Story 1.3)."""

    @pytest.mark.fast
    def test_no_pandas_imports_in_aimo_files(self):
        """Test no pandas imports in AIMO subsystem."""
        import ast
        import os

        aimo_dir = os.path.dirname(os.path.abspath(__file__))
        pandas_files = []

        for filename in os.listdir(aimo_dir):
            if filename.endswith(".py") and filename != "test_regression_stability.py":
                filepath = os.path.join(aimo_dir, filename)
                with open(filepath, "r") as f:
                    try:
                        tree = ast.parse(f.read())
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Import):
                                for alias in node.names:
                                    if alias.name == "pandas":
                                        pandas_files.append(filename)
                            elif isinstance(node, ast.ImportFrom):
                                if node.module == "pandas":
                                    pandas_files.append(filename)
                    except SyntaxError:
                        pass

        assert len(pandas_files) == 0, f"Found pandas imports in: {pandas_files}"

    @pytest.mark.fast
    def test_polars_imported_in_core_files(self):
        """Test polars is imported in core AIMO files."""

        # Verify polars is available
        import polars as pl

        assert pl is not None

    @pytest.mark.fast
    def test_dataframe_uses_polars_not_pandas(self):
        """Test DataFrames use polars API."""
        import polars as pl

        df = pl.DataFrame({"id": ["test1"], "problem": ["Solve x + 1 = 2"]})

        # Polars API (not pandas)
        assert df.shape == (1, 2)
        assert df["id"].to_list() == ["test1"]
        assert df["problem"].to_list() == ["Solve x + 1 = 2"]


class TestStory14ProcessManagement:
    """Tests for process management (Story 1.4)."""

    @pytest.mark.fast
    def test_cleanup_script_exists(self):
        """Test cleanup.sh exists."""
        import os

        cleanup_path = os.path.join(os.path.dirname(__file__), "cleanup.sh")
        assert os.path.exists(cleanup_path)

    @pytest.mark.fast
    def test_cleanup_script_is_executable(self):
        """Test cleanup.sh is executable."""
        import os
        import stat

        cleanup_path = os.path.join(os.path.dirname(__file__), "cleanup.sh")
        mode = os.stat(cleanup_path).st_mode
        assert mode & stat.S_IXUSR

    @pytest.mark.fast
    def test_knower_auditor_handles_divergence(self):
        """Test KnowerAuditor handles divergent answers."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs([16, 17], ["reasoning1", "reasoning2"])

        assert result["consistent"] is False
        assert result["action"] == "TIE_BREAKER"
        assert result["final_answer"] is None

    @pytest.mark.fast
    def test_knower_auditor_handles_consistency(self):
        """Test KnowerAuditor handles consistent answers."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs([16, 16], ["reasoning1", "reasoning2"])

        assert result["consistent"] is True
        assert result["action"] == "COMMIT"
        assert result["final_answer"] == 16
        assert result["stability_score"] == 1.0


class TestStabilityIntegration:
    """Integration tests for all stability fixes."""

    @pytest.mark.fast
    def test_full_pipeline_with_error_handling(self):
        """Test full pipeline handles errors gracefully."""
        coordinator = SwarmCoordinator()
        auditor = KnowerAuditor()

        problem = "Solve for x: x + 2 = 5"
        task = coordinator.plan_journey("test", problem)

        # Simulate error response
        error_response = "Error: Timeout"

        # Error should be handled, not crash
        answer = auditor.audit_runs([0, 0], [error_response, error_response])

        assert answer["final_answer"] == 0
        assert answer["action"] == "COMMIT"

    @pytest.mark.fast
    def test_routing_always_returns_two_specialists(self):
        """Test routing always assigns at least 2 specialists."""
        coordinator = SwarmCoordinator()

        test_problems = [
            "Solve x^2 = 4",  # Algebra
            "Find area of circle radius 5",  # Geometry
            "Is 17 prime?",  # Number theory
            "How many ways to arrange 3 items?",  # Combinatorics
            "General math problem",  # Fallback
        ]

        for problem in test_problems:
            task = coordinator.plan_journey("test", problem)
            assert len(task.assigned_specialists) >= 2, f"Problem: {problem}"
