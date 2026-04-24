"""Fixtures for compound integration tests."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import pytest_asyncio

from cohezion.core.mcp_client import MCPClient


class _MockVirtualMemory:
    """Fake psutil result — reports 50% memory so resource guardrails don't fire.

    Includes all attributes used by silicon_guard.py, resource_monitor, and executor:
      - percent: used by executor guardrail (threshold ~85-90%)
      - total: 128 GiB (Strix Halo spec)
      - available: 64 GiB free
    """

    percent = 50.0
    total = 128 * 1024**3  # 128 GiB
    available = 64 * 1024**3  # 64 GiB free
    used = 64 * 1024**3


@pytest.fixture(autouse=True)
def _mock_psutil_resources():
    """Auto-patch psutil virtual_memory and cpu_percent for all compound tests.

    The resource guardrail in CompoundExecutor blocks execution when system
    memory exceeds ~85% or CPU exceeds ~80%. On a busy machine (running background
    agents, EVO loop, etc.) real resources can exceed these thresholds, causing
    every test that calls execute_task to fail.
    Mocking at conftest level fixes this suite-wide without touching each test.
    """
    with (
        patch("psutil.virtual_memory", return_value=_MockVirtualMemory()),
        patch("psutil.cpu_percent", return_value=25.0),
    ):
        yield


@pytest_asyncio.fixture
async def mcp_client():
    """Create mock MCP client for testing."""
    return MagicMock(spec=MCPClient)


def _find_project_root(start: Path) -> Path | None:
    """Walk upward looking for a ``.context`` directory."""
    current = start.resolve()
    while current != current.parent:
        if (current / ".context").exists():
            return current
        current = current.parent
    return None


@pytest.fixture(autouse=True, scope="session")
def _ensure_context_placeholders() -> None:
    """Materialise placeholder files referenced by .context/traceability/manifest.json.

    Reads the manifest, resolves each ``core_files[*].path``, and writes a
    minimal placeholder if the target is missing. This is idempotent and
    cheap: existing files are untouched. (Σ4 Ω12 Patch 7)
    """
    project_root = _find_project_root(Path(__file__).parent)
    if project_root is None:
        return

    manifest_path = project_root / ".context" / "traceability" / "manifest.json"
    if not manifest_path.exists():
        return

    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return

    context_dir = project_root / ".context"
    for entry in manifest.get("core_files", []):
        rel = entry.get("path")
        if not rel:
            continue
        target = context_dir / rel
        if target.exists():
            continue
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(
            "# Placeholder for compound context loader (created by tests/compound/conftest.py).\n"
            "# Real content lives in the corresponding src/ module; this file exists so\n"
            "# ContextManager._load_file() does not raise ContextLoadError during tests.\n",
            encoding="utf-8",
        )
