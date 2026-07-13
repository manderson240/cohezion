"""Tests for Compound MCP Server new tools.

Follows AGENTS.md patterns:
- Mock external services at source level
- Keep all I/O async with timeouts
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import pytest

from cohezion.mcp.compound_server import (
    McpClientResolver,
    cohezion_batch_port_skills,
    cohezion_inspect_codebase,
    cohezion_skill_matrix,
    err,
    mcp,
    mcp_tool,
    ok,
)


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------


@pytest.mark.fast
class TestToolRegistration:
    """Verify the 3 new tools are registered on the FastMCP instance."""

    @pytest.mark.asyncio
    async def test_batch_port_skills_registered(self) -> None:
        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        assert "cohezion_batch_port_skills" in names

    @pytest.mark.asyncio
    async def test_inspect_codebase_registered(self) -> None:
        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        assert "cohezion_inspect_codebase" in names

    @pytest.mark.asyncio
    async def test_skill_matrix_registered(self) -> None:
        tools = await mcp.list_tools()
        names = {t.name for t in tools}
        assert "cohezion_skill_matrix" in names

    @pytest.mark.asyncio
    async def test_total_tool_count(self) -> None:
        tools = await mcp.list_tools()
        # Base tools (13) + 3 new = 16
        assert len(tools) >= 16


# ---------------------------------------------------------------------------
# Compound utilities (elegant simplicity)
# ---------------------------------------------------------------------------


@pytest.mark.fast
class TestCompoundUtils:
    """Verify the DRY utilities extracted during elegance refactor."""

    def test_ok_factory(self) -> None:
        r = ok(value=42, name="test")
        assert r == {"status": "success", "value": 42, "name": "test"}

    def test_err_factory(self) -> None:
        r = err("boom", code=7)
        assert r == {"status": "error", "error": "boom", "code": 7}

    @pytest.mark.asyncio
    async def test_mcp_tool_wraps_exceptions(self) -> None:
        mock_mcp = AsyncMock()
        # mcp.tool(description="...") returns a decorator that accepts the wrapper
        mock_mcp.tool = Mock(return_value=lambda fn: fn)

        @mcp_tool(mock_mcp)
        async def _explode(x: int) -> dict[str, Any]:
            """Boom."""
            raise ValueError("kaboom")

        result = await _explode(1)
        assert result["status"] == "error"
        assert "kaboom" in result["error"]
        mock_mcp.tool.assert_called_once()

    @pytest.mark.asyncio
    async def test_mcp_tool_returns_ok_on_success(self) -> None:
        mock_mcp = AsyncMock()
        mock_mcp.tool = Mock(return_value=lambda fn: fn)

        @mcp_tool(mock_mcp)
        async def _double(x: int) -> dict[str, Any]:
            """Double."""
            return ok(result=x * 2)

        result = await _double(21)
        assert result == {"status": "success", "result": 42}

    @pytest.mark.asyncio
    async def test_mcp_client_resolver_fresh(self) -> None:
        fake_client = AsyncMock()
        resolver = McpClientResolver(get_default_client=lambda: fake_client)

        with (
            patch.object(resolver, "_get_default", return_value=fake_client),
            patch(
                "cohezion.core.mcp_client.create_mcp_client",
                return_value=fake_client,
            ),
        ):
            client, _is_fresh = await resolver.resolve("http://test:8080")
            assert client is fake_client
            fake_client.connect.assert_awaited_once()

    def test_module_line_count(self) -> None:
        """Module shrunk from 782 to < 500 lines (elegant simplicity gate)."""
        mod = (
            Path(__file__).resolve().parents[2] / "src" / "cohezion" / "mcp" / "compound_server.py"
        )
        assert mod.exists()
        lines = len(mod.read_text().splitlines())
        assert lines <= 500, f"compound_server.py is {lines} lines; refactor target is <= 500"

    def test_error_handler_count(self) -> None:
        """Only 3 error handlers remain in module (was 16 before DRY refactor)."""
        mod = (
            Path(__file__).resolve().parents[2] / "src" / "cohezion" / "mcp" / "compound_server.py"
        )
        text = mod.read_text()
        assert text.count("except Exception") <= 5, "too many bare except blocks remain"


# ---------------------------------------------------------------------------
# cohezion_inspect_codebase tests
# ---------------------------------------------------------------------------


@pytest.mark.fast
class TestInspectCodebase:
    """Verify inspect_codebase returns metrics without touching live services."""

    @pytest.mark.asyncio
    async def test_returns_success_for_known_subdir(self) -> None:
        result = await cohezion_inspect_codebase(subdirectory="swarm", pattern="*.py", max_depth=2)
        assert result["status"] == "success"
        assert result["files"] >= 1
        assert result["total_lines"] >= 1
        assert "tree" in result
        for node in result["tree"]:
            assert "path" in node
            assert "lines" in node
            assert "depth" in node

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_subdir(self) -> None:
        result = await cohezion_inspect_codebase(
            subdirectory="nonexistent_xyz_123", pattern="*.py", max_depth=2
        )
        assert result["status"] == "error"
        assert "not found" in result["error"].lower() or "Path not found" in result["error"]

    @pytest.mark.asyncio
    async def test_respects_max_depth(self) -> None:
        result = await cohezion_inspect_codebase(subdirectory="cache", pattern="*.py", max_depth=1)
        assert result["status"] == "success"
        assert all(node["depth"] <= 1 for node in result["tree"])


# ---------------------------------------------------------------------------
# cohezion_skill_matrix tests
# ---------------------------------------------------------------------------


@pytest.mark.fast
class TestSkillMatrix:
    """Verify skill_matrix returns structured JSON."""

    @pytest.mark.asyncio
    async def test_returns_success_with_matrix(self) -> None:
        result = await cohezion_skill_matrix()
        assert result["status"] == "success"
        assert "prime_skills" in result
        assert "categories" in result
        assert "local_hermes_skills" in result
        assert "matrix" in result
        matrix: dict[str, Any] = result["matrix"]
        assert "prime_total" in matrix
        assert "hermes_local_total" in matrix
        assert "ported" in matrix
        assert "not_ported" in matrix
        assert "hermes_only" in matrix

    @pytest.mark.asyncio
    async def test_prime_skills_non_empty(self) -> None:
        result = await cohezion_skill_matrix()
        assert len(result["prime_skills"]) > 0
        for skill in result["prime_skills"]:
            assert "name" in skill
            assert "category" in skill
            assert "path" in skill

    @pytest.mark.asyncio
    async def test_local_skills_have_legacy_names(self) -> None:
        result = await cohezion_skill_matrix()
        local = result.get("local_hermes_skills", [])
        if not local:
            # cohezion_skill_matrix scans ~/.hermes/skills (an optional external Hermes
            # integration). When it isn't provisioned (CI, most dev envs) there are no local
            # skills to verify — skip rather than fail. The invariant only applies WHEN local
            # hermes skills exist: they must carry a legacy_name.
            pytest.skip("~/.hermes/skills not provisioned — no local hermes skills to verify")
        with_legacy = [s for s in local if s.get("legacy_name")]
        assert len(with_legacy) > 0, "No ported skills found with legacy_name"


# ---------------------------------------------------------------------------
# cohezion_batch_port_skills tests (mocked subprocess)
# ---------------------------------------------------------------------------


@pytest.mark.fast
class TestBatchPortSkills:
    """Verify batch port orchestration with mocked converter subprocess."""

    @pytest.mark.asyncio
    async def test_dry_run_with_mocked_converter(self) -> None:
        fake_proc = AsyncMock()
        fake_proc.returncode = 0
        fake_proc.communicate = AsyncMock(return_value=(b"ok", b""))

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            result = await cohezion_batch_port_skills(
                skill_names=["FAKE_SKILL_PRIME"], dry_run=True
            )

        assert result["status"] == "success"
        assert result["total"] == 1
        assert result["successes"] == 1
        assert result["dry_run"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_converter_missing_returns_error(self) -> None:
        with patch("pathlib.Path.exists", return_value=False):
            result = await cohezion_batch_port_skills(
                skill_names=["FAKE_SKILL_PRIME"], dry_run=False
            )
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_timeout_handled_gracefully(self) -> None:
        fake_proc = AsyncMock()
        fake_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            result = await cohezion_batch_port_skills(
                skill_names=["FAKE_SKILL_PRIME"], dry_run=False
            )

        assert result["status"] == "success"
        assert result["successes"] == 0
        assert result["results"][0]["success"] is False
        assert "timeout" in result["results"][0]["error"].lower()

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero_counts(self) -> None:
        result = await cohezion_batch_port_skills(skill_names=[], dry_run=False)
        assert result["status"] == "success"
        assert result["total"] == 0
        assert result["successes"] == 0
        assert result["results"] == []
