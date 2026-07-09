from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from src.cohezion.healing.immune_system import ActuatorSystem, SelfDiagnostic


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
    # Mock subprocess so we don't run the full test suite
    mock_result = MagicMock()
    mock_result.returncode = 0
    with patch("subprocess.run", return_value=mock_result):
        res = await actuator.execute_patch(
            "src/cohezion/healing/drift_analyzer.py", ["Optimize imports"]
        )
    assert res is True


@pytest.mark.asyncio
async def test_self_diagnostic_checks():
    diagnostic = SelfDiagnostic()

    # Mock open_connection (success), subprocess (git count = 12000), path parsing, systemctl failed
    mock_reader = MagicMock()
    mock_writer = MagicMock()
    mock_writer.wait_closed = AsyncMock()

    mock_git_proc = MagicMock()
    mock_git_proc.communicate = AsyncMock(return_value=(b"12000\n", b""))
    mock_git_proc.returncode = 0

    mock_systemctl_proc = MagicMock()
    mock_systemctl_proc.communicate = AsyncMock(return_value=(b"failed\n", b""))
    mock_systemctl_proc.returncode = 0

    # Mocking Path.exists for unit files
    mock_path = MagicMock()
    mock_path.exists.return_value = True
    mock_path.read_text.return_value = "SURREALDB_URL=http://localhost:8000\n"

    with (
        patch("asyncio.open_connection", AsyncMock(return_value=(mock_reader, mock_writer))),
        patch("asyncio.create_subprocess_shell", AsyncMock(return_value=mock_git_proc)),
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_systemctl_proc)),
        patch("src.cohezion.healing.immune_system.Path", return_value=mock_path),
    ):
        report = await diagnostic.run()

    assert report["status"] == "degraded"
    assert any("Git index bloat" in issue for issue in report["issues"])
    assert any("Port mismatch" in issue for issue in report["issues"])
    assert any("failed state" in issue for issue in report["issues"])


@pytest.mark.asyncio
async def test_self_diagnostic_surreal_error():
    diagnostic = SelfDiagnostic()

    with (
        patch("asyncio.open_connection", AsyncMock(side_effect=ConnectionRefusedError("Refused"))),
        patch("asyncio.create_subprocess_shell", AsyncMock(side_effect=Exception("Disabled"))),
        patch("asyncio.create_subprocess_exec", AsyncMock(side_effect=Exception("Disabled"))),
    ):
        report = await diagnostic.run()

    assert report["status"] == "error"
    assert any("SurrealDB connection refused" in issue for issue in report["issues"])


@pytest.mark.asyncio
async def test_actuator_autonomic_remediations():
    actuator = ActuatorSystem()

    # Mock create_subprocess_shell and create_subprocess_exec
    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(b"", b""))
    mock_proc.returncode = 0

    with (
        patch("asyncio.create_subprocess_shell", AsyncMock(return_value=mock_proc)) as mock_shell,
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_proc)) as mock_exec,
        patch("os.path.exists", return_value=True),
        patch("src.cohezion.healing.immune_system.get_narrator"),
    ):
        # 1. Test fix_entire_sync_port
        res_port = await actuator.fix_entire_sync_port()
        assert res_port is True
        mock_shell.assert_any_call(
            "sudo -n sed -i 's/localhost:8000/localhost:8001/g' /etc/systemd/system/entire-sync.service",
            stdout=-1,
            stderr=-1,
        )

        # 2. Test restart_failed_service
        res_restart = await actuator.restart_failed_service("entire-sync.service")
        assert res_restart is True
        # It checked status first
        mock_exec.assert_any_call(
            "systemctl", "--user", "status", "entire-sync.service", stdout=-1, stderr=-1
        )

        # 3. Test compact_git_index
        with patch("builtins.open", MagicMock()):
            res_compact = await actuator.compact_git_index()
            assert res_compact is True
            mock_exec.assert_any_call(
                "git",
                "rm",
                "-r",
                "--cached",
                ".archives",
                "archives",
                cwd=str(actuator._project_root),
                stdout=-1,
                stderr=-1,
            )


@pytest.mark.asyncio
async def test_self_diagnostic_stale_systemd_paths():
    diagnostic = SelfDiagnostic()

    # Mock pathlib.Path methods directly
    def mock_path_exists(self):
        return "entire-sync.service" in str(self)

    def mock_read_text(self, *args, **kwargs):
        if "entire-sync.service" in str(self):
            return "ExecStart=/stale_bin/sync\nWorkingDirectory=/stale_dir/cwd\n"
        return ""

    mock_reader = MagicMock()
    mock_writer = MagicMock()
    mock_writer.wait_closed = AsyncMock()

    mock_git_proc = MagicMock()
    mock_git_proc.communicate = AsyncMock(return_value=(b"100\n", b""))
    mock_git_proc.returncode = 0

    mock_systemctl_proc = MagicMock()
    mock_systemctl_proc.communicate = AsyncMock(return_value=(b"active\n", b""))
    mock_systemctl_proc.returncode = 0

    with (
        patch("asyncio.open_connection", AsyncMock(return_value=(mock_reader, mock_writer))),
        patch("asyncio.create_subprocess_shell", AsyncMock(return_value=mock_git_proc)),
        patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_systemctl_proc)),
        patch("pathlib.Path.exists", mock_path_exists),
        patch("pathlib.Path.read_text", mock_read_text),
        patch("os.path.exists", return_value=False),
    ):
        report = await diagnostic.run()

    assert report["status"] == "degraded"
    assert any("Stale ExecStart path" in issue for issue in report["issues"])
    assert any("Stale WorkingDirectory" in issue for issue in report["issues"])


@pytest.mark.asyncio
async def test_actuator_patch_verification_failure_rollback():
    import os

    actuator = ActuatorSystem()

    dummy_file = str(actuator._project_root / "src/cohezion/healing/temp_test_patch.py")
    initial_content = "def test_func():\n    return 42\n"
    with open(dummy_file, "w") as f:
        f.write(initial_content)

    try:

        def mock_subprocess_run(*args, **kwargs):
            # Modify file content inside the mock to simulate a failing applied patch
            with open(dummy_file, "w") as f:
                f.write("def test_func():\n    return 'invalid'\n")
            mock_result = MagicMock()
            mock_result.returncode = 1
            return mock_result

        with patch("subprocess.run", mock_subprocess_run):
            res = await actuator.execute_patch(dummy_file, ["Verification failure"])

        assert res is False
        with open(dummy_file) as f:
            current_content = f.read()
        assert current_content == initial_content
        assert not os.path.exists(dummy_file + ".bak")

    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)
        if os.path.exists(dummy_file + ".bak"):
            os.remove(dummy_file + ".bak")


@pytest.mark.asyncio
async def test_self_healing_systemd_integration():
    from src.cohezion.healing import HealthStatus, get_healing_system

    system = get_healing_system()

    status = HealthStatus(
        component="surrealdb",
        status="failing",
        metric="available",
        current_value=0.0,
        threshold=1.0,
    )

    with patch(
        "cohezion.healing.immune_system.ActuatorSystem.restart_failed_service",
        AsyncMock(return_value=True),
    ) as mock_restart:
        healed = await system.heal([status])

    assert healed == 1
    mock_restart.assert_called_once_with("surrealdb.service")
