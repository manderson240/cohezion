import logging
import os
import re
import shutil
import subprocess

from cohezion.mycelium.scripter import ShadowScripter


logger = logging.getLogger(__name__)

# Resolve uv executable at module load to avoid S607 partial-path warnings.
_UV = shutil.which("uv") or "/usr/local/bin/uv"


class CoverageLoop:
    """
    Orchestrates the iterative test generation and verification loop.
    """

    def __init__(
        self, scripter: ShadowScripter, root_dir: str = ".", test_output_dir: str = "tests/mycelium"
    ):
        self.scripter = scripter
        self.root_dir = root_dir
        self.test_output_dir = test_output_dir

    def run_tests_and_get_coverage(self, file_path: str) -> float:
        """
        Runs pytest with coverage for a specific file and parses the percentage.
        """
        try:
            # We assume tests for src/cohezion/x.py are in tests/
            # For simplicity in the loop, we run all tests but report on the specific file
            output = subprocess.check_output(  # noqa: S603 - file_path comes from internal coverage loop config
                [_UV, "run", "pytest", "--cov=" + file_path],
                cwd=self.root_dir,
                stderr=subprocess.STDOUT,
            ).decode("utf-8")

            # Use regex to find the coverage percentage for the file
            # Example line: src/cohezion/dummy.py                  10      2    80%
            pattern = rf"{re.escape(file_path)}\s+\d+\s+\d+\s+(\d+)%"
            match = re.search(pattern, output)

            if match:
                return float(match.group(1))

            logger.warning(f"Could not find coverage percentage for {file_path} in output.")
            return 0.0

        except subprocess.CalledProcessError as e:
            error_msg = e.output.decode("utf-8")
            logger.error(f"Test run failed for {file_path}: {error_msg}")
            # Returning 0.0 allows the loop to continue and potentially 'fix' the test
            return 0.0

    async def execute(
        self,
        file_path: str,
        code_context: str,
        target_coverage: float = 100.0,
        max_iterations: int = 3,
    ) -> float:
        """
        Executes the iterative synthesis loop.
        """
        current_coverage = self.run_tests_and_get_coverage(file_path)
        iteration = 0

        while current_coverage < target_coverage and iteration < max_iterations:
            logger.info(
                f"Current coverage for {file_path}: {current_coverage}%. Target: {target_coverage}%"
            )

            # Synthesize more tests
            test_code = await self.scripter.synthesize_test_suite(file_path, code_context)

            # Write synthesized tests to a file
            test_filename = f"generated_test_{os.path.basename(file_path)}"
            test_file = os.path.join(self.test_output_dir, test_filename)
            os.makedirs(self.test_output_dir, exist_ok=True)

            with open(test_file, "w") as f:
                f.write(test_code)

            current_coverage = self.run_tests_and_get_coverage(file_path)
            iteration += 1

        return current_coverage
