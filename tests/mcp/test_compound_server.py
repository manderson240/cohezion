"""Tests for Compound MCP Server new tools.

Follows AGENTS.md patterns:
- Mock external services at source level
- Keep all I/O async with timeouts
- Use Pydantic at boundaries where applicable
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from types import ModuleType
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

# Import the module without running main() by using importlib
_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_SERVER_PATH = _PROJECT_ROOT / "src" / "cohezion" / "mcp" / "compound_server.py"


def _load_module_without_main() -> ModuleType:
    """Load compound_server without executing main()."""
    import importlib.util

    spec = importlib.util.spec_from_file_location("compound_server", str(_SERVER_PATH))
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    # Prevent __name__ == '__main__' branch from firing
    mod.__name__ = "compound_server_test"
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def compound_module() -> ModuleType:
    """Provide the compound_server module loaded safely."""
    return _load_module_without_main()


# ---------------------------------------------------------------------------
# Tool registration tests
# ---------------------------------------------------------------------------


@pytest.mark.fast
class TestToolRegistration:
    """Verify the 3 new tools are registered on the FastMCP instance."""

    @pytest.mark.asyncio
    async def test_batch_port_skills_registered(self, compound_module: ModuleType) -> None:
        tools = await compound_module.mcp.list_tools()
        names = {t.name for t in tools}
        assert "cohezion_batch_port_skills" in names

    @pytest.mark.asyncio
    async def test_inspect_codebase_registered(self, compound_module: ModuleType) -> None:
        tools = await compound_module.mcp.list_tools()
        names = {t.name for t in tools}
        assert "cohezion_inspect_codebase" in names

    @pytest.mark.asyncio
    async def test_skill_matrix_registered(self, compound_module: ModuleType) -> None:
        tools = await compound_module.mcp.list_tools()
        names = {t.name for t in tools}
        assert "cohezion_skill_matrix" in names

    @pytest.mark.asyncio
    async def test_total_tool_count(self, compound_module: ModuleType) -> None:
        tools = await compound_module.mcp.list_tools()
        # Base tools (13) + 3 new = 16
        assert len(tools) >= 16


# ---------------------------------------------------------------------------
# cohezion_inspect_codebase tests
# ---------------------------------------------------------------------------


@pytest.mark.fast
class TestInspectCodebase:
    """Verify inspect_codebase returns metrics without touching live services."""

    @pytest.mark.asyncio
    async def test_returns_success_for_known_subdir(self, compound_module: ModuleType) -> None:
        result = await compound_module.cohezion_inspect_codebase(
            subdirectory="swarm", pattern="*.py", max_depth=2
        )
        assert result["status"] == "success"
        assert result["files"] >= 1
        assert result["total_lines"] >= 1
        assert "tree" in result
        for node in result["tree"]:
            assert "path" in node
            assert "lines" in node
            assert "depth" in node

    @pytest.mark.asyncio
    async def test_returns_error_for_missing_subdir(self, compound_module: ModuleType) -> None:
        result = await compound_module.cohezion_inspect_codebase(
            subdirectory="nonexistent_xyz_123", pattern="*.py", max_depth=2
        )
        assert result["status"] == "error"
        assert "not found" in result["error"].lower() or "Path not found" in result["error"]

    @pytest.mark.asyncio
    async def test_respects_max_depth(self, compound_module: ModuleType) -> None:
        result = await compound_module.cohezion_inspect_codebase(
            subdirectory="cache", pattern="*.py", max_depth=1
        )
        assert result["status"] == "success"
        assert all(node["depth"] <= 1 for node in result["tree"])


# ---------------------------------------------------------------------------
# cohezion_skill_matrix tests
# ---------------------------------------------------------------------------


@pytest.mark.fast
class TestSkillMatrix:
    """Verify skill_matrix returns structured JSON."""

    @pytest.mark.asyncio
    async def test_returns_success_with_matrix(self, compound_module: ModuleType) -> None:
        result = await compound_module.cohezion_skill_matrix()
        assert result["status"] == "success"
        assert "prime_skills" in result
        assert "categories" in result
        assert "local_hermes_skills" in result
        assert "matrix" in result
        matrix = result["matrix"]
        assert "prime_total" in matrix
        assert "hermes_local_total" in matrix
        assert "ported" in matrix
        assert "not_ported" in matrix
        assert "hermes_only" in matrix

    @pytest.mark.asyncio
    async def test_prime_skills_non_empty(self, compound_module: ModuleType) -> None:
        result = await compound_module.cohezion_skill_matrix()
        assert len(result["prime_skills"]) > 0
        # Each skill should have name/category/path
        for skill in result["prime_skills"]:
            assert "name" in skill
            assert "category" in skill
            assert "path" in skill


# ---------------------------------------------------------------------------
# cohezion_batch_port_skills tests (mocked subprocess)
# ---------------------------------------------------------------------------


@pytest.mark.fast
class TestBatchPortSkills:
    """Verify batch port orchestration with mocked converter subprocess."""

    @pytest.mark.asyncio
    async def test_dry_run_with_mocked_converter(self, compound_module: ModuleType) -> None:
        with patch.object(
            compound_module, "asyncio"
        ) as mock_asyncio, patch.object(
            compound_module.Path, "__truediv__", side_effect=lambda x: Path("/tmp/fake_converter")
        ):
            # We actually want to mock the subprocess call inside the real asyncio,
            # so instead we patch create_subprocess_exec on the real asyncio module.
            pass

        # Simpler approach: patch asyncio.create_subprocess_exec directly
        fake_proc = AsyncMock()
        fake_proc.returncode = 0
        fake_proc.communicate = AsyncMock(return_value=(b"ok", b""))

        with patch(
            "asyncio.create_subprocess_exec", return_value=fake_proc
        ):
            result = await compound_module.cohezion_batch_port_skills(
                skill_names=["FAKE_SKILL_PRIME"], dry_run=True
            )

        assert result["status"] == "success"
        assert result["total"] == 1
        assert result["successes"] == 1
        assert result["dry_run"] is True
        assert len(result["results"]) == 1
        assert result["results"][0]["success"] is True

    @pytest.mark.asyncio
    async def test_converter_missing_returns_error(self, compound_module: ModuleType) -> None:
        # Force converter to not exist by patching Path.exists
        with patch("pathlib.Path.exists", return_value=False):
            result = await compound_module.cohezion_batch_port_skills(
                skill_names=["FAKE_SKILL_PRIME"], dry_run=False
            )
        assert result["status"] == "error"
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_timeout_handled_gracefully(self, compound_module: ModuleType) -> None:
        fake_proc = AsyncMock()
        fake_proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError)

        with patch("asyncio.create_subprocess_exec", return_value=fake_proc):
            result = await compound_module.cohezion_batch_port_skills(
                skill_names=["FAKE_SKILL_PRIME"], dry_run=False
            )

        assert result["status"] == "success"
        assert result["successes"] == 0
        assert result["results"][0]["success"] is False
        assert "timeout" in result["results"][0]["error"].lower()

    @pytest.mark.asyncio
    async def test_empty_list_returns_zero_counts(self, compound_module: ModuleType) -> None:
        result = await compound_module.cohezion_batch_port_skills(skill_names=[], dry_run=False)
        assert result["status"] == "success"
        assert result["total"] == 0
        assert result["successes"] == 0
        assert result["results"] == []
