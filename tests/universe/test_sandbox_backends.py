"""Tests for sandbox isolation backends."""

import shutil
import subprocess

import pytest


def _systemd_user_available() -> bool:
    """Check if systemd-run --user can connect to the session bus."""
    if not shutil.which("systemd-run"):
        return False
    try:
        result = subprocess.run(
            ["systemd-run", "--user", "--scope", "--", "true"],
            capture_output=True,
            timeout=5,
        )
        return result.returncode == 0
    except Exception:
        return False


from cohezion.universe.sandbox_backends import (
    BackendResult,
    DockerBackend,
    SubprocessBackend,
    SystemdRunBackend,
    select_backend,
)
from cohezion.universe.sandbox_profiles import SandboxProfile, SandboxTier, get_profile


class TestSubprocessBackend:
    """SubprocessBackend is always available — test it thoroughly."""

    @pytest.fixture
    def backend(self):
        return SubprocessBackend()

    @pytest.fixture
    def light_profile(self):
        return get_profile(SandboxTier.LIGHT)

    @pytest.mark.anyio
    async def test_simple_script(self, backend, light_profile):
        result = await backend.execute("print('hello sandbox')", light_profile)
        assert result.success
        assert result.exit_code == 0
        assert "hello sandbox" in result.stdout

    @pytest.mark.anyio
    async def test_script_with_error(self, backend, light_profile):
        result = await backend.execute("raise ValueError('boom')", light_profile)
        assert not result.success
        assert result.exit_code != 0
        assert "boom" in result.stderr

    @pytest.mark.anyio
    async def test_script_with_files(self, backend, light_profile):
        script = "import json; data = json.load(open('input.json')); print(data['key'])"
        files = {"input.json": '{"key": "value123"}'}
        result = await backend.execute(script, light_profile, files=files)
        assert result.success
        assert "value123" in result.stdout

    @pytest.mark.anyio
    async def test_script_with_env(self, backend, light_profile):
        script = "import os; print(os.environ.get('TEST_VAR', 'missing'))"
        result = await backend.execute(script, light_profile, env={"TEST_VAR": "found_it"})
        assert result.success
        assert "found_it" in result.stdout

    @pytest.mark.anyio
    async def test_timeout(self, backend):
        short_profile = SandboxProfile(
            memory_limit_mb=512,
            cpu_quota_percent=100,
            timeout_seconds=5,
        )
        # justify: time.sleep(30) is the SANDBOXED PAYLOAD (a string passed to
        # backend.execute), not in-test sleep; needed to exercise the 5s timeout
        result = await backend.execute("import time; time.sleep(30)", short_profile)
        assert not result.success
        assert "Timeout" in result.stderr or result.exit_code != 0

    @pytest.mark.anyio
    async def test_cleanup_removes_workdir(self, backend, light_profile):
        # Execute creates a temporary directory and should clean it up
        result = await backend.execute("print('cleanup test')", light_profile)
        assert result.success

    @pytest.mark.anyio
    async def test_result_has_duration(self, backend, light_profile):
        result = await backend.execute("print('timing')", light_profile)
        assert result.duration > 0

    def test_is_available(self):
        assert SubprocessBackend.is_available() is True


class TestDockerBackend:
    @pytest.mark.skipif(
        not DockerBackend.is_available(),
        reason="Docker not available",
    )
    @pytest.mark.anyio
    async def test_docker_simple_script(self):
        backend = DockerBackend()
        profile = get_profile(SandboxTier.LIGHT)
        result = await backend.execute("print('docker hello')", profile)
        assert result.success
        assert "docker hello" in result.stdout


class TestSystemdRunBackend:
    @pytest.mark.skipif(
        not _systemd_user_available(),
        reason="systemd-run --user session bus not available",
    )
    @pytest.mark.anyio
    async def test_systemd_simple_script(self):
        backend = SystemdRunBackend()
        profile = get_profile(SandboxTier.LIGHT)
        result = await backend.execute("print('systemd hello')", profile)
        assert result.success
        assert "systemd hello" in result.stdout


class TestSelectBackend:
    def test_returns_backend(self):
        backend = select_backend()
        # Should return one of the three backends
        assert isinstance(backend, (DockerBackend, SystemdRunBackend, SubprocessBackend))

    def test_subprocess_always_fallback(self):
        # SubprocessBackend should always be available as fallback
        assert SubprocessBackend.is_available()


class TestBackendResult:
    def test_dataclass_fields(self):
        result = BackendResult(
            success=True,
            exit_code=0,
            stdout="output",
            stderr="",
            duration=1.5,
        )
        assert result.success
        assert result.output_files is None
