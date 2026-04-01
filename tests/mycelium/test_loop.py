from unittest.mock import AsyncMock, patch

import pytest

from cohezion.mycelium.loop import CoverageLoop


@pytest.fixture
def mock_scripter():
    mock = AsyncMock()
    return mock

@pytest.fixture
def loop(mock_scripter):
    return CoverageLoop(scripter=mock_scripter)

@pytest.mark.asyncio
async def test_run_tests_and_get_coverage(loop):
    """Test running tests and parsing coverage output."""
    with patch("subprocess.check_output") as mock_run:
        # Mocking pytest output with coverage
        mock_run.return_value = b"""
---------- coverage: platform linux, python 3.13.11-final-0 ----------
Name                                Stmts   Miss  Cover
-------------------------------------------------------
src/cohezion/dummy.py                  10      2    80%
-------------------------------------------------------
TOTAL                                  10      2    80%
"""
        coverage = loop.run_tests_and_get_coverage(file_path="src/cohezion/dummy.py")
        assert coverage == 80.0

@pytest.mark.asyncio
async def test_execute_loop_achieves_target(loop, mock_scripter):
    """Test the iterative loop logic."""
    # First run returns 80%, second run returns 100%
    with patch.object(loop, "run_tests_and_get_coverage") as mock_coverage:
        mock_coverage.side_effect = [80.0, 100.0]
        mock_scripter.synthesize_test_suite.return_value = "def test_more(): pass"
        
        final_coverage = await loop.execute(
            file_path="src/cohezion/dummy.py",
            code_context="code",
            target_coverage=100.0,
            max_iterations=2
        )
        
        assert final_coverage == 100.0
        assert mock_scripter.synthesize_test_suite.call_count == 1
        assert mock_coverage.call_count == 2
