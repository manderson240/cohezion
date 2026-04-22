"""Tests for the health check module."""

import os
from pathlib import Path
from unittest.mock import Mock

import pytest

from mcp_server.health import HealthChecker, HealthStatus


_IN_CI = os.environ.get("CI") == "true"


class TestHealthChecker:
    """Test suite for HealthChecker."""

    @pytest.fixture
    def health_checker(self, tmp_path):
        """Create a health checker with temporary vault path."""
        return HealthChecker(
            vault_path=str(tmp_path),
            surrealdb_url="http://localhost:8000",
            ollama_url="http://localhost:11434",
        )

    @pytest.fixture
    def real_vault_checker(self):
        """Create health checker with real vault path (local-only)."""
        if _IN_CI:
            pytest.skip("Requires local vault path — unavailable in CI")
        return HealthChecker(
            vault_path="/home/mike-anderson/vaults/cohezion-vault",
            surrealdb_url="http://localhost:8000",
            ollama_url="http://localhost:11434",
        )

    # ── Vault Health Checks ────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_check_vault_exists_and_writable(self, real_vault_checker):
        """Test vault check with existing, writable directory."""
        result = await real_vault_checker.check_vault()
        assert result["status"] == "ok"
        assert result["path_accessible"] is True
        assert "latency_ms" in result

    @pytest.mark.asyncio
    async def test_check_vault_nonexistent(self, health_checker):
        """Test vault check with nonexistent path."""
        health_checker.vault_path = Path("/nonexistent/path")
        result = await health_checker.check_vault()
        assert result["status"] == "error"
        assert result["path_accessible"] is False

    @pytest.mark.asyncio
    async def test_check_vault_not_directory(self, tmp_path, health_checker):
        """Test vault check when path is a file, not directory."""
        file_path = tmp_path / "file.txt"
        file_path.write_text("test")
        health_checker.vault_path = file_path
        result = await health_checker.check_vault()
        assert result["status"] == "error"
        assert result["path_accessible"] is False

    # ── SurrealDB Health Checks ────────────────────────────────────

    @pytest.mark.asyncio
    async def test_check_surrealdb_success(self, real_vault_checker):
        """Test SurrealDB check with live service."""
        result = await real_vault_checker.check_surrealdb()
        # May be "ok" if SurrealDB is running, or "error" if not
        assert result["status"] in ("ok", "error")
        assert "latency_ms" in result
        assert "connected" in result

    @pytest.mark.asyncio
    async def test_check_surrealdb_timeout(self, health_checker):
        """Test SurrealDB check with unreachable service."""
        health_checker.surrealdb_url = "http://127.0.0.1:19999"
        result = await health_checker.check_surrealdb()
        assert result["status"] == "error"
        assert result["connected"] is False

    # ── Ollama Health Checks ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_check_ollama_success(self, real_vault_checker):
        """Test Ollama check with live service."""
        result = await real_vault_checker.check_ollama()
        # May be "ok" if Ollama is running, or "error" if not
        assert result["status"] in ("ok", "error")
        assert "latency_ms" in result
        assert "models_loaded" in result

    @pytest.mark.asyncio
    async def test_check_ollama_timeout(self, health_checker):
        """Test Ollama check with unreachable service."""
        health_checker.ollama_url = "http://127.0.0.1:29999"
        result = await health_checker.check_ollama()
        assert result["status"] == "error"
        assert result["models_loaded"] == 0

    # ── Disk Space Health Checks ───────────────────────────────────

    @pytest.mark.asyncio
    async def test_check_disk_space_ok(self, real_vault_checker):
        """Test disk space check with normal disk usage."""
        result = await real_vault_checker.check_disk_space()
        assert result["status"] in ("ok", "warning", "critical")
        assert "free_gb" in result
        assert result["threshold_gb"] == 10

    # ── Memory Health Checks ───────────────────────────────────────

    @pytest.mark.asyncio
    async def test_check_memory_ok(self, real_vault_checker):
        """Test memory check."""
        result = await real_vault_checker.check_memory()
        assert result["status"] in ("ok", "warning")
        assert "memory_percent" in result
        assert "memory_mb" in result
        assert 0 <= result["memory_percent"] <= 100

    # ── Sheets API Health Checks ───────────────────────────────────

    @pytest.mark.asyncio
    async def test_check_sheets_api_disabled(self, health_checker):
        """Test Sheets API check when bridge is not configured."""
        result = await health_checker.check_sheets_api()
        assert result["status"] == "disabled"
        assert result["authenticated"] is False

    @pytest.mark.asyncio
    async def test_check_sheets_api_with_bridge(self, health_checker):
        """Test Sheets API check with mock bridge."""
        mock_bridge = Mock()
        mock_bridge.get_all_rows = Mock(return_value=[])
        health_checker.sheets_bridge = mock_bridge
        result = await health_checker.check_sheets_api()
        assert result["status"] == "ok"
        assert result["authenticated"] is True

    @pytest.mark.asyncio
    async def test_check_sheets_api_error(self, health_checker):
        """Test Sheets API check with bridge that raises error."""
        mock_bridge = Mock()
        mock_bridge.get_all_rows = Mock(side_effect=Exception("Auth failed"))
        health_checker.sheets_bridge = mock_bridge
        result = await health_checker.check_sheets_api()
        assert result["status"] == "error"
        assert result["authenticated"] is False

    # ── Overall Health Status Aggregation ──────────────────────────

    def test_aggregate_status_all_healthy(self):
        """Test status aggregation when all checks are healthy."""
        checks = {
            "vault": {"status": "ok"},
            "surrealdb": {"status": "ok"},
            "disk": {"status": "ok"},
        }
        status = HealthChecker._aggregate_status(checks)
        assert status == "healthy"

    def test_aggregate_status_with_warning(self):
        """Test status aggregation when one check has warning."""
        checks = {
            "vault": {"status": "ok"},
            "disk": {"status": "warning"},
            "memory": {"status": "ok"},
        }
        status = HealthChecker._aggregate_status(checks)
        assert status == "degraded"

    def test_aggregate_status_with_critical(self):
        """Test status aggregation when one check is critical."""
        checks = {
            "vault": {"status": "ok"},
            "disk": {"status": "critical"},
        }
        status = HealthChecker._aggregate_status(checks)
        assert status == "degraded"

    def test_aggregate_status_with_error(self):
        """Test status aggregation when one check has error."""
        checks = {
            "vault": {"status": "ok"},
            "surrealdb": {"status": "error"},
        }
        status = HealthChecker._aggregate_status(checks)
        assert status == "unhealthy"

    def test_aggregate_status_with_disabled(self):
        """Test status aggregation ignores disabled services."""
        checks = {
            "vault": {"status": "ok"},
            "sheets": {"status": "disabled"},
        }
        status = HealthChecker._aggregate_status(checks)
        assert status == "healthy"

    # ── Full Health Checks ─────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_run_all_checks_real(self, real_vault_checker):
        """Test running all checks together."""
        status = await real_vault_checker.run_all_checks(timeout=5)
        assert isinstance(status, HealthStatus)
        assert status.status in ("healthy", "degraded", "unhealthy")
        assert "vault" in status.checks
        assert "surrealdb" in status.checks
        assert "sheets_api" in status.checks
        assert "ollama" in status.checks
        assert "disk_space" in status.checks
        assert "memory" in status.checks

    @pytest.mark.asyncio
    async def test_run_all_checks_timeout(self, health_checker):
        """Test that timeout is handled gracefully."""
        health_checker.surrealdb_url = "http://127.0.0.1:19999"
        status = await health_checker.run_all_checks(timeout=1)
        assert isinstance(status, HealthStatus)
        assert status.status is not None

    @pytest.mark.asyncio
    async def test_caching(self, real_vault_checker):
        """Test that health check results are cached."""
        # First call
        status1 = await real_vault_checker.run_all_checks(timeout=5)
        # Second call should use cache
        status2 = await real_vault_checker.run_all_checks(timeout=5)

        assert status1.timestamp == status2.timestamp
        # Cache TTL is 60 seconds by default

    # ── Response Format ────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_health_status_to_dict(self, real_vault_checker):
        """Test HealthStatus.to_dict() method."""
        status = await real_vault_checker.run_all_checks(timeout=5)
        data = status.to_dict()

        assert isinstance(data, dict)
        assert data["status"] in ("healthy", "degraded", "unhealthy")
        assert "timestamp" in data
        assert isinstance(data["checks"], dict)
        for check_name, check_result in data["checks"].items():
            assert isinstance(check_result, dict)
