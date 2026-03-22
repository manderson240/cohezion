from __future__ import annotations

import pytest

from src.cohezion.healing.immune_system import ActuatorSystem


@pytest.mark.asyncio
async def test_actuator_patch_safety_gate():
    """Test that sensitive files are blocked from patching."""
    actuator = ActuatorSystem()
    # Attempt to patch sensitive file
    res = await actuator.execute_patch(".agent/CONSTITUTION.md", ["Fix typo"])
    assert res is False


@pytest.mark.asyncio
async def test_actuator_patch_forbidden_patterns():
    """Test that files matching forbidden patterns are blocked."""
    actuator = ActuatorSystem()
    # Test various forbidden patterns
    forbidden_paths = [
        ".env",
        ".secrets/config.yaml",
        "src/cohezion/security/output_filter.py",
        "config/credentials.json",
        "keys/private.pem",
        "CONSTITUTION.md",
    ]
    for path in forbidden_paths:
        res = await actuator.execute_patch(path, ["Fix"])
        assert res is False, f"Should block {path}"


@pytest.mark.asyncio
async def test_actuator_patch_path_traversal():
    """Test that path traversal attempts are blocked."""
    actuator = ActuatorSystem()
    # Path traversal attempts
    traversal_paths = [
        "../../../etc/passwd",
        "../../../../root/.ssh/id_rsa",
        "..\\..\\..\\windows\\system32",
    ]
    for path in traversal_paths:
        res = await actuator.execute_patch(path, ["Fix"])
        assert res is False, f"Should block path traversal: {path}"


@pytest.mark.asyncio
async def test_actuator_patch_case_sensitivity():
    """Test that case sensitivity bypasses are blocked."""
    actuator = ActuatorSystem()
    # Case variations
    case_paths = [
        "SECURITY/shield.py",
        "src/SECURITY/filter.py",
        ".Agent/constitution.md",
    ]
    for path in case_paths:
        res = await actuator.execute_patch(path, ["Fix"])
        assert res is False, f"Should block case variation: {path}"


@pytest.mark.asyncio
async def test_actuator_patch_verification_success():
    actuator = ActuatorSystem()
    # Mocking successful run (current suite should pass)
    res = await actuator.execute_patch("src/cohezion/healing/drift_analyzer.py", ["Optimize imports"])
    # If pytest passes locally, this should be True
    # In CI, we might need a mock for subprocess.run
    assert res is True
