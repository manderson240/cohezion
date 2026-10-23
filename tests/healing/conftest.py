"""Keep the self-healing health log out of the repository during tests.

cohezion.healing._core writes HEALTH_LOG_PATH, which points at the tracked
src/cohezion/knowledge_graph/health_log.json; every test run rewrote it.
"""

from __future__ import annotations

import pytest

from cohezion.healing import _core


@pytest.fixture(autouse=True)
def _health_log_in_tmp(tmp_path, monkeypatch):
    monkeypatch.setattr(_core, "HEALTH_LOG_PATH", tmp_path / "health_log.json")
