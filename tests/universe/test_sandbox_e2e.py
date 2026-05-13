"""End-to-end integration tests for sandbox simulation pipeline.

Uses SubprocessBackend (always available, no Docker needed) to validate
script execution, output file collection, and result persistence.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from cohezion.universe.example_simulations import (
    COHERENCE_WALK,
    EXAMPLES,
    HELLO_SANDBOX,
)
from cohezion.universe.sandbox_backends import SubprocessBackend
from cohezion.universe.sandbox_profiles import SandboxProfile
from cohezion.universe.sandbox_results import persist_result


# Use a lenient profile for tests — high memory limit avoids RLIMIT_AS failures
# on systems where Python's own footprint is large.
TEST_PROFILE = SandboxProfile(
    memory_limit_mb=2048,
    cpu_quota_percent=100,
    timeout_seconds=30,
    network_enabled=False,
    gpu_passthrough=False,
)


@pytest.fixture
def backend() -> SubprocessBackend:
    return SubprocessBackend()


@pytest.fixture
def profile() -> SandboxProfile:
    return TEST_PROFILE


@pytest.mark.asyncio
async def test_hello_sandbox_example(backend: SubprocessBackend, profile: SandboxProfile) -> None:
    """Run HELLO_SANDBOX and verify JSON output."""
    result = await backend.execute(HELLO_SANDBOX, profile)

    assert result.success, f"Script failed: {result.stderr}"
    assert result.exit_code == 0

    # stdout should be valid JSON
    output = json.loads(result.stdout)
    assert output["status"] == "ok"
    assert "python_version" in output
    assert "cwd" in output


@pytest.mark.asyncio
async def test_coherence_walk_example(backend: SubprocessBackend, profile: SandboxProfile) -> None:
    """Run COHERENCE_WALK and verify coherence stays in [0, 1]."""
    result = await backend.execute(COHERENCE_WALK, profile)

    assert result.success, f"Script failed: {result.stderr}"

    output = json.loads(result.stdout)
    assert output["status"] == "ok"
    assert 0.0 <= output["final_coherence"] <= 1.0
    assert 0.0 <= output["mean_coherence"] <= 1.0
    assert output["min_coherence"] >= 0.0
    assert output["max_coherence"] <= 1.0


@pytest.mark.asyncio
async def test_output_files_collected(backend: SubprocessBackend, profile: SandboxProfile) -> None:
    """Verify files written to output/ appear in result.output_files."""
    result = await backend.execute(HELLO_SANDBOX, profile)

    assert result.success, f"Script failed: {result.stderr}"
    assert result.output_files is not None, "No output files collected"
    assert "result.json" in result.output_files

    # Verify content is valid JSON
    content = json.loads(result.output_files["result.json"])
    assert content["status"] == "ok"


@pytest.mark.asyncio
async def test_coherence_walk_output_files(backend: SubprocessBackend, profile: SandboxProfile) -> None:
    """Verify coherence_walk produces both result.json and trajectory.json."""
    result = await backend.execute(COHERENCE_WALK, profile)

    assert result.success, f"Script failed: {result.stderr}"
    assert result.output_files is not None
    assert "result.json" in result.output_files
    assert "trajectory.json" in result.output_files

    trajectory = json.loads(result.output_files["trajectory.json"])
    assert isinstance(trajectory, list)
    assert len(trajectory) == 201  # 200 steps + initial value


@pytest.mark.asyncio
async def test_result_persistence(backend: SubprocessBackend, profile: SandboxProfile) -> None:
    """Verify persist_result writes to disk correctly."""
    result = await backend.execute(HELLO_SANDBOX, profile)
    assert result.success

    with tempfile.TemporaryDirectory() as tmpdir:
        run_dir = persist_result(
            result,
            run_id="test_run_001",
            tier="light",
            backend="SubprocessBackend",
            base_dir=Path(tmpdir),
        )

        assert run_dir.is_dir()
        assert (run_dir / "meta.json").is_file()
        assert (run_dir / "stdout.txt").is_file()

        meta = json.loads((run_dir / "meta.json").read_text())
        assert meta["run_id"] == "test_run_001"
        assert meta["tier"] == "light"
        assert meta["success"] is True
        assert meta["exit_code"] == 0
        assert meta["duration"] > 0

        # Output files should be saved
        assert (run_dir / "output" / "result.json").is_file()


@pytest.mark.asyncio
async def test_failed_script(backend: SubprocessBackend, profile: SandboxProfile) -> None:
    """Verify a failing script returns success=False."""
    bad_script = "import sys; print('about to fail'); sys.exit(1)"
    result = await backend.execute(bad_script, profile)

    assert not result.success
    assert result.exit_code == 1
    assert "about to fail" in result.stdout


@pytest.mark.asyncio
async def test_examples_dict() -> None:
    """Verify EXAMPLES dict contains expected entries."""
    assert "hello" in EXAMPLES
    assert "coherence_walk" in EXAMPLES
    assert EXAMPLES["hello"] == HELLO_SANDBOX
    assert EXAMPLES["coherence_walk"] == COHERENCE_WALK
